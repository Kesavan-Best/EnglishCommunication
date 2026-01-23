"""
Script to reset all users' call counts to 0
Run this with: python reset_call_counts.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import Database

def reset_call_counts():
    """Reset all users' call counts to 0"""
    db = Database.get_db()
    
    result = db.users.update_many(
        {},
        {
            "$set": {
                "total_calls": 0,
                "total_call_duration": 0,
                "ai_score": 0.0,
                "avg_fluency_score": 0.0
            }
        }
    )
    
    print(f"✅ Reset call counts for {result.modified_count} users")
    print("All users now have:")
    print("  - total_calls: 0")
    print("  - total_call_duration: 0")
    print("  - ai_score: 0.0")
    print("  - avg_fluency_score: 0.0")

if __name__ == "__main__":
    print("🔄 Resetting all user call counts...")
    reset_call_counts()
    print("✅ Done!")
