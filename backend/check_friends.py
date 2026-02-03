from app.database import Database
from bson import ObjectId

# Check friends data
db = Database.get_db()

print("=" * 60)
print("CHECKING FRIENDS DATA")
print("=" * 60)

users = list(db.users.find({}, {"_id": 1, "name": 1, "email": 1, "friends": 1, "is_online": 1}))

for user in users:
    user_id = str(user["_id"])
    friends = user.get("friends", [])
    is_online = user.get("is_online", False)
    
    print(f"\nUser: {user['name']} ({user['email']})")
    print(f"  ID: {user_id}")
    print(f"  Online: {is_online}")
    print(f"  Friends list: {[str(f) for f in friends]}")
    
    # Check if user's own ID is in friends list
    if ObjectId(user_id) in friends:
        print(f"  ⚠️  WARNING: User's own ID is in their friends list!")
    
    # Check for duplicates
    if len(friends) != len(set(friends)):
        print(f"  ⚠️  WARNING: Duplicate friends detected!")

print("\n" + "=" * 60)
