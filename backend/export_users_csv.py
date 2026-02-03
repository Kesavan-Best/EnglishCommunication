"""Export all users to a readable CSV file"""
from app.database import Database
import csv

db = Database.get_db()
all_users = list(db.users.find({}, {
    'email': 1, 
    'name': 1, 
    'created_at': 1, 
    'total_calls': 1,
    'ai_score': 1
}))

# Save to CSV
with open('users_list.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Email', 'Name', 'Created At', 'Total Calls', 'AI Score'])
    
    for user in all_users:
        writer.writerow([
            user.get('email', ''),
            user.get('name', ''),
            user.get('created_at', ''),
            user.get('total_calls', 0),
            user.get('ai_score', 0.0)
        ])

print(f"✅ Exported {len(all_users)} users to users_list.csv")
print(f"   File location: E:\\english_communication\\backend\\users_list.csv")
