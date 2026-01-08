from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    client = None
    db = None
    
    @classmethod
    def connect(cls):
        """Connect to MongoDB"""
        try:
            cls.client = MongoClient(
                os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            cls.client.admin.command('ping')
            cls.db = cls.client[os.getenv("DB_NAME", "english_comm")]
            print("Connected to MongoDB successfully")
        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            raise
    
    @classmethod
    def disconnect(cls):
        """Disconnect from MongoDB"""
        if cls.client:
            cls.client.close()
            print("Disconnected from MongoDB")
    
    @classmethod
    def get_db(cls):
        """Get database instance"""
        if cls.db is None:
            cls.connect()
        return cls.db

async def init_db():
    """Initialize database connection and indexes"""
    db = Database.get_db()
    
    # Create indexes
    db.users.create_index("email", unique=True)
    db.users.create_index("ai_score")
    db.calls.create_index([("caller_id", 1), ("receiver_id", 1)])
    db.calls.create_index("status")
    db.ai_analysis.create_index("user_id")
    db.ai_analysis.create_index("call_id", unique=True)
    
    print("Database indexes created")