from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pymongo import ReturnDocument
import shutil
import os
import logging
import random
import string
from pathlib import Path

from backend.app.schemas import UserRegisterRequest, UserLoginRequest, UserResponse, ForgotPasswordRequest, ResetPasswordRequest
from backend.app.models import UserInDB
from backend.app.auth import AuthHandler
from backend.app.database import Database
from backend.app.core.config import settings
from datetime import timedelta
from backend.app.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _persist_voice_enrollment_audio(user_id: str, audio_bytes: bytes, suffix: str) -> str:
    """Persist latest enrollment audio under static and return the public URL path."""
    static_audio_dir = Path(__file__).resolve().parents[3] / "static" / "audio" / "enrollments"
    static_audio_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    filename = f"{user_id}_{timestamp}{ext}"
    file_path = static_audio_dir / filename

    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    return f"/static/audio/enrollments/{filename}"

# Helper function to check if user is online based on WebSocket + database status
# Priority: WebSocket connection (real-time) > Database flag (cross-instance)
def is_user_online_db(user_id: str) -> bool:
    """Check if user is online - uses WebSocket first, then DB fallback"""
    try:
        # FIRST: Check WebSocket manager for real-time connection (same server instance)
        try:
            from backend.app.api.websocket import manager
            if manager.is_user_connected(user_id):
                return True
            # Also check if user is in grace period (just disconnected, might reconnect)
            if user_id in manager._offline_tasks:
                return True  # Still in grace period, treat as online
        except Exception:
            pass  # WebSocket manager not available, fall back to DB
        
        # SECOND: Check database status (works across server instances)
        db = Database.get_db()
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return False
        
        # User must have is_online=True AND last_seen within the recent heartbeat window
        is_online = user.get("is_online", False)
        last_seen = user.get("last_seen")
        
        if not is_online:
            return False
        
        if last_seen:
            # Check if last_seen is within the last 20 seconds (heartbeat is 15s)
            time_threshold = datetime.utcnow() - timedelta(seconds=20)
            if last_seen < time_threshold:
                # Stale status - mark as offline in DB to clean up
                db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"is_online": False}}
                )
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking online status for {user_id}: {e}")
        return False

# Helper function to calculate user rank
async def calculate_user_rank(user_id: str) -> int:
    db = Database.get_db()
    test_emails = ["john@example.com", "jane@example.com", "bob@example.com"]
    all_users = list(db.users.find({"email": {"$nin": test_emails}}).sort("ai_score", -1))
    rank = next((i + 1 for i, u in enumerate(all_users) if str(u["_id"]) == user_id), None)
    return rank

