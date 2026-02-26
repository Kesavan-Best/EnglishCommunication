from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from bson import ObjectId
from datetime import datetime
import uuid
import os
import traceback

from backend.app.auth import AuthHandler
from backend.app.database import Database
from backend.app.models import UserInDB, CallInDB
from backend.app.schemas import CallResponse, CallInviteRequest, CallAcceptRequest, CallEndRequest, RatePartnerRequest
from backend.app.core.config import settings

router = APIRouter()

@router.post("/invite", response_model=CallResponse)
async def invite_to_call(
    invite_data: CallInviteRequest,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Invite a user to a call"""
    try:
        db = Database.get_db()
        
        try:
            receiver_id = ObjectId(invite_data.receiver_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID"
            )
        
        # Check if receiver exists and is online
        receiver = db.users.find_one({"_id": receiver_id})
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check online status using DATABASE (works across server instances)
        from backend.app.api.users import is_user_online_db
        is_receiver_online = is_user_online_db(str(receiver_id))
        
        if not is_receiver_online:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is offline"
            )
        
        # Convert current_user.id to ObjectId for database query
        caller_id = ObjectId(str(current_user.id)) if not isinstance(current_user.id, ObjectId) else current_user.id
        
        # Cancel any old pending calls from this caller to this receiver
        # This allows multiple call attempts without getting stuck
        db.calls.update_many(
            {
                "caller_id": caller_id,
                "receiver_id": receiver_id,
                "status": "pending"
            },
            {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow()}}
        )
        
        # Also cancel any old pending calls from receiver to caller (in case of reverse call)
        db.calls.update_many(
            {
                "caller_id": receiver_id,
                "receiver_id": caller_id,
                "status": "pending"
            },
            {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow()}}
        )
        
        # Check for existing ACTIVE call (not pending - we just cancelled those)
        existing_call = db.calls.find_one({
            "$or": [
                {"caller_id": caller_id, "receiver_id": receiver_id},
                {"caller_id": receiver_id, "receiver_id": caller_id}
            ],
            "status": "active"
        })
        
        if existing_call:
            # There's an active call, return it
            return CallResponse(
                id=str(existing_call["_id"]),
                caller_id=str(existing_call["caller_id"]),
                receiver_id=str(existing_call["receiver_id"]),
                status=existing_call["status"],
                jitsi_room_id=existing_call["jitsi_room_id"],
                start_time=existing_call.get("start_time"),
                end_time=existing_call.get("end_time"),
                duration_seconds=existing_call.get("duration_seconds"),
                created_at=existing_call["created_at"]
            )
        
        # Generate Jitsi room ID immediately
        jitsi_room_id = f"english-comm-{uuid.uuid4().hex}"
        
        # Get caller name for notification
        caller_name = current_user.name if hasattr(current_user, 'name') else current_user.username
        
        # Create call record with 'pending' status - receiver needs to accept
        call_dict = {
            "caller_id": caller_id,
            "receiver_id": receiver_id,
            "jitsi_room_id": jitsi_room_id,
            "status": "pending",
            "caller_name": caller_name,  # Store caller name for cross-instance notifications
            "notification_seen": False,  # Track if receiver has seen the notification
            "start_time": None,
            "end_time": None,
            "duration_seconds": None,
            "audio_url": None,
            "transcript_id": None,
            "analysis_id": None,
            "created_at": datetime.utcnow()
        }
        
        result = db.calls.insert_one(call_dict)
        call_id = result.inserted_id
        
        # Send WebSocket notification to receiver (may not work cross-instance)
        try:
            from backend.app.api.websocket import manager
            
            await manager.send_call_invite(
                from_user_id=str(caller_id),
                to_user_id=str(receiver_id),
                call_id=str(call_id),
                caller_name=caller_name
            )
            print(f"📞 Sent WebSocket call invite to user {receiver_id}")
        except Exception as ws_error:
            print(f"⚠️ WebSocket notification failed (cross-instance): {ws_error}")
            # This is OK - receiver will poll for pending calls
        
        return CallResponse(
            id=str(call_id),
            caller_id=str(caller_id),
            receiver_id=str(receiver_id),
            status="pending",
            jitsi_room_id=jitsi_room_id,
            start_time=None,
            end_time=None,
            duration_seconds=None,
            created_at=call_dict["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in invite_to_call: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create call: {str(e)}"
        )

@router.post("/accept", response_model=CallResponse)
async def accept_call(
    accept_data: CallAcceptRequest,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Accept a call invitation"""
    db = Database.get_db()
    
    try:
        call_id = ObjectId(accept_data.call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    # Get call
    call_data = db.calls.find_one({"_id": call_id})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    call = CallInDB(**call_data)
    
    # Check if current user is the receiver
    if str(call.receiver_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to accept this call"
        )
    
    # Since calls are now created with 'active' status, just return the call details
    # No need to update status - both users can join immediately
    if call.status not in ["active", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Call is already {call.status}"
        )
    
    # If call is still pending, update to active
    if call.status == "pending":
        db.calls.update_one(
            {"_id": call_id},
            {"$set": {"status": "active", "start_time": datetime.utcnow()}}
        )
        call.status = "active"
        call.start_time = datetime.utcnow()
    
    return CallResponse(
        id=str(call.id),
        caller_id=str(call.caller_id),
        receiver_id=str(call.receiver_id),
        status=call.status,
        jitsi_room_id=call.jitsi_room_id,
        start_time=call.start_time,
        end_time=call.end_time,
        duration_seconds=call.duration_seconds,
        created_at=call.created_at
    )

@router.post("/end", response_model=CallResponse)
async def end_call(
    end_data: CallEndRequest,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """End a call"""
    db = Database.get_db()
    
    try:
        call_id = ObjectId(end_data.call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    # Get call
    call_data = db.calls.find_one({"_id": call_id})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    call = CallInDB(**call_data)
    
    # Check if current user is part of the call
    if (str(call.caller_id) != str(current_user.id) and 
        str(call.receiver_id) != str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to end this call"
        )
    
    # Update call
    end_time = datetime.utcnow()
    duration = end_data.duration_seconds
    
    update_data = {
        "status": "completed",
        "end_time": end_time,
        "duration_seconds": duration
    }
    
    if end_data.audio_file:
        update_data["audio_url"] = end_data.audio_file
    
    db.calls.update_one(
        {"_id": call_id},
        {"$set": update_data}
    )
    
    # Update user statistics ONLY if call is valid:
    # - Both users actually connected
    # - Call duration between 60 seconds (1 min) and 300 seconds (5 min)  
    # - Users actually spoke (transcripts not empty)
    call_data = db.calls.find_one({"_id": call_id})
    both_connected = call_data.get("both_users_connected", False)
    caller_transcript = call_data.get("caller_transcript", "")
    receiver_transcript = call_data.get("receiver_transcript", "")
    
    # Check if users actually spoke (at least 20 characters in transcript)
    caller_spoke = len(caller_transcript.strip()) > 20
    receiver_spoke = len(receiver_transcript.strip()) > 20
    
    # Enforce 5-minute call limit for free users
    MAX_CALL_DURATION = 300  # 5 minutes in seconds
    if duration > MAX_CALL_DURATION:
        duration = MAX_CALL_DURATION
        update_data["duration_seconds"] = MAX_CALL_DURATION
        update_data["call_limit_reached"] = True
        db.calls.update_one(
            {"_id": call_id},
            {"$set": update_data}
        )
    
    # Validate call: both connected, 1-5 minutes, both spoke
    is_valid_call = (both_connected and 
                     60 <= duration <= MAX_CALL_DURATION and
                     caller_spoke and receiver_spoke)
    
    # Update user stats only for valid calls
    if is_valid_call:
        for user_id in [call.caller_id, call.receiver_id]:
            db.users.update_one(
                {"_id": user_id},
                {
                    "$inc": {
                        "total_calls": 1,
                        "total_call_duration": duration
                    }
                }
            )
    
    # Generate AI feedback - now based on REAL transcript only
    from backend.app.ai_processing.instant_analyzer import instant_analyzer
    
    # Get the stored transcripts and conversation
    conversation = call_data.get("conversation", [])
    
    # Generate feedback for caller
    caller_feedback = instant_analyzer.generate_instant_feedback(
        duration_seconds=duration,
        user_id=str(call.caller_id),
        transcript=caller_transcript if caller_transcript else None,
        conversation=conversation if conversation else None
    )
    
    # Generate feedback for receiver
    receiver_feedback = instant_analyzer.generate_instant_feedback(
        duration_seconds=duration,
        user_id=str(call.receiver_id),
        transcript=receiver_transcript if receiver_transcript else None,
        conversation=conversation if conversation else None
    )
    
    # Save AI feedback to database (only save real data, no fake ratings)
    db.calls.update_one(
        {"_id": call_id},
        {
            "$set": {
                "caller_ai_rating": caller_feedback.get("ai_rating"),  # May be None if no transcript
                "caller_ai_feedback": caller_feedback["overall_message"],
                "caller_strengths": caller_feedback["strengths"],
                "caller_weaknesses": [
                    {
                        "category": w["category"],
                        "title": w["title"],
                        "description": w["description"],
                        "tip": w["tip"]
                    }
                    for w in caller_feedback["weaknesses"]
                ],
                "caller_recommended_topics": caller_feedback["recommended_topics"],
                "caller_transcript_analyzed": caller_feedback.get("transcript_analyzed", False),
                "receiver_ai_rating": receiver_feedback.get("ai_rating"),  # May be None if no transcript
                "receiver_ai_feedback": receiver_feedback["overall_message"],
                "receiver_strengths": receiver_feedback["strengths"],
                "receiver_weaknesses": [
                    {
                        "category": w["category"],
                        "title": w["title"],
                        "description": w["description"],
                        "tip": w["tip"]
                    }
                    for w in receiver_feedback["weaknesses"]
                ],
                "receiver_recommended_topics": receiver_feedback["recommended_topics"],
                "receiver_transcript_analyzed": receiver_feedback.get("transcript_analyzed", False),
                "analysis_completed_at": datetime.utcnow(),
                "both_users_connected": True  # Mark as connected since call completed
            }
        }
    )
    
    print(f"✅ AI feedback generated for call {call_id} (duration: {duration}s, valid: {is_valid_call})")
    
    if not is_valid_call:
        # Log why call was not counted
        reasons = []
        if not both_connected:
            reasons.append("both users did not connect")
        if not (60 <= duration <= MAX_CALL_DURATION):
            reasons.append(f"duration {duration}s not between 60-300s")
        if not caller_spoke:
            reasons.append("caller did not speak enough")
        if not receiver_spoke:
            reasons.append("receiver did not speak enough")
        
        print(f"⚠️ Call not counted - Reasons: {', '.join(reasons)}")
        
        # Store reason in database
        db.calls.update_one(
            {"_id": call_id},
            {"$set": {"invalid_reason": ", ".join(reasons)}}
        )
    
    call.status = "completed"
    call.end_time = end_time
    call.duration_seconds = duration
    
    return CallResponse(
        id=str(call.id),
        caller_id=str(call.caller_id),
        receiver_id=str(call.receiver_id),
        status=call.status,
        jitsi_room_id=call.jitsi_room_id,
        start_time=call.start_time,
        end_time=call.end_time,
        duration_seconds=call.duration_seconds,
        created_at=call.created_at
    )

@router.get("/pending-invites")
async def get_pending_invites(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get pending call invitations for current user (for cross-instance polling)"""
    db = Database.get_db()
    
    # Find pending calls where current user is the receiver
    pending_calls = list(db.calls.find({
        "receiver_id": current_user.id,
        "status": "pending",
        "notification_seen": {"$ne": True}
    }).sort("created_at", -1).limit(5))
    
    invites = []
    for call in pending_calls:
        # Check if call is not too old (< 60 seconds)
        call_age = (datetime.utcnow() - call["created_at"]).total_seconds()
        if call_age < 60:
            invites.append({
                "call_id": str(call["_id"]),
                "caller_id": str(call["caller_id"]),
                "caller_name": call.get("caller_name", "Someone"),
                "jitsi_room_id": call["jitsi_room_id"],
                "created_at": call["created_at"].isoformat()
            })
    
    return {"invites": invites}

@router.get("/check-status/{call_id}")
async def check_call_status(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Check status of a call (for caller polling to know when accepted)"""
    db = Database.get_db()
    
    try:
        call = db.calls.find_one({"_id": ObjectId(call_id)})
        if not call:
            return {"status": "not_found"}
        
        return {
            "status": call.get("status", "unknown"),
            "accepted_at": call.get("accepted_at").isoformat() if call.get("accepted_at") else None,
            "jitsi_room_id": call.get("jitsi_room_id")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/mark-invite-seen")
async def mark_invite_seen(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Mark a call invite as seen (to stop polling for it)"""
    db = Database.get_db()
    
    try:
        db.calls.update_one(
            {"_id": ObjectId(call_id), "receiver_id": current_user.id},
            {"$set": {"notification_seen": True}}
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-calls", response_model=list[CallResponse])
async def get_my_calls(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get user's call history"""
    db = Database.get_db()
    
    calls = []
    cursor = db.calls.find({
        "$or": [
            {"caller_id": current_user.id},
            {"receiver_id": current_user.id}
        ]
    }).sort("created_at", -1).limit(50)
    
    for call_data in cursor:
        call = CallInDB(**call_data)
        calls.append(CallResponse(
            id=str(call.id),
            caller_id=str(call.caller_id),
            receiver_id=str(call.receiver_id),
            status=call.status,
            jitsi_room_id=call.jitsi_room_id,
            start_time=call.start_time,
            end_time=call.end_time,
            duration_seconds=call.duration_seconds,
            created_at=call.created_at
        ))
    
    return calls

@router.post("/upload-audio")
async def upload_audio(
    call_id: str,
    audio_file: UploadFile = File(...),
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Upload audio recording for a call"""
    # Validate file
    if not audio_file.filename.endswith('.webm') and not audio_file.filename.endswith('.wav'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .webm or .wav files are allowed"
        )
    
    # Save file
    filename = f"{call_id}_{current_user.id}_{datetime.utcnow().timestamp()}.webm"
    filepath = os.path.join(settings.audio_storage_path, filename)
    
    with open(filepath, "wb") as buffer:
        content = await audio_file.read()
        buffer.write(content)
    
    # Update call with audio URL
    db = Database.get_db()
    db.calls.update_one(
        {"_id": ObjectId(call_id)},
        {"$set": {"audio_url": f"/static/audio/{filename}"}}
    )
    
    return {"filename": filename, "url": f"/static/audio/{filename}"}

@router.post("/mark-joined")
async def mark_user_joined(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Mark that a user has actually joined the Jitsi call"""
    db = Database.get_db()
    
    try:
        call_id_obj = ObjectId(call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    call_data = db.calls.find_one({"_id": call_id_obj})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Determine if caller or receiver
    is_caller = str(call_data["caller_id"]) == str(current_user.id)
    is_receiver = str(call_data["receiver_id"]) == str(current_user.id)
    
    if not is_caller and not is_receiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not part of this call"
        )
    
    # Update joined status
    update_fields = {}
    if is_caller:
        update_fields["caller_joined"] = True
    else:
        update_fields["receiver_joined"] = True
    
    # Check if both have now joined
    caller_joined = call_data.get("caller_joined", False) or is_caller
    receiver_joined = call_data.get("receiver_joined", False) or is_receiver
    
    if caller_joined and receiver_joined:
        update_fields["both_users_connected"] = True
        print(f"✅ Both users connected to call {call_id}")
    
    db.calls.update_one(
        {"_id": call_id_obj},
        {"$set": update_fields}
    )
    
    return {
        "message": "Joined status updated",
        "both_connected": update_fields.get("both_users_connected", False)
    }

@router.post("/rate-partner")
async def rate_partner(
    rate_data: RatePartnerRequest,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Rate your conversation partner after a call"""
    db = Database.get_db()
    
    try:
        call_id = ObjectId(rate_data.call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    # Get call
    call_data = db.calls.find_one({"_id": call_id})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Determine who is rating whom
    is_caller = str(call_data["caller_id"]) == str(current_user.id)
    is_receiver = str(call_data["receiver_id"]) == str(current_user.id)
    
    if not is_caller and not is_receiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to rate this call"
        )
    
    # Update the appropriate rating
    if is_caller:
        # Caller rates receiver
        db.calls.update_one(
            {"_id": call_id},
            {
                "$set": {
                    "receiver_peer_rating": rate_data.rating,
                    "receiver_peer_feedback": rate_data.feedback
                }
            }
        )
    else:
        # Receiver rates caller
        db.calls.update_one(
            {"_id": call_id},
            {
                "$set": {
                    "caller_peer_rating": rate_data.rating,
                    "caller_peer_feedback": rate_data.feedback
                }
            }
        )
    
    return {"message": "Rating submitted successfully"}

@router.get("/{call_id}/results")
async def get_call_results(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get call results including ratings and weaknesses"""
    db = Database.get_db()
    
    try:
        call_id_obj = ObjectId(call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    # Get call
    call_data = db.calls.find_one({"_id": call_id_obj})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check authorization
    is_caller = str(call_data["caller_id"]) == str(current_user.id)
    is_receiver = str(call_data["receiver_id"]) == str(current_user.id)
    
    if not is_caller and not is_receiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this call"
        )
    
    # Check if call had any duration (relaxed from 10 to 5 seconds)
    duration = call_data.get("duration_seconds", 0)
    if duration < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call was too short for analysis. Please have a longer conversation."
        )
    
    # Check if AI analysis has been completed
    # If not, generate it now (for cases where end_call wasn't properly triggered)
    if not call_data.get("caller_ai_rating") or not call_data.get("receiver_ai_rating"):
        # Generate AI feedback now
        try:
            from backend.app.ai_processing.instant_analyzer import instant_analyzer
            
            caller_feedback = instant_analyzer.generate_instant_feedback(
                duration_seconds=duration,
                user_id=str(call_data["caller_id"]),
                transcript=call_data.get("caller_transcript"),
                conversation=call_data.get("conversation", [])
            )
            
            receiver_feedback = instant_analyzer.generate_instant_feedback(
                duration_seconds=duration,
                user_id=str(call_data["receiver_id"]),
                transcript=call_data.get("receiver_transcript"),
                conversation=call_data.get("conversation", [])
            )
            
            # Save to database
            db.calls.update_one(
                {"_id": call_id_obj},
                {
                    "$set": {
                        "caller_ai_rating": caller_feedback["ai_rating"],
                        "caller_ai_feedback": caller_feedback["overall_message"],
                        "caller_strengths": caller_feedback["strengths"],
                        "caller_weaknesses": [
                            {"category": w["category"], "title": w["title"], 
                             "description": w["description"], "tip": w["tip"]}
                            for w in caller_feedback["weaknesses"]
                        ],
                        "caller_recommended_topics": caller_feedback["recommended_topics"],
                        "receiver_ai_rating": receiver_feedback["ai_rating"],
                        "receiver_ai_feedback": receiver_feedback["overall_message"],
                        "receiver_strengths": receiver_feedback["strengths"],
                        "receiver_weaknesses": [
                            {"category": w["category"], "title": w["title"], 
                             "description": w["description"], "tip": w["tip"]}
                            for w in receiver_feedback["weaknesses"]
                        ],
                        "receiver_recommended_topics": receiver_feedback["recommended_topics"],
                        "both_users_connected": True,
                        "analysis_completed_at": datetime.utcnow()
                    }
                }
            )
            
            # Re-fetch the updated data
            call_data = db.calls.find_one({"_id": call_id_obj})
            
        except Exception as e:
            print(f"Error generating AI feedback: {e}")
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Analysis is being generated. Please refresh in a moment."
            )
    
    # Determine which feedback to show based on current user
    my_feedback = {}
    partner_feedback = {}
    
    if is_caller:
        my_feedback = {
            "ai_rating": call_data.get("caller_ai_rating"),
            "ai_feedback": call_data.get("caller_ai_feedback"),
            "strengths": call_data.get("caller_strengths", []),
            "weaknesses": call_data.get("caller_weaknesses", []),
            "recommended_topics": call_data.get("caller_recommended_topics", []),
            "peer_rating": call_data.get("receiver_peer_rating")
        }
        partner_feedback = {
            "peer_rating": call_data.get("caller_peer_rating")
        }
    else:
        my_feedback = {
            "ai_rating": call_data.get("receiver_ai_rating"),
            "ai_feedback": call_data.get("receiver_ai_feedback"),
            "strengths": call_data.get("receiver_strengths", []),
            "weaknesses": call_data.get("receiver_weaknesses", []),
            "recommended_topics": call_data.get("receiver_recommended_topics", []),
            "peer_rating": call_data.get("caller_peer_rating")
        }
        partner_feedback = {
            "peer_rating": call_data.get("receiver_peer_rating")
        }
    
    return {
        "call_id": str(call_data["_id"]),
        "duration_seconds": call_data.get("duration_seconds"),
        "start_time": call_data.get("start_time"),
        "end_time": call_data.get("end_time"),
        "my_feedback": my_feedback,
        "partner_feedback": partner_feedback,
        "call_status": call_data["status"]
    }

@router.get("/topics/all")
async def get_all_topics(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get all available learning topics"""
    from backend.app.ai_processing.instant_analyzer import instant_analyzer
    return {"topics": instant_analyzer.get_all_topics()}

@router.get("/topics/{topic_key}")
async def get_topic_details(
    topic_key: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get detailed content for a specific topic including reading and quiz"""
    from backend.app.ai_processing.instant_analyzer import instant_analyzer
    
    topic_data = instant_analyzer.get_topic_details(topic_key)
    if not topic_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return topic_data

@router.post("/{call_id}/generate-quiz")
async def generate_quiz(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Generate a personalized quiz based on call weaknesses"""
    db = Database.get_db()
    
    try:
        call_id_obj = ObjectId(call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    # Get call
    call_data = db.calls.find_one({"_id": call_id_obj})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Determine user's weaknesses
    is_caller = str(call_data["caller_id"]) == str(current_user.id)
    weaknesses = call_data.get("caller_weaknesses" if is_caller else "receiver_weaknesses", [])
    
    if not weaknesses:
        weaknesses = ["General English grammar", "Vocabulary building", "Sentence structure"]
    
    # Generate quiz from quiz generator
    from backend.app.ai_processing.quiz_generator import QuizGenerator
    
    quiz_generator = QuizGenerator()
    try:
        quiz_data = await quiz_generator.generate_quiz_from_topics(
            topics=weaknesses,
            num_questions=10
        )
        
        # Store quiz in database
        quiz_doc = {
            "user_id": current_user.id,
            "call_id": call_id_obj,
            "weaknesses": weaknesses,
            "questions": quiz_data["questions"],
            "completed": False,
            "score": None,
            "created_at": datetime.utcnow()
        }
        
        result = db.quizzes.insert_one(quiz_doc)
        quiz_doc["_id"] = result.inserted_id
        
        return {
            "id": str(result.inserted_id),
            "weaknesses": weaknesses,
            "questions": quiz_data["questions"],
            "completed": False,
            "score": None,
            "created_at": quiz_doc["created_at"]
        }
    except Exception as e:
        print(f"Error generating quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz: {str(e)}"
        )

from backend.app.api.websocket import manager as ws_manager

@router.post("/save-transcription")
async def save_transcription(
    call_id: str,
    text: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Save real-time transcription from a user during a call"""
    db = Database.get_db()
    
    try:
        call_id_obj = ObjectId(call_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID"
        )
    
    call_data = db.calls.find_one({"_id": call_id_obj})
    if not call_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Determine if caller or receiver
    is_caller = str(call_data["caller_id"]) == str(current_user.id)
    is_receiver = str(call_data["receiver_id"]) == str(current_user.id)
    
    if not is_caller and not is_receiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not part of this call"
        )
    
    # Determine role
    speaker_role = "caller" if is_caller else "receiver"
    transcript_field = "caller_transcript" if is_caller else "receiver_transcript"
    
    # Append to existing transcript or create new
    existing_transcript = call_data.get(transcript_field, "")
    updated_transcript = existing_transcript + " " + text if existing_transcript else text
    
    # Add to conversation array
    conversation = call_data.get("conversation", [])
    conversation.append({
        "speaker": speaker_role,
        "text": text,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Update in database
    db.calls.update_one(
        {"_id": call_id_obj},
        {
            "$set": {
                transcript_field: updated_transcript.strip(),
                "conversation": conversation
            }
        }
    )
    
    # Broadcast transcription to all participants via WebSocket
    try:
        await ws_manager.broadcast_transcription(
            call_id=call_id,
            speaker_id=str(current_user.id),
            speaker_role=speaker_role,
            text=text
        )
    except Exception as e:
        print(f"⚠️ Failed to broadcast transcription: {e}")
    
    return {
        "success": True,
        "message": "Transcription saved",
        "transcript_length": len(updated_transcript)
    }

# In your invite_to_call function, add after creating the call:
async def send_call_notification(call_id: str, receiver_id: str, caller_id: str, jitsi_room_id: str):
    """Send WebSocket call notification"""
    try:
        call_data = {
            "call_id": call_id,
            "caller_id": caller_id,
            "jitsi_room_id": jitsi_room_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await ws_manager.send_call_invitation(
            from_user=str(caller_id),
            to_user=str(receiver_id),
            call_id=call_id,
            call_data=call_data
        )
        
        print(f"📞 Call notification sent to {receiver_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")
        return False


# ==================== WebRTC Signaling API (Database-based) ====================
# These endpoints enable cross-instance WebRTC signaling by storing signals in MongoDB

@router.post("/webrtc/signal")
async def store_webrtc_signal(
    signal_data: dict,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Store a WebRTC signal (offer, answer, or ICE candidate) in database for cross-instance signaling"""
    db = Database.get_db()
    
    try:
        call_id = signal_data.get("call_id")
        to_user_id = signal_data.get("to_user_id")
        signal_type = signal_data.get("type")  # offer, answer, ice-candidate
        
        if not all([call_id, to_user_id, signal_type]):
            raise HTTPException(status_code=400, detail="Missing required fields: call_id, to_user_id, type")
        
        # Create signal document
        signal_doc = {
            "call_id": call_id,
            "from_user_id": str(current_user.id),
            "to_user_id": to_user_id,
            "signal_type": signal_type,
            "signal_data": signal_data,
            "created_at": datetime.utcnow(),
            "read": False
        }
        
        # Store in webrtc_signals collection
        result = db.webrtc_signals.insert_one(signal_doc)
        
        print(f"📡 WebRTC signal stored: {signal_type} from {current_user.id} to {to_user_id}")
        
        # Also try WebSocket for faster delivery (may fail if cross-instance)
        try:
            from backend.app.api.websocket import manager
            await manager.send_personal_message({
                "type": "webrtc_signal",
                "signal": signal_data
            }, to_user_id)
        except Exception as ws_error:
            print(f"⚠️ WebSocket delivery failed (user will poll): {ws_error}")
        
        return {"status": "ok", "signal_id": str(result.inserted_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error storing signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webrtc/signals/{call_id}")
async def get_webrtc_signals(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Poll for WebRTC signals directed to current user for a specific call"""
    db = Database.get_db()
    
    try:
        # Find unread signals for this user and call
        signals = list(db.webrtc_signals.find({
            "call_id": call_id,
            "to_user_id": str(current_user.id),
            "read": False
        }).sort("created_at", 1))  # Oldest first
        
        # Mark signals as read
        if signals:
            signal_ids = [s["_id"] for s in signals]
            db.webrtc_signals.update_many(
                {"_id": {"$in": signal_ids}},
                {"$set": {"read": True}}
            )
        
        # Return signal data
        result = []
        for s in signals:
            result.append({
                "type": s["signal_type"],
                "signal": s["signal_data"],
                "from_user_id": s["from_user_id"],
                "created_at": s["created_at"].isoformat()
            })
        
        return {"signals": result}
        
    except Exception as e:
        print(f"❌ Error fetching signals: {e}")
        return {"signals": [], "error": str(e)}


@router.delete("/webrtc/signals/{call_id}")
async def clear_webrtc_signals(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Clear all WebRTC signals for a call (cleanup after call ends)"""
    db = Database.get_db()
    
    try:
        result = db.webrtc_signals.delete_many({
            "call_id": call_id,
            "$or": [
                {"from_user_id": str(current_user.id)},
                {"to_user_id": str(current_user.id)}
            ]
        })
        
        return {"status": "ok", "deleted": result.deleted_count}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}