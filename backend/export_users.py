"""Export users from local MongoDB to JSON file"""
import json
import sys
from pathlib import Path

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app.database import Database
from bson import ObjectId

def export_users():
    """Export all users from MongoDB"""
    try:
        db = Database.get_db()
        
        # Get all users
        users = list(db.users.find({}))
        print(f"Found {len(users)} users in local database")
        
        # Convert ObjectId to string for JSON serialization
        for user in users:
            if '_id' in user:
                user['_id'] = str(user['_id'])
            # Convert any other ObjectId fields
            for key, value in user.items():
                if isinstance(value, ObjectId):
                    user[key] = str(value)
        
        # Save to JSON file
        output_file = "users_export.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, default=str)
        
        print(f"\nUsers exported successfully to: {output_file}")
        print("\nSample user data:")
        for user in users[:3]:  # Show first 3 users
            print(f"  - {user.get('email')} (Name: {user.get('name')})")
        
        return users
        
    except Exception as e:
        print(f"Error exporting users: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    export_users()
