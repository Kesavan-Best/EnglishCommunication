"""Check all accounts in MongoDB Atlas"""
from app.database import Database

db = Database.get_db()
all_users = list(db.users.find({}, {'email': 1, 'name': 1, 'created_at': 1}))

print("=" * 70)
print(f"Total users in MongoDB Atlas: {len(all_users)}")
print("=" * 70)

for i, user in enumerate(all_users, 1):
    created = user.get('created_at', 'Unknown')
    print(f"{i}. {user['email']:40} | {user['name']:20} | Created: {created}")

print("=" * 70)