def generate_password_reset_otp(length: int = 6) -> str:
    """Generate numeric OTP for password reset"""
    return ''.join(random.choices(string.digits, k=length))

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegisterRequest):
    """Register a new user - requires email verification"""
    try:
        db = Database.get_db()
        
        logger.info(f"📝 Registration attempt for: {user_data.email}")
        
        # Check if user already exists
        existing_user = db.users.find_one({"email": user_data.email})
        if existing_user:
            logger.warning(f"❌ Email already registered: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verify OTP was verified (email verification required)
        otp_record = db.otps.find_one({
            "email": user_data.email,
            "verified": True
        })
        
        if not otp_record:
            logger.warning(f"❌ Email not verified: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please verify your email with OTP first"
            )
        
        # Hash password
        hashed_password = AuthHandler.hash_password(user_data.password)
        logger.info(f"🔐 Password hashed for: {user_data.email}")
        
        # Create user document
        user_doc = {
            "email": user_data.email,
            "name": user_data.name,
            "hashed_password": hashed_password,
            "avatar_url": None,
            "is_online": False,
            "ai_score": 0.0,
            "total_calls": 0,
            "total_call_duration": 0,
            "avg_fluency_score": 0.0,
            "weaknesses": [],
            "voice_fingerprint": None,
            # Voice enrollment is required only for users created after this feature.
            "voice_enrollment_required": True,
            "voice_fingerprint_enrolled": False,
            "voice_fingerprint_enrolled_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        
        # Delete used OTP
        db.otps.delete_many({"email": user_data.email})
        
        # Send welcome email (non-blocking)
        try:
            from backend.app.email_service import email_service
            success, error_msg = email_service.send_welcome_email(user_data.email, user_data.name)
            if not success:
                logger.warning(f"⚠️ Welcome email failed: {error_msg}")
        except Exception as e:
            logger.warning(f"Warning: Failed to send welcome email: {e}")
        
        logger.info(f"✅ User registered successfully: {user_data.email} (ID: {result.inserted_id})")
        
        return UserResponse(
            id=str(result.inserted_id),
            email=user_data.email,
            name=user_data.name,
            avatar_url=None,
            is_online=False,
            ai_score=0.0,
            total_calls=0,
            total_call_duration=0,
            avg_fluency_score=0.0,
            weaknesses=[],
            rank=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login")
async def login(user_data: UserLoginRequest):
    """Login user and return access token"""
    db = Database.get_db()
    
    print(f"🔐 Login attempt for email: {user_data.email}")
    
    # Find user
    user = db.users.find_one({"email": user_data.email})
    if not user:
        print(f"❌ User not found: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    print(f"✅ User found: {user_data.email}")
    
    # Get password hash (handle both old and new field names)
    password_hash = user.get("hashed_password") or user.get("password_hash")
    if not password_hash:
        print(f"❌ No password hash found for user: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    
    print(f"🔑 Verifying password for: {user_data.email}")
    
    # Verify password
    if not AuthHandler.verify_password(user_data.password, password_hash):
        print(f"❌ Password verification failed for: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    print(f"✅ Password verified successfully for: {user_data.email}")
    
    # Create access token
    token = AuthHandler.create_access_token(str(user["_id"]))
    
    # Update online status
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_online": True, "last_seen": datetime.utcnow()}}
    )
    
    # Calculate rank
    all_users = list(db.users.find().sort("ai_score", -1))
    rank = next((i + 1 for i, u in enumerate(all_users) if str(u["_id"]) == str(user["_id"])), None)
    
    voice_fingerprint_enrolled = bool(user.get("voice_fingerprint_enrolled", False))
    voice_enrollment_required = bool(user.get("voice_enrollment_required", False)) and not voice_fingerprint_enrolled

    return {
        "access_token": token,
        "token_type": "bearer",
        "voice_fingerprint_enrolled": voice_fingerprint_enrolled,
        "voice_enrollment_required": voice_enrollment_required,
        "user": UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url"),
            is_online=True,
            ai_score=user.get("ai_score", 0.0),
            total_calls=user.get("total_calls", 0),
            total_call_duration=user.get("total_call_duration", 0),
            avg_fluency_score=user.get("avg_fluency_score", 0.0),
            weaknesses=user.get("weaknesses", []),
            rank=rank
        )
    }

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Send password reset OTP to a registered user's email"""
    db = Database.get_db()
    email = request.email.strip()

    # Check if user exists
    user = db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )

    otp = generate_password_reset_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Keep only one active reset code per email
    db.password_resets.delete_many({"email": email, "used": False})
    db.password_resets.insert_one({
        "email": email,
        "user_id": user["_id"],
        "otp": otp,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "attempts": 0,
        "used": False
    })

    # Send reset email
    success, error_msg = email_service.send_password_reset_email(
        to_email=email,
        otp=otp,
        name=user.get("name", "")
    )

    db.password_resets.update_one(
        {"email": email, "used": False},
        {"$set": {
            "email_sent": success,
            "email_error": error_msg if not success else None
        }}
    )

    if not success:
        logger.error(f"❌ Password reset email failed for {email}: {error_msg}")
        return {
            "message": "Reset code generated but email failed to send",
            "email": email,
            "email_sent": False,
            "otp_for_testing": otp,
            "warning": "Use the OTP below for testing or check email configuration",
            "error_details": error_msg
        }

    return {
        "message": "Password reset code sent successfully",
        "email": email,
        "email_sent": True,
        "expires_in_minutes": 10
    }

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset user password using OTP sent to email"""
    db = Database.get_db()
    email = request.email.strip()
    otp = request.otp.strip()
    new_password = request.new_password.strip()

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    reset_record = db.password_resets.find_one(
        {"email": email, "used": False},
        sort=[("created_at", -1)]
    )

    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active reset request found. Please request a new code."
        )

    if datetime.utcnow() > reset_record["expires_at"]:
        db.password_resets.delete_one({"_id": reset_record["_id"]})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new code."
        )

    attempts = reset_record.get("attempts", 0)
    if attempts >= 5:
        db.password_resets.delete_one({"_id": reset_record["_id"]})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. Please request a new code."
        )

    if reset_record.get("otp") != otp:
        db.password_resets.update_one(
            {"_id": reset_record["_id"]},
            {"$inc": {"attempts": 1}}
        )
        remaining = max(0, 4 - attempts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reset code. {remaining} attempts remaining."
        )

    user = db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found"
        )

    hashed_password = AuthHandler.hash_password(new_password)
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "hashed_password": hashed_password,
            "updated_at": datetime.utcnow()
        }}
    )

    db.password_resets.update_one(
        {"_id": reset_record["_id"]},
        {"$set": {"used": True, "used_at": datetime.utcnow()}}
    )

    return {"message": "Password reset successful. Please login with your new password."}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get current logged-in user information"""
    db = Database.get_db()
    
    # Calculate rank
    all_users = list(db.users.find().sort("ai_score", -1))
    rank = next((i + 1 for i, u in enumerate(all_users) if str(u["_id"]) == str(current_user.id)), None)
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        is_online=current_user.is_online,
        ai_score=current_user.ai_score,
        total_calls=current_user.total_calls,
        total_call_duration=current_user.total_call_duration,
        avg_fluency_score=current_user.avg_fluency_score,
        weaknesses=current_user.weaknesses,
        rank=rank
    )

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    name: str = Form(None),
    avatar: UploadFile = File(None),
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Update user profile information"""
    db = Database.get_db()
    
    update_data = {"updated_at": datetime.utcnow()}
    
    # Update name if provided
    if name and name.strip():
        update_data["name"] = name.strip()
    
    # Handle avatar upload
    if avatar and avatar.filename:
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if avatar.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPEG, PNG, GIF, or WebP images are allowed"
            )
        
        # Create avatars directory if it doesn't exist
        avatar_dir = os.path.join(settings.audio_storage_path, "..", "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = os.path.splitext(avatar.filename)[1]
        filename = f"avatar_{current_user.id}_{datetime.utcnow().timestamp()}{file_extension}"
        filepath = os.path.join(avatar_dir, filename)
        
        # Save the file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)
        
        # Update avatar URL
        avatar_url = f"/static/avatars/{filename}"
        update_data["avatar_url"] = avatar_url
        
        # Delete old avatar if exists
        if current_user.avatar_url:
            old_filename = current_user.avatar_url.split("/")[-1]
            old_filepath = os.path.join(avatar_dir, old_filename)
            if os.path.exists(old_filepath):
                os.remove(old_filepath)
    
    # Update user in database
    db.users.update_one(
        {"_id": current_user.id},
        {"$set": update_data}
    )
    
    # Get updated user
    updated_user = db.users.find_one({"_id": current_user.id})
    user = UserInDB(**updated_user)
    
    # Calculate rank
    rank = await calculate_user_rank(str(user.id))
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_online=user.is_online,
        ai_score=user.ai_score,
        total_calls=user.total_calls,
        total_call_duration=user.total_call_duration,
        avg_fluency_score=user.avg_fluency_score,
        weaknesses=user.weaknesses,
        rank=rank
    )

@router.put("/update-score")
async def update_user_score(
    ai_score: float = None,
    fluency_score: float = None,
    weakness: str = None,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Update user's AI score and statistics"""
    db = Database.get_db()
    
    update_data = {"updated_at": datetime.utcnow()}
    
    if ai_score is not None:
        update_data["ai_score"] = ai_score
    
    if fluency_score is not None:
        # Calculate new average fluency score
        user_data = db.users.find_one({"_id": current_user.id})
        current_avg = user_data.get("avg_fluency_score", 0)
        total_calls = user_data.get("total_calls", 1)
        
        # Weighted average update
        new_avg = (current_avg * (total_calls - 1) + fluency_score) / total_calls
        update_data["avg_fluency_score"] = round(new_avg, 2)
    
    if weakness:
        # Add weakness if not already present
        db.users.update_one(
            {"_id": current_user.id},
            {"$addToSet": {"weaknesses": weakness}}
        )
    
    # Apply updates
    if update_data:
        db.users.update_one(
            {"_id": current_user.id},
            {"$set": update_data}
        )
    
    return {"message": "User score updated successfully"}

@router.get("/stats")
async def get_user_statistics(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get detailed user statistics"""
    db = Database.get_db()
    
    # Get user's calls data
    pipeline = [
        {"$match": {
            "$or": [
                {"caller_id": current_user.id},
                {"receiver_id": current_user.id}
            ],
            "status": "completed"
        }},
        {"$group": {
            "_id": None,
            "total_duration": {"$sum": "$duration_seconds"},
            "average_duration": {"$avg": "$duration_seconds"},
            "call_count": {"$sum": 1},
            "recent_calls": {
                "$push": {
                    "date": "$created_at",
                    "duration": "$duration_seconds"
                }
            }
        }}
    ]
    
    calls_stats = list(db.calls.aggregate(pipeline))
    
    # Get AI analysis stats
    analysis_pipeline = [
        {"$match": {"user_id": current_user.id}},
        {"$group": {
            "_id": None,
            "avg_grammar_errors": {"$avg": "$grammar_errors"},
            "avg_fluency": {"$avg": "$fluency_score"},
            "avg_wpm": {"$avg": "$words_per_minute"},
            "total_analyses": {"$sum": 1},
            "weakness_distribution": {"$push": "$weaknesses"}
        }}
    ]
    
    analysis_stats = list(db.ai_analysis.aggregate(analysis_pipeline))
    
    # Calculate improvement over time
    improvement_pipeline = [
        {"$match": {"user_id": current_user.id}},
        {"$sort": {"created_at": 1}},
        {"$group": {
            "_id": {
                "$dateToString": {"format": "%Y-%m", "date": "$created_at"}
            },
            "avg_score": {"$avg": "$overall_score"},
            "call_count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 6}
    ]
    
    improvement_data = list(db.ai_analysis.aggregate(improvement_pipeline))
    
    return {
        "calls_stats": calls_stats[0] if calls_stats else {},
        "analysis_stats": analysis_stats[0] if analysis_stats else {},
        "improvement_timeline": improvement_data,
        "current_rank": await calculate_user_rank(str(current_user.id)),
        "total_users": db.users.count_documents({})
    }

@router.get("/all", response_model=List[UserResponse])
async def get_all_users(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get all registered users excluding test accounts and current user"""
    db = Database.get_db()
    
    # Filter out test email addresses and current user
    test_emails = ["john@example.com", "jane@example.com", "bob@example.com"]
    
    users = db.users.find({
        "_id": {"$ne": current_user.id},
        "email": {"$nin": test_emails}
    })
    
    result = []
    for user in users:
        user_id_str = str(user["_id"])
        
        # Check online status from database (works across server instances)
        is_actually_online = is_user_online_db(user_id_str)
        
        rank = await calculate_user_rank(user_id_str)
        result.append(UserResponse(
            id=user_id_str,
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url"),
            is_online=is_actually_online,  # Use DB status for cross-instance compatibility
            ai_score=user.get("ai_score", 0.0),
            total_calls=user.get("total_calls", 0),
            total_call_duration=user.get("total_call_duration", 0),
            avg_fluency_score=user.get("avg_fluency_score", 0.0),
            weaknesses=user.get("weaknesses", []),
            rank=rank
        ))
    
    return result

@router.post("/logout")
async def logout(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Logout user and update online status"""
    db = Database.get_db()
    
    # Update online status
    db.users.update_one(
        {"_id": current_user.id},
        {"$set": {"is_online": False, "last_seen": datetime.utcnow()}}
    )
    
    return {"message": "Logged out successfully"}

@router.post("/friend-request/{user_id}")
async def send_friend_request(
    user_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Send a friend request to another user"""
    db = Database.get_db()
    
    # Prevent sending friend request to yourself
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    # Check if user exists
    target_user = db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already friends
    if ObjectId(user_id) in current_user.friends:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already friends with this user"
        )
    
    # Create friend request
    friend_request = {
        "from_user_id": current_user.id,
        "to_user_id": ObjectId(user_id),
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    # Check if request already exists
    existing_request = db.friend_requests.find_one({
        "from_user_id": current_user.id,
        "to_user_id": ObjectId(user_id),
        "status": "pending"
    })
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Friend request already sent"
        )
    
    db.friend_requests.insert_one(friend_request)
    
    # Send WebSocket notification to recipient
    from backend.app.api.websocket import manager
    await manager.send_personal_message({
        "type": "friend_request",
        "from_user_id": str(current_user.id),
        "sender_name": current_user.name,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)
    
    return {"message": "Friend request sent successfully"}

@router.get("/friend-requests")
async def get_friend_requests(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get all pending friend requests for the current user"""
    db = Database.get_db()
    
    # Get incoming requests
    incoming_requests = list(db.friend_requests.find({
        "to_user_id": current_user.id,
        "status": "pending"
    }))
    
    result = []
    for request in incoming_requests:
        from_user = db.users.find_one({"_id": request["from_user_id"]})
        if from_user:
            result.append({
                "request_id": str(request["_id"]),
                "from_user": {
                    "id": str(from_user["_id"]),
                    "name": from_user["name"],
                    "email": from_user["email"],
                    "avatar_url": from_user.get("avatar_url")
                },
                "created_at": request["created_at"]
            })
    
    return result

@router.post("/friend-request/{request_id}/accept")
async def accept_friend_request(
    request_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Accept a friend request"""
    db = Database.get_db()
    
    # Get friend request
    request = db.friend_requests.find_one({
        "_id": ObjectId(request_id),
        "to_user_id": current_user.id,
        "status": "pending"
    })
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    # Add friends to each other
    db.users.update_one(
        {"_id": current_user.id},
        {"$addToSet": {"friends": request["from_user_id"]}}
    )
    
    db.users.update_one(
        {"_id": request["from_user_id"]},
        {"$addToSet": {"friends": current_user.id}}
    )
    
    # Update request status
    db.friend_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}}
    )
    
    # Send WebSocket notification to the sender that their request was accepted
    from backend.app.api.websocket import manager
    sender_id = str(request["from_user_id"])
    await manager.send_personal_message({
        "type": "friend_request_accepted",
        "from_user_id": str(current_user.id),
        "accepter_name": current_user.name,
        "message": f"{current_user.name} accepted your friend request!",
        "timestamp": datetime.utcnow().isoformat()
    }, sender_id)
    
    return {"message": "Friend request accepted"}

@router.post("/friend-request/{request_id}/reject")
async def reject_friend_request(
    request_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Reject a friend request"""
    db = Database.get_db()
    
    # Get friend request
    request = db.friend_requests.find_one({
        "_id": ObjectId(request_id),
        "to_user_id": current_user.id,
        "status": "pending"
    })
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    # Update request status
    db.friend_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "rejected", "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Friend request rejected"}

@router.get("/friends", response_model=List[UserResponse])
async def get_friends(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get all friends of the current user"""
    db = Database.get_db()
    
    # Get current user's friends list
    user = db.users.find_one({"_id": current_user.id})
    friend_ids = user.get("friends", [])
    
    if not friend_ids:
        return []
    
    # Get friend details
    friends = db.users.find({"_id": {"$in": friend_ids}})
    
    result = []
    for friend in friends:
        friend_id_str = str(friend["_id"])
        
        # Check online status from database (works across server instances)
        is_actually_online = is_user_online_db(friend_id_str)
        
        rank = await calculate_user_rank(friend_id_str)
        result.append(UserResponse(
            id=friend_id_str,
            email=friend["email"],
            name=friend["name"],
            avatar_url=friend.get("avatar_url"),
            is_online=is_actually_online,  # Use DB status for cross-instance compatibility
            ai_score=friend.get("ai_score", 0.0),
            total_calls=friend.get("total_calls", 0),
            total_call_duration=friend.get("total_call_duration", 0),
            avg_fluency_score=friend.get("avg_fluency_score", 0.0),
            weaknesses=friend.get("weaknesses", []),
            rank=rank
        ))
    
    return result

@router.post("/unfriend/{user_id}")
async def unfriend_user(
    user_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Remove a friend (unfriend)"""
    db = Database.get_db()
    
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unfriend yourself"
        )
    
    target_user = db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove from both users' friend lists
    db.users.update_one(
        {"_id": current_user.id},
        {"$pull": {"friends": ObjectId(user_id)}}
    )
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"friends": current_user.id}}
    )
    
    # Remove any friend request records between them
    db.friend_requests.delete_many({
        "$or": [
            {"from_user_id": current_user.id, "to_user_id": ObjectId(user_id)},
            {"from_user_id": ObjectId(user_id), "to_user_id": current_user.id}
        ]
    })
    
    # Notify via WebSocket
    try:
        from backend.app.api.websocket import manager
        await manager.send_personal_message({
            "type": "unfriended",
            "by_user_id": str(current_user.id),
            "by_user_name": current_user.name,
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
    except Exception:
        pass
    
    return {"message": "Successfully unfriended"}

@router.get("/friend-status/{user_id}")
async def get_friend_status(
    user_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get the friendship status between current user and target user.
    Returns: 'friends', 'pending_sent', 'pending_received', or 'none'
    """
    db = Database.get_db()
    
    # Check if they are already friends
    current = db.users.find_one({"_id": current_user.id})
    current_friends = current.get("friends", [])
    
    # Convert to string list for comparison  
    friend_id_strs = [str(fid) for fid in current_friends]
    
    if user_id in friend_id_strs:
        return {"status": "friends"}
    
    # Check if there's a pending request FROM current user TO target
    pending_sent = db.friend_requests.find_one({
        "from_user_id": current_user.id,
        "to_user_id": ObjectId(user_id),
        "status": "pending"
    })
    if pending_sent:
        return {"status": "pending_sent", "request_id": str(pending_sent["_id"])}
    
    # Check if there's a pending request FROM target TO current user
    pending_received = db.friend_requests.find_one({
        "from_user_id": ObjectId(user_id),
        "to_user_id": current_user.id,
        "status": "pending"
    })
    if pending_received:
        return {"status": "pending_received", "request_id": str(pending_received["_id"])}
    
    return {"status": "none"}

@router.get("/friend-statuses")
async def get_all_friend_statuses(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get friendship status for all users in one call (batch).
    Returns a dict mapping user_id -> status
    """
    db = Database.get_db()
    
    # Get current user's friends
    current = db.users.find_one({"_id": current_user.id})
    current_friends = [str(fid) for fid in current.get("friends", [])]
    
    # Get all pending requests sent by current user
    sent_requests = list(db.friend_requests.find({
        "from_user_id": current_user.id,
        "status": "pending"
    }))
    sent_map = {str(r["to_user_id"]): str(r["_id"]) for r in sent_requests}
    
    # Get all pending requests received by current user
    received_requests = list(db.friend_requests.find({
        "to_user_id": current_user.id,
        "status": "pending"
    }))
    received_map = {str(r["from_user_id"]): str(r["_id"]) for r in received_requests}
    
    statuses = {}
    for fid in current_friends:
        statuses[fid] = {"status": "friends"}
    for uid, rid in sent_map.items():
        if uid not in statuses:
            statuses[uid] = {"status": "pending_sent", "request_id": rid}
    for uid, rid in received_map.items():
        if uid not in statuses:
            statuses[uid] = {"status": "pending_received", "request_id": rid}
    
    return {"statuses": statuses}

@router.get("/find-random-partner")
async def find_random_partner(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Deprecated: random calls now use real-time queue so both users explicitly opt in."""
    return {
        "message": "Random matching now uses the live queue. Click Find Random Partner to join queue.",
        "partner": None
    }

@router.post("/enroll-voice")
async def enroll_voice(
    audio: UploadFile = File(..., description="Voice recording (20-30s, WebM/WAV)"),
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
):
    """
    Enroll the current user's voice fingerprint.

    Accepts a 20-30 second audio recording, extracts MFCC-based voice features,
    and stores the fingerprint in the user's DB document.  This is called once
    on first login so the system can later identify the user's voice during calls.
    """
    import shutil
    import tempfile

    content_type = (audio.content_type or "").lower()
    if "wav" in content_type:
        suffix = ".wav"
    elif "ogg" in content_type:
        suffix = ".ogg"
    elif "mp4" in content_type or "m4a" in content_type:
        suffix = ".mp4"
    else:
        suffix = ".webm"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name

        file_size = os.path.getsize(tmp_path)
        if file_size < 10_000:  # < 10 KB is probably too short
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recording is too short. Please record at least 20 seconds of speech.",
            )

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        try:
            from backend.app.ai_processing.voice_fingerprint import (
                estimate_audio_duration_seconds,
                extract_voice_fingerprint,
            )
        except ModuleNotFoundError as dep_exc:
            missing_module = dep_exc.name or "required dependency"
            logger.error(
                "[VoiceEnroll] Missing dependency '%s' while enrolling user %s",
                missing_module,
                current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Voice enrollment dependency missing on server: {missing_module}. "
                    "Install backend requirements and restart the backend."
                ),
            ) from dep_exc

        duration_seconds = estimate_audio_duration_seconds(audio_bytes, suffix=suffix)
        if duration_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Could not decode audio. Please re-record in Chrome/Edge and try again. "
                    "Supported formats: WebM, WAV, OGG, MP4."
                ),
            )

        if duration_seconds < 20 or duration_seconds > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recording must be 20-30 seconds. Current length: {duration_seconds:.1f}s.",
            )

        enrollment_transcription = ""
        transcription_confidence = None
        transcription_note = ""
        enrollment_audio_url = ""

        # Persist latest enrollment recording for user-side audit/playback.
        try:
            enrollment_audio_url = _persist_voice_enrollment_audio(str(current_user.id), audio_bytes, suffix)
        except Exception as audio_save_exc:
            logger.warning("[VoiceEnroll] Could not save enrollment audio for user %s: %s", current_user.id, audio_save_exc)

        # Best-effort STT for auditability using the same faster-whisper pipeline.
        try:
            from backend.app.ai_processing.faster_whisper_stt import faster_whisper_stt

            transcription_text, confidence = faster_whisper_stt.transcribe(tmp_path, language="en")
            enrollment_transcription = (transcription_text or "").strip()
            if isinstance(confidence, (int, float)):
                transcription_confidence = round(float(confidence), 4)

            if not enrollment_transcription:
                transcription_note = (
                    "No clear speech detected for transcription. Please speak clearly and re-record if needed."
                )
                if not faster_whisper_stt.is_available():
                    transcription_note = "Server fast-whisper model is unavailable."
        except Exception as stt_exc:
            logger.warning(
                "[VoiceEnroll] STT preview unavailable for user %s: %s",
                current_user.id,
                stt_exc,
            )
            transcription_note = "Could not generate speech-to-text preview for this recording."

        fingerprint = extract_voice_fingerprint(audio_bytes, suffix=suffix)

        if fingerprint is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract voice features. Please re-record in a quiet environment.",
            )

        db = Database.get_db()
        now = datetime.now().astimezone()
        voice_id_label = f"VID-{str(current_user.id)[-6:].upper()}"

        # Atomic one-shot write to the authenticated user's document.
        updated_user = db.users.find_one_and_update(
            {"_id": current_user.id},
            {
                "$set": {
                    "voice_fingerprint": fingerprint,
                    "voice_enrollment_required": False,
                    "voice_fingerprint_enrolled": True,
                    "voice_fingerprint_enrolled_at": now,
                    "voice_fingerprint_duration_seconds": round(duration_seconds, 2),
                    "voice_enrollment_transcript": enrollment_transcription,
                    "voice_enrollment_transcript_confidence": transcription_confidence,
                    "voice_enrollment_transcript_generated_at": now,
                    "voice_enrollment_audio_url": enrollment_audio_url,
                    "voice_enrollment_audio_saved_at": now if enrollment_audio_url else None,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
            projection={
                "_id": 1,
                "voice_fingerprint": 1,
                "voice_fingerprint_enrolled": 1,
                "voice_fingerprint_enrolled_at": 1,
                "voice_enrollment_transcript": 1,
                "voice_enrollment_transcript_confidence": 1,
                "voice_enrollment_audio_url": 1,
            },
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found while saving voice enrollment.",
            )

        stored_fp = updated_user.get("voice_fingerprint")
        if not updated_user.get("voice_fingerprint_enrolled") or not isinstance(stored_fp, list) or not stored_fp:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Voice enrollment could not be persisted for this user.",
            )

        logger.info(
            "[VoiceEnroll] User %s enrolled (fp_dim=%d)", current_user.id, len(fingerprint)
        )
        return {
            "success": True,
            "message": "Voice ID enrolled successfully!",
            "voice_id_label": voice_id_label,
            "fingerprint_dimensions": len(fingerprint),
            "recording_duration_seconds": round(duration_seconds, 2),
            "enrolled_at": now.isoformat(),
            "enrollment_transcription": updated_user.get("voice_enrollment_transcript", "") or "",
            "transcription_confidence": updated_user.get("voice_enrollment_transcript_confidence"),
            "transcription_available": bool(updated_user.get("voice_enrollment_transcript")),
            "transcription_note": transcription_note,
            "enrollment_audio_url": updated_user.get("voice_enrollment_audio_url", "") or "",
            "user_id": str(updated_user["_id"]),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[VoiceEnroll] Failed for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice enrollment failed: {exc}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.get("/voice-enrollment-status")
async def voice_enrollment_status(
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
):
    """Return whether the current user has a stored voice fingerprint."""
    db = Database.get_db()
    user_doc = db.users.find_one(
        {"_id": current_user.id},
        {
            "voice_enrollment_required": 1,
            "voice_fingerprint_enrolled": 1,
            "voice_fingerprint_enrolled_at": 1,
            "voice_enrollment_transcript": 1,
            "voice_enrollment_transcript_confidence": 1,
            "voice_enrollment_audio_url": 1,
        },
    )
    enrolled = bool(user_doc and user_doc.get("voice_fingerprint_enrolled", False))
    required = bool(user_doc and user_doc.get("voice_enrollment_required", False)) and not enrolled
    enrolled_at = None
    if enrolled and user_doc.get("voice_fingerprint_enrolled_at"):
        raw_enrolled_at = user_doc["voice_fingerprint_enrolled_at"]
        if raw_enrolled_at.tzinfo is None:
            raw_enrolled_at = raw_enrolled_at.replace(tzinfo=timezone.utc)
        enrolled_at = raw_enrolled_at.astimezone().isoformat()
    voice_id_label = f"VID-{str(current_user.id)[-6:].upper()}"
    return {
        "enrolled": enrolled,
        "required": required,
        "voice_id_label": voice_id_label,
        "enrolled_at": enrolled_at,
        "last_enrollment_transcription": (user_doc or {}).get("voice_enrollment_transcript", "") if user_doc else "",
        "last_enrollment_transcription_confidence": (user_doc or {}).get("voice_enrollment_transcript_confidence") if user_doc else None,
        "last_enrollment_audio_url": (user_doc or {}).get("voice_enrollment_audio_url", "") if user_doc else "",
    }


@router.get("/debug/db-status")
async def debug_db_status():
    """Debug endpoint to check database status"""
    try:
        db = Database.get_db()
        
        # Count users
        user_count = db.users.count_documents({})
        
        # Get sample user (without sensitive data)
        sample_users = list(db.users.find({}, {"email": 1, "_id": 1}).limit(3))
        
        # Database info
        db_info = {
            "status": "connected",
            "database_name": db.name,
            "user_count": user_count,
            "sample_user_emails": [u.get("email") for u in sample_users],
            "mongodb_url_configured": os.getenv("MONGODB_URL") is not None,
            "environment": os.getenv("ENVIRONMENT", "development")
        }
        
        return db_info
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "mongodb_url_configured": os.getenv("MONGODB_URL") is not None
        }

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get user profile by ID"""
    db = Database.get_db()
    
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check online status from database (works across server instances)
        is_actually_online = is_user_online_db(user_id)
        
        rank = await calculate_user_rank(user_id)
        
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url"),
            is_online=is_actually_online,  # Use DB status for cross-instance compatibility
            ai_score=user.get("ai_score", 0.0),
            total_calls=user.get("total_calls", 0),
            total_call_duration=user.get("total_call_duration", 0),
            avg_fluency_score=user.get("avg_fluency_score", 0.0),
            weaknesses=user.get("weaknesses", []),
            rank=rank
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID: {str(e)}"
        )