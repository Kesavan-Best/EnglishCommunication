"""
OTP (One-Time Password) router for email verification
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import random
import string

from backend.app.database import Database
from backend.app.email_service import email_service

router = APIRouter()

class SendOTPRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = ""

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

def generate_otp(length: int = 6) -> str:
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

@router.post("/send-otp")
async def send_otp(request: SendOTPRequest):
    """Send OTP to email for verification"""
    try:
        db = Database.get_db()
        
        # Check if email already exists
        existing_user = db.users.find_one({"email": request.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate OTP
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Store OTP in database
        db.otps.delete_many({"email": request.email})  # Remove old OTPs
        db.otps.insert_one({
            "email": request.email,
            "otp": otp,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "verified": False,
            "attempts": 0
        })
        
        # Send email
        success = email_service.send_otp_email(request.email, otp, request.name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please check your email configuration."
            )
        
        print(f"📧 OTP sent to {request.email}: {otp}")  # For debugging
        
        return {
            "message": "OTP sent successfully",
            "email": request.email,
            "expires_in_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )

@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """Verify OTP code"""
    try:
        db = Database.get_db()
        
        # Find OTP record
        otp_record = db.otps.find_one({
            "email": request.email,
            "verified": False
        })
        
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OTP found for this email or OTP already used"
            )
        
        # Check expiration
        if datetime.utcnow() > otp_record["expires_at"]:
            db.otps.delete_one({"_id": otp_record["_id"]})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )
        
        # Check attempts (max 5 attempts)
        if otp_record["attempts"] >= 5:
            db.otps.delete_one({"_id": otp_record["_id"]})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many failed attempts. Please request a new OTP."
            )
        
        # Verify OTP
        if otp_record["otp"] != request.otp:
            # Increment attempts
            db.otps.update_one(
                {"_id": otp_record["_id"]},
                {"$inc": {"attempts": 1}}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {4 - otp_record['attempts']} attempts remaining."
            )
        
        # Mark as verified
        db.otps.update_one(
            {"_id": otp_record["_id"]},
            {"$set": {"verified": True, "verified_at": datetime.utcnow()}}
        )
        
        print(f"✅ OTP verified successfully for {request.email}")
        
        return {
            "message": "OTP verified successfully",
            "email": request.email,
            "verified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify OTP: {str(e)}"
        )

@router.post("/resend-otp")
async def resend_otp(request: SendOTPRequest):
    """Resend OTP if previous one expired or lost"""
    try:
        db = Database.get_db()
        
        # Check if email already exists
        existing_user = db.users.find_one({"email": request.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Delete old OTP
        db.otps.delete_many({"email": request.email})
        
        # Same as send_otp
        return await send_otp(request)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resending OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend OTP: {str(e)}"
        )
