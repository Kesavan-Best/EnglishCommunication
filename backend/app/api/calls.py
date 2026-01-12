from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from bson import ObjectId
from datetime import datetime
import uuid
import os

from backend.app.auth import AuthHandler
from backend.app.database import Database
from backend.app.models import UserInDB
from backend.app.schemas import CallResponse, CallInviteRequest, CallAcceptRequest, CallEndRequest
from backend.app.core.config import settings

router = APIRouter()

@router.post("/invite", response_model=CallResponse)
async def invite_to_call(
    invite_data: CallInviteRequest,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Invite a user to a call"""
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
    
    # Check for existing pending call
    existing_call = db.calls.find_one({
        "caller_id": current_user.id,
        "receiver_id": receiver_id,
        "status": "pending"
    })
    
    if existing_call:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already have a pending call with this user"
        )
    
    # Create call record
    call_data = CallInDB(
        caller_id=current_user.id,
        receiver_id=receiver_id
    )
    
    result = db.calls.insert_one(call_data.dict(by_alias=True))
    call_data.id = result.inserted_id
    
    return CallResponse(
        id=str(call_data.id),
        caller_id=str(call_data.caller_id),
        receiver_id=str(call_data.receiver_id),
        status=call_data.status,
        jitsi_room_id=call_data.jitsi_room_id,
        start_time=call_data.start_time,
        end_time=call_data.end_time,
        duration_seconds=call_data.duration_seconds,
        created_at=call_data.created_at
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
    
    # Check call status
    if call.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Call is already {call.status}"
        )
    
    # Generate Jitsi room ID
    jitsi_room_id = f"english-comm-{uuid.uuid4().hex}"
    
    # Update call
    update_data = {
        "status": "accepted",
        "jitsi_room_id": jitsi_room_id,
        "start_time": datetime.utcnow()
    }
    
    db.calls.update_one(
        {"_id": call_id},
        {"$set": update_data}
    )
    
    call.jitsi_room_id = jitsi_room_id
    call.status = "accepted"
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
    
    # Update user statistics
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