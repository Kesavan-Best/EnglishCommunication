# english_communication/backend/init_db.py
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from app.database import Database
from pymongo import MongoClient
from datetime import datetime
import bcrypt

def initialize_database():
    print("🚀 Initializing MongoDB for English Communication Platform...")
    
    # Connect directly
    client = MongoClient("mongodb://localhost:27017/")
    db = client["english_comm"]
    
    # Check connection
    try:
        client.admin.command('ping')
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ Cannot connect to MongoDB: {e}")
        return False
    
    # Clear existing data (optional - for fresh start)
    print("\n📦 Setting up database collections...")
    collections = ['users', 'calls', 'transcripts', 'ai_analysis', 'feedback', 'quizzes']
    
    for collection in collections:
        if collection in db.list_collection_names():
            db[collection].drop()
            print(f"   Cleared existing '{collection}' collection")
    
    # Create Users with hashed passwords
    print("\n👥 Creating sample users...")
    
    # Password for all test users: "password123"
    hashed_password = bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode()
    
    users = [
        {
            "email": "john@example.com",
            "password_hash": hashed_password,
            "name": "John Doe",
            "avatar_url": None,
            "is_online": True,
            "last_seen": datetime.utcnow(),
            "ai_score": 85.5,
            "total_calls": 12,
            "total_call_duration": 3600,
            "avg_fluency_score": 78.2,
            "weaknesses": ["grammar", "filler_words"],
            "friends": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "email": "jane@example.com",
            "password_hash": hashed_password,
            "name": "Jane Smith",
            "avatar_url": None,
            "is_online": False,
            "last_seen": datetime.utcnow(),
            "ai_score": 92.3,
            "total_calls": 25,
            "total_call_duration": 7200,
            "avg_fluency_score": 88.5,
            "weaknesses": ["vocabulary_repetition"],
            "friends": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "email": "bob@example.com",
            "password_hash": hashed_password,
            "name": "Bob Wilson",
            "avatar_url": None,
            "is_online": True,
            "last_seen": datetime.utcnow(),
            "ai_score": 67.8,
            "total_calls": 8,
            "total_call_duration": 1800,
            "avg_fluency_score": 65.4,
            "weaknesses": ["grammar", "fluency", "pauses"],
            "friends": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = db.users.insert_many(users)
    print(f"✅ Created {len(result.inserted_ids)} sample users")
    
    # Create indexes
    print("\n🔧 Creating database indexes...")
    db.users.create_index("email", unique=True)
    db.users.create_index("ai_score")
    db.users.create_index("is_online")
    print("✅ User indexes created")
    
    # Create a sample call
    print("\n📞 Creating sample call data...")
    from bson import ObjectId
    
    call_data = {
        "caller_id": result.inserted_ids[0],  # John
        "receiver_id": result.inserted_ids[1],  # Jane
        "status": "completed",
        "jitsi_room_id": "english-comm-sample-room",
        "start_time": datetime.utcnow(),
        "end_time": datetime.utcnow(),
        "duration_seconds": 300,
        "audio_url": None,
        "transcript_id": None,
        "analysis_id": None,
        "created_at": datetime.utcnow()
    }
    
    call_result = db.calls.insert_one(call_data)
    print("✅ Sample call created")
    
    # Create indexes for calls
    db.calls.create_index([("caller_id", 1), ("receiver_id", 1)])
    db.calls.create_index("status")
    
    print("\n" + "="*50)
    print("🎉 DATABASE INITIALIZATION COMPLETE!")
    print("="*50)
    print("\n📋 Test Credentials:")
    print("   Email: john@example.com | Password: password123")
    print("   Email: jane@example.com | Password: password123")
    print("   Email: bob@example.com  | Password: password123")
    print("\n🔗 Database: english_comm")
    print("📊 Total users: 3")
    print("\n🚀 Next: Start the backend server with 'python main.py'")
    
    client.close()
    return True

if __name__ == "__main__":
    initialize_database()