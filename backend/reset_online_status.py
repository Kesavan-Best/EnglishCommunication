from app.database import Database
from datetime import datetime, timezone

# Reset all users to offline
db = Database.get_db()
result = db.users.update_many(
    {},
    {"$set": {"is_online": False, "last_seen": datetime.now(timezone.utc)}}
)
print(f"✅ Updated {result.modified_count} users to offline status")
