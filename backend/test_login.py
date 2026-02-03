"""Test login with Render-created account"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Database
import bcrypt

# The account created on Render
test_email = "abc@gmail.com"
test_password = input(f"Enter the password for {test_email}: ")

db = Database.get_db()
user = db.users.find_one({'email': test_email})

print("\n" + "="*70)
print(f"Testing login for: {test_email}")
print("="*70)

if not user:
    print("❌ User NOT found in MongoDB Atlas!")
else:
    print(f"✅ User found in database")
    print(f"   Email: {user['email']}")
    print(f"   Name: {user['name']}")
    
    # Check password hash
    password_hash = user.get('hashed_password') or user.get('password_hash')
    if not password_hash:
        print("❌ No password hash found!")
    else:
        print(f"✅ Password hash exists")
        
        # Try to verify password
        is_valid = bcrypt.checkpw(test_password.encode('utf-8'), password_hash.encode('utf-8'))
        if is_valid:
            print("✅ Password verification SUCCESSFUL!")
        else:
            print("❌ Password verification FAILED!")
            print("   The password you entered doesn't match.")

print("="*70)
