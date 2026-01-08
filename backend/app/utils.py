import os
import uuid
from datetime import datetime
from typing import Optional
import json
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB ObjectId and datetime"""
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def generate_unique_filename(extension: str = "webm") -> str:
    """Generate a unique filename with timestamp"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}.{extension}"

def ensure_directory(path: str):
    """Ensure directory exists, create if not"""
    os.makedirs(path, exist_ok=True)

def calculate_ai_score(user_data: dict) -> float:
    """
    Calculate AI communication score based on user metrics
    
    Args:
        user_data: User document from database
    
    Returns:
        AI score (0-100)
    """
    base_score = 50.0
    
    # Adjust based on call count
    total_calls = user_data.get("total_calls", 0)
    if total_calls > 0:
        base_score += min(20, total_calls * 0.5)
    
    # Adjust based on average fluency
    avg_fluency = user_data.get("avg_fluency_score", 0)
    base_score += avg_fluency * 0.3
    
    # Adjust based on weaknesses count
    weaknesses = user_data.get("weaknesses", [])
    base_score -= len(weaknesses) * 5
    
    # Ensure score stays within bounds
    return max(0.0, min(100.0, base_score))

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining = seconds % 60
        return f"{minutes}m {remaining}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"