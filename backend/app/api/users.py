from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from datetime import datetime
from typing import List
from bson import ObjectId
import shutil
import os

from backend.app.schemas import UserRegisterRequest, UserLoginRequest, UserResponse
from backend.app.models import UserInDB
from backend.app.auth import AuthHandler
from backend.app.database import Database
from backend.app.core.config import settings

router = APIRouter()

# Helper function to calculate user rank
async def calculate_user_rank(user_id: str) -> int:
    db = Database.get_db()
    test_emails = ["john@example.com", "jane@example.com", "bob@example.com"]
    all_users = list(db.users.find({"email": {"$nin": test_emails}}).sort("ai_score", -1))
    rank = next((i + 1 for i, u in enumerate(all_users) if str(u["_id"]) == user_id), None)
    return rank

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegisterRequest):
    """Register a new user"""
    db = Database.get_db()
    
    # Check if user already exists
    if db.users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = AuthHandler.hash_password(user_data.password)
    
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
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
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

@router.post("/login")
async def login(user_data: UserLoginRequest):
    """Login user and return access token"""
    db = Database.get_db()
    
    # Find user
    user = db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Get password hash (handle both old and new field names)
    password_hash = user.get("hashed_password") or user.get("password_hash")
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    
    # Verify password
    if not AuthHandler.verify_password(user_data.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
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
    
    return {
        "access_token": token,
        "token_type": "bearer",
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
        rank = await calculate_user_rank(str(user["_id"]))
        result.append(UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url"),
            is_online=user.get("is_online", False),
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
        rank = await calculate_user_rank(str(friend["_id"]))
        result.append(UserResponse(
            id=str(friend["_id"]),
            email=friend["email"],
            name=friend["name"],
            avatar_url=friend.get("avatar_url"),
            is_online=friend.get("is_online", False),
            ai_score=friend.get("ai_score", 0.0),
            total_calls=friend.get("total_calls", 0),
            total_call_duration=friend.get("total_call_duration", 0),
            avg_fluency_score=friend.get("avg_fluency_score", 0.0),
            weaknesses=friend.get("weaknesses", []),
            rank=rank
        ))
    
    return result

@router.get("/find-random-partner")
async def find_random_partner(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Find a random online partner for calling"""
    db = Database.get_db()
    
    # Filter out test emails and current user, get only online users
    test_emails = ["john@example.com", "jane@example.com", "bob@example.com"]
    
    # Find online users who are not the current user
    online_users = list(db.users.find({
        "_id": {"$ne": current_user.id},
        "email": {"$nin": test_emails},
        "is_online": True
    }))
    
    if not online_users:
        return {"message": "No online partners available", "partner": None}
    
    # Get a random user
    import random
    random_partner = random.choice(online_users)
    
    return {
        "partner": {
            "id": str(random_partner["_id"]),
            "name": random_partner["name"],
            "email": random_partner["email"],
            "avatar_url": random_partner.get("avatar_url"),
            "ai_score": random_partner.get("ai_score", 0.0)
        }
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
        
        rank = await calculate_user_rank(user_id)
        
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url"),
            is_online=user.get("is_online", False),
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