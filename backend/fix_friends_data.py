from app.database import Database
from bson import ObjectId
from datetime import datetime, timezone

db = Database.get_db()

print("=" * 60)
print("FIXING FRIENDS DATA")
print("=" * 60)

# Remove self-references from friends lists
users = list(db.users.find({}, {"_id": 1, "name": 1, "friends": 1}))

for user in users:
    user_id = user["_id"]
    friends = user.get("friends", [])
    
    # Check if user's own ID is in friends list
    if user_id in friends:
        print(f"\n❌ Found self-reference for {user['name']}")
        print(f"   Before: {[str(f) for f in friends]}")
        
        # Remove self-reference
        friends.remove(user_id)
        
        # Update database
        db.users.update_one(
            {"_id": user_id},
            {"$set": {"friends": friends}}
        )
        
        print(f"   After:  {[str(f) for f in friends]}")
        print(f"   ✅ Fixed!")

print("\n" + "=" * 60)
print("RESETTING ONLINE STATUS")  
print("=" * 60)

# Reset all users to offline
result = db.users.update_many(
    {},
    {"$set": {"is_online": False, "last_seen": datetime.now(timezone.utc)}}
)
print(f"✅ Set {result.modified_count} users to offline")

print("\n" + "=" * 60)
print("✅ ALL FIXES APPLIED!")
print("=" * 60)
