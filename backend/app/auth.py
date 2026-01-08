from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

from app.database import Database
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models import UserInDB, UserPublic, Token
from app.core.config import settings

security = HTTPBearer()

class AuthHandler:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return get_password_hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return verify_password(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(user_id: str) -> str:
        """Create JWT access token for a user"""
        return create_access_token(data={"sub": user_id})
    
    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with email and password"""
        db = Database.get_db()
        user_data = db.users.find_one({"email": email})
        
        if not user_data:
            return None
        
        user = UserInDB(**user_data)
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    async def register_user(user_data: dict) -> UserInDB:
        """Register new user"""
        db = Database.get_db()
        
        # Check if user already exists
        if db.users.find_one({"email": user_data["email"]}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user document
        user = UserInDB(
            email=user_data["email"],
            name=user_data["name"],
            password_hash=user_data["password_hash"]
        )
        
        # Insert into database
        result = db.users.insert_one(user.dict(by_alias=True))
        user.id = result.inserted_id
        
        return user
    
    @staticmethod
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> UserInDB:
        """Get current user from JWT token"""
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        db = Database.get_db()
        user_data = db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Handle both password_hash and hashed_password fields
        if "hashed_password" in user_data and "password_hash" not in user_data:
            user_data["password_hash"] = user_data["hashed_password"]
        
        # Update last seen
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_seen": datetime.utcnow(), "is_online": True}}
        )
        
        return UserInDB(**user_data)
    
    @staticmethod
    async def create_token_for_user(user: UserInDB) -> Token:
        """Create JWT token for user"""
        access_token = create_access_token(
            data={"sub": str(user.id)}
        )
        
        # Convert to public user model
        public_user = UserPublic(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_online=user.is_online,
            ai_score=user.ai_score,
            total_calls=user.total_calls
        )
        
        return Token(
            access_token=access_token,
            user=public_user
        )
    
    @staticmethod
    async def logout_user(user_id: str):
        """Mark user as offline"""
        db = Database.get_db()
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_online": False, "last_seen": datetime.utcnow()}}
        )