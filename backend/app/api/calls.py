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
            await manager.send_call_invite(
                from_user_id=str(caller_id),
                to_user_id=str(receiver_id),
                call_id=str(call_id)
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
    else:
        print(f"⚠️ Call not counted - both_connected: {both_connected}, duration: {duration}")
    
    # Trigger AI processing in background
    if end_data.audio_file:
        # This would trigger Whisper processing
        # For now, we'll create a placeholder
        pass
    
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
    
    # Check if AI analysis has been completed
    if not call_data.get("caller_ai_rating") or not call_data.get("receiver_ai_rating"):
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Analysis not ready yet. Audio processing is in progress. Please check back in a few minutes."
        )
    
    return CallResponse(
        id=str(call_data["_id"]),
        caller_id=str(call_data["caller_id"]),
        receiver_id=str(call_data["receiver_id"]),
        status=call_data["status"],
        jitsi_room_id=call_data.get("jitsi_room_id"),
        start_time=call_data.get("start_time"),
        end_time=call_data.get("end_time"),
        duration_seconds=call_data.get("duration_seconds"),
        caller_audio_url=call_data.get("caller_audio_url"),
        receiver_audio_url=call_data.get("receiver_audio_url"),
        caller_ai_rating=call_data.get("caller_ai_rating"),
        receiver_ai_rating=call_data.get("receiver_ai_rating"),
        caller_peer_rating=call_data.get("caller_peer_rating"),
        receiver_peer_rating=call_data.get("receiver_peer_rating"),
        caller_ai_feedback=call_data.get("caller_ai_feedback"),
        receiver_ai_feedback=call_data.get("receiver_ai_feedback"),
        caller_weaknesses=call_data.get("caller_weaknesses", []),
        receiver_weaknesses=call_data.get("receiver_weaknesses", []),
        created_at=call_data["created_at"]
    )

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