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
        
        if not receiver.get("is_online", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is offline"
            )
        
        # Convert current_user.id to ObjectId for database query
        caller_id = ObjectId(str(current_user.id)) if not isinstance(current_user.id, ObjectId) else current_user.id
        
        # Check for existing pending/active call and clean up old ones
        existing_call = db.calls.find_one({
            "$or": [
                {"caller_id": caller_id, "receiver_id": receiver_id},
                {"caller_id": receiver_id, "receiver_id": caller_id}
            ],
            "status": {"$in": ["pending", "active"]}
        })
        
        if existing_call:
            # Check if call is more than 5 minutes old, if so, mark as failed and create new one
            call_age = (datetime.utcnow() - existing_call["created_at"]).total_seconds()
            if call_age > 300:  # 5 minutes
                db.calls.update_one(
                    {"_id": existing_call["_id"]},
                    {"$set": {"status": "failed", "end_time": datetime.utcnow()}}
                )
            else:
                # Return existing call if it's recent
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
        
        # Create call record with 'active' status so both users can join immediately
        call_dict = {
            "caller_id": caller_id,
            "receiver_id": receiver_id,
            "jitsi_room_id": jitsi_room_id,
            "status": "active",
            "start_time": datetime.utcnow(),
            "end_time": None,
            "duration_seconds": None,
            "audio_url": None,
            "transcript_id": None,
            "analysis_id": None,
            "created_at": datetime.utcnow()
        }
        
        result = db.calls.insert_one(call_dict)
        call_id = result.inserted_id
        
        # Send WebSocket notification to receiver
        try:
            from backend.app.api.websocket import manager
            
            # Get caller name for notification
            caller_name = current_user.name if hasattr(current_user, 'name') else current_user.username
            
            await manager.send_call_invite(
                from_user_id=str(caller_id),
                to_user_id=str(receiver_id),
                call_id=str(call_id),
                caller_name=caller_name
            )
            print(f"📞 Sent call invite notification to user {receiver_id}")
        except Exception as ws_error:
            print(f"⚠️ Failed to send WebSocket notification: {ws_error}")
        
        return CallResponse(
            id=str(call_id),
            caller_id=str(caller_id),
            receiver_id=str(receiver_id),
            status="active",
            jitsi_room_id=jitsi_room_id,
            start_time=call_dict["start_time"],
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
    
    # Update user statistics ONLY if BOTH users actually connected
    call_data = db.calls.find_one({"_id": call_id})
    both_connected = call_data.get("both_users_connected", False)
    
    if both_connected and duration >= 10:
        # Only count as valid call if both users connected AND spoke for 10+ seconds
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
        
        # Generate INSTANT AI feedback for both users using stored conversation
        from backend.app.ai_processing.instant_analyzer import instant_analyzer
        
        # Get the stored transcripts and conversation
        caller_transcript = call_data.get("caller_transcript", "")
        receiver_transcript = call_data.get("receiver_transcript", "")
        conversation = call_data.get("conversation", [])
        
        # Generate feedback for caller based on their transcript
        caller_feedback = instant_analyzer.generate_instant_feedback(
            duration_seconds=duration,
            user_id=str(call.caller_id),
            transcript=caller_transcript if caller_transcript else None,
            conversation=conversation if conversation else None
        )
        
        # Generate feedback for receiver based on their transcript
        receiver_feedback = instant_analyzer.generate_instant_feedback(
            duration_seconds=duration,
            user_id=str(call.receiver_id),
            transcript=receiver_transcript if receiver_transcript else None,
            conversation=conversation if conversation else None
        )
        
        # Save AI feedback to database
        db.calls.update_one(
            {"_id": call_id},
            {
                "$set": {
                    "caller_ai_rating": caller_feedback["ai_rating"],
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
                    "receiver_ai_rating": receiver_feedback["ai_rating"],
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
                    "analysis_completed_at": datetime.utcnow()
                }
            }
        )
        
        print(f"✅ Instant AI feedback generated for call {call_id}")
    else:
        print(f"⚠️ Call not counted - both_connected: {both_connected}, duration: {duration}")
    
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
    
    # Check if call actually had a meaningful conversation
    if not call_data.get("duration_seconds") or call_data.get("duration_seconds", 0) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call was too short for analysis. Minimum 10 seconds required."
        )
    
    # Check if BOTH users actually connected
    if not call_data.get("both_users_connected", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call did not connect properly. Both users must join the call. Please try again."
        )
    
    # Check if AI analysis has been completed (should be instant now)
    if not call_data.get("caller_ai_rating") or not call_data.get("receiver_ai_rating"):
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Analysis is being generated. Please wait a moment."
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