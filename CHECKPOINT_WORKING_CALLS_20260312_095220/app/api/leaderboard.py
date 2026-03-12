from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional

from backend.app.auth import AuthHandler
from backend.app.database import Database
from backend.app.models import UserInDB
from backend.app.schemas import LeaderboardEntry

router = APIRouter()

@router.get("/top", response_model=List[LeaderboardEntry])
async def get_top_leaderboard(
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
    limit: int = 10,
    timeframe: str = "all",  # all, weekly, monthly, daily
    skill_filter: Optional[str] = None  # grammar, fluency, vocabulary
):
    """Get top users leaderboard with filters"""
    db = Database.get_db()
    
    # Filter out test email addresses
    test_emails = ["john@example.com", "jane@example.com", "bob@example.com"]
    
    # Time filter
    time_filter = {}
    now = datetime.utcnow()
    
    if timeframe == "daily":
        time_filter = {"updated_at": {"$gte": now - timedelta(days=1)}}
    elif timeframe == "weekly":
        time_filter = {"updated_at": {"$gte": now - timedelta(days=7)}}
    elif timeframe == "monthly":
        time_filter = {"updated_at": {"$gte": now - timedelta(days=30)}}
    
    # Base pipeline - exclude test emails
    pipeline = [
        {"$match": {"ai_score": {"$gt": 0}, "email": {"$nin": test_emails}}},
        {"$match": time_filter} if time_filter else {"$match": {}},
        {"$sort": {"ai_score": -1}},
        {"$limit": limit},
        {"$project": {
            "_id": 1,
            "name": 1,
            "avatar_url": 1,
            "ai_score": 1,
            "total_calls": 1,
            "avg_fluency_score": 1,
            "weaknesses": 1,
            "total_call_duration": 1
        }}
    ]
    
    # Apply skill filter
    if skill_filter:
        if skill_filter == "grammar":
            # Get users with grammar analysis data
            analysis_pipeline = [
                {"$match": {"grammar_errors": {"$exists": True}}},
                {"$group": {
                    "_id": "$user_id",
                    "grammar_score": {"$avg": {"$subtract": [100, {"$multiply": ["$grammar_errors", 5]}]}}
                }},
                {"$sort": {"grammar_score": -1}},
                {"$limit": limit}
            ]
            
            analysis_results = list(db.ai_analysis.aggregate(analysis_pipeline))
            user_ids = [ObjectId(r["_id"]) for r in analysis_results]
            
            pipeline.insert(0, {"$match": {"_id": {"$in": user_ids}}})
            
        elif skill_filter == "fluency":
            pipeline[2] = {"$sort": {"avg_fluency_score": -1}}
        elif skill_filter == "activity":
            pipeline[2] = {"$sort": {"total_calls": -1}}
    
    leaderboard = []
    cursor = db.users.aggregate(pipeline)
    
    for rank, user_data in enumerate(cursor, 1):
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            user_id=str(user_data["_id"]),
            name=user_data["name"],
            avatar_url=user_data.get("avatar_url"),
            ai_score=user_data["ai_score"],
            total_calls=user_data["total_calls"],
            avg_fluency_score=user_data.get("avg_fluency_score", 0)
        ))
    
    return leaderboard

@router.get("/my-rank")
async def get_my_rank(
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
    timeframe: str = "all"
):
    """Get current user's rank with detailed position"""
    db = Database.get_db()
    
    # Time filter
    time_filter = {}
    now = datetime.utcnow()
    
    if timeframe == "daily":
        time_filter = {"updated_at": {"$gte": now - timedelta(days=1)}}
    elif timeframe == "weekly":
        time_filter = {"updated_at": {"$gte": now - timedelta(days=7)}}
    elif timeframe == "monthly":
        time_filter = {"updated_at": {"$gte": now - timedelta(days=30)}}
    
    # Get all users sorted by AI score with time filter
    query = {"ai_score": {"$gt": 0}}
    if time_filter:
        query.update(time_filter)
    
    all_users = list(db.users.find(
        query,
        {"_id": 1, "ai_score": 1, "name": 1}
    ).sort("ai_score", -1))
    
    # Find user's position
    user_rank = 1
    for idx, user in enumerate(all_users, 1):
        if str(user["_id"]) == str(current_user.id):
            user_rank = idx
            break
    
    # Calculate percentiles
    total_users = len(all_users)
    percentile = ((total_users - user_rank) / total_users * 100) if total_users > 0 else 0
    
    # Get users above and below
    context_size = 2
    start_idx = max(0, user_rank - context_size - 1)
    end_idx = min(total_users, user_rank + context_size)
    
    context_users = []
    for i in range(start_idx, end_idx):
        if i < len(all_users):
            context_users.append({
                "rank": i + 1,
                "name": all_users[i]["name"],
                "ai_score": all_users[i]["ai_score"],
                "is_me": str(all_users[i]["_id"]) == str(current_user.id)
            })
    
    return {
        "rank": user_rank,
        "total_users": total_users,
        "percentile": round(percentile, 2),
        "ai_score": current_user.ai_score,
        "context": context_users,
        "timeframe": timeframe
    }

@router.get("/around-me", response_model=List[LeaderboardEntry])
async def get_leaderboard_around_me(
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
    range_size: int = 3
):
    """Get leaderboard entries around current user"""
    db = Database.get_db()
    
    # Get user's rank
    higher_scorers = db.users.count_documents({
        "ai_score": {"$gt": current_user.ai_score}
    })
    user_rank = higher_scorers + 1
    
    # Calculate range
    start_rank = max(1, user_rank - range_size)
    end_rank = user_rank + range_size
    
    # Get users in range
    pipeline = [
        {"$match": {"ai_score": {"$gt": 0}}},
        {"$sort": {"ai_score": -1}},
        {"$skip": start_rank - 1},
        {"$limit": end_rank - start_rank + 1},
        {"$project": {
            "_id": 1,
            "name": 1,
            "avatar_url": 1,
            "ai_score": 1,
            "total_calls": 1,
            "avg_fluency_score": 1
        }}
    ]
    
    leaderboard = []
    cursor = db.users.aggregate(pipeline)
    
    for idx, user_data in enumerate(cursor, start_rank):
        leaderboard.append(LeaderboardEntry(
            rank=idx,
            user_id=str(user_data["_id"]),
            name=user_data["name"],
            avatar_url=user_data.get("avatar_url"),
            ai_score=user_data["ai_score"],
            total_calls=user_data["total_calls"],
            avg_fluency_score=user_data.get("avg_fluency_score", 0)
        ))
    
    return leaderboard

@router.get("/achievements/{user_id}")
async def get_user_achievements(
    user_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get user's achievements and badges"""
    db = Database.get_db()
    
    try:
        target_user_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Get user data
    user_data = db.users.find_one({"_id": target_user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate achievements
    achievements = []
    
    # Call count achievements
    total_calls = user_data.get("total_calls", 0)
    if total_calls >= 1:
        achievements.append({
            "name": "First Call",
            "description": "Completed your first practice call",
            "icon": "🎤",
            "unlocked": True,
            "date": user_data.get("created_at")
        })
    if total_calls >= 5:
        achievements.append({
            "name": "Practice Enthusiast",
            "description": "Completed 5 practice calls",
            "icon": "🔥",
            "unlocked": True
        })
    if total_calls >= 25:
        achievements.append({
            "name": "Conversation Master",
            "description": "Completed 25 practice calls",
            "icon": "👑",
            "unlocked": True if total_calls >= 25 else False
        })
    
    # Score achievements
    ai_score = user_data.get("ai_score", 0)
    if ai_score >= 70:
        achievements.append({
            "name": "Good Communicator",
            "description": "Reached AI score of 70+",
            "icon": "⭐",
            "unlocked": True
        })
    if ai_score >= 85:
        achievements.append({
            "name": "Excellent Speaker",
            "description": "Reached AI score of 85+",
            "icon": "🌟",
            "unlocked": True if ai_score >= 85 else False
        })
    
    # Duration achievements
    total_duration = user_data.get("total_call_duration", 0)
    if total_duration >= 3600:  # 1 hour
        achievements.append({
            "name": "Hour of Practice",
            "description": "Completed 1 hour of practice calls",
            "icon": "⏱️",
            "unlocked": True
        })
    
    # Streak achievement (simplified - would need daily call tracking)
    # Get recent calls for streak calculation
    recent_calls = list(db.calls.find({
        "$or": [
            {"caller_id": target_user_id},
            {"receiver_id": target_user_id}
        ],
        "status": "completed",
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=7)}
    }).sort("created_at", -1))
    
    if len(recent_calls) >= 3:
        achievements.append({
            "name": "Consistent Learner",
            "description": "Practiced 3 days in a row",
            "icon": "📅",
            "unlocked": True
        })
    
    return {
        "user_id": user_id,
        "user_name": user_data.get("name"),
        "total_achievements": len(achievements),
        "achievements": achievements,
        "progress": {
            "calls": total_calls,
            "score": ai_score,
            "duration": total_duration,
            "streak": len(recent_calls)
        }
    }

@router.get("/global-stats")
async def get_global_statistics(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get global platform statistics"""
    db = Database.get_db()
    
    # Total users count
    total_users = db.users.count_documents({})
    active_users = db.users.count_documents({
        "last_seen": {"$gte": datetime.utcnow() - timedelta(days=7)}
    })
    
    # Total calls statistics
    calls_stats = list(db.calls.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "total_duration": {"$sum": "$duration_seconds"},
            "avg_duration": {"$avg": "$duration_seconds"}
        }}
    ]))
    
    # Average AI score
    avg_score_result = list(db.users.aggregate([
        {"$match": {"ai_score": {"$gt": 0}}},
        {"$group": {
            "_id": None,
            "avg_score": {"$avg": "$ai_score"},
            "max_score": {"$max": "$ai_score"},
            "min_score": {"$min": "$ai_score"}
        }}
    ]))
    
    # Top 3 users
    top_users = list(db.users.find(
        {"ai_score": {"$gt": 0}},
        {"_id": 1, "name": 1, "ai_score": 1, "avatar_url": 1}
    ).sort("ai_score", -1).limit(3))
    
    # Most active users (by calls)
    active_pipeline = [
        {"$match": {"status": "completed"}},
        {"$facet": {
            "callers": [
                {"$group": {
                    "_id": "$caller_id",
                    "call_count": {"$sum": 1}
                }},
                {"$sort": {"call_count": -1}},
                {"$limit": 5}
            ],
            "receivers": [
                {"$group": {
                    "_id": "$receiver_id",
                    "call_count": {"$sum": 1}
                }},
                {"$sort": {"call_count": -1}},
                {"$limit": 5}
            ]
        }}
    ]
    
    activity_result = list(db.calls.aggregate(active_pipeline))
    
    # Convert ObjectIds in activity result
    most_active = {}
    if activity_result:
        result = activity_result[0]
        most_active = {
            "callers": [
                {
                    "user_id": str(item["_id"]),
                    "call_count": item["call_count"]
                }
                for item in result.get("callers", [])
            ],
            "receivers": [
                {
                    "user_id": str(item["_id"]),
                    "call_count": item["call_count"]
                }
                for item in result.get("receivers", [])
            ]
        }
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "calls_stats": calls_stats[0] if calls_stats else {},
        "score_stats": avg_score_result[0] if avg_score_result else {},
        "top_users": [
            {
                "id": str(user["_id"]),
                "name": user["name"],
                "score": user["ai_score"],
                "avatar": user.get("avatar_url")
            }
            for user in top_users
        ],
        "most_active": most_active,
        "updated_at": datetime.utcnow().isoformat()
    }