"""Test MongoDB Atlas connection from localhost"""
from app.database import Database

db = Database.get_db()
count = db.users.count_documents({})

print("=" * 60)
print("✅ Connected to MongoDB Atlas successfully!")
print("=" * 60)
print(f"Total users in database: {count}")
print("\nSample users:")

users = list(db.users.find({}, {'email': 1, 'name': 1}).limit(6))
for i, user in enumerate(users, 1):
    print(f"  {i}. {user['email']} - {user['name']}")

print("=" * 60)
print("🎉 Localhost is now using MongoDB Atlas!")
print("=" * 60)
