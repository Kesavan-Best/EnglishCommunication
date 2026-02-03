"""Import users from JSON file to MongoDB Atlas"""
import json
import sys
from pathlib import Path
from pymongo import MongoClient
from datetime import datetime

def import_users_to_atlas():
    """Import users from users_export.json to MongoDB Atlas"""
    
    # MongoDB Atlas connection string
    MONGODB_URL = "mongodb+srv://english_admin:KendallJenner@communication.btgwj0j.mongodb.net/?appName=Communication"
    DB_NAME = "english_comm"
    
    try:
        print("Connecting to MongoDB Atlas...")
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=30000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        
        db = client[DB_NAME]
        
        # Read exported users
        print("\nReading users_export.json...")
        with open('users_export.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        print(f"Found {len(users)} users to import")
        
        # Check existing users
        existing_count = db.users.count_documents({})
        print(f"Current users in Atlas database: {existing_count}")
        
        if existing_count > 0:
            response = input("\n⚠️  Database already has users. Clear and re-import? (yes/no): ")
            if response.lower() == 'yes':
                result = db.users.delete_many({})
                print(f"Deleted {result.deleted_count} existing users")
        
        # Import users
        print("\nImporting users...")
        imported = 0
        skipped = 0
        
        for user in users:
            # Remove _id from export (MongoDB will create new ones)
            if '_id' in user:
                del user['_id']
            
            # Convert string dates back to datetime if needed
            for field in ['created_at', 'updated_at', 'last_seen']:
                if field in user and isinstance(user[field], str):
                    try:
                        user[field] = datetime.fromisoformat(user[field].replace('Z', '+00:00'))
                    except:
                        user[field] = datetime.utcnow()
            
            # Check if user already exists
            existing = db.users.find_one({"email": user['email']})
            if existing:
                print(f"  ⚠️  Skipped: {user['email']} (already exists)")
                skipped += 1
            else:
                db.users.insert_one(user)
                print(f"  ✅ Imported: {user['email']} (Name: {user.get('name')})")
                imported += 1
        
        print(f"\n{'='*60}")
        print(f"Import Complete!")
        print(f"  ✅ Imported: {imported} users")
        print(f"  ⚠️  Skipped: {skipped} users (already existed)")
        print(f"  📊 Total in database: {db.users.count_documents({})}")
        print(f"{'='*60}")
        
        # Show all users in database
        print("\nUsers in MongoDB Atlas:")
        all_users = list(db.users.find({}, {"email": 1, "name": 1}))
        for i, user in enumerate(all_users, 1):
            print(f"  {i}. {user.get('email')} - {user.get('name')}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import_users_to_atlas()
