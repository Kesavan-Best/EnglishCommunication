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
        
        # Try to send email
        success, error_msg = email_service.send_otp_email(request.email, otp, request.name)
        
        # Store whether email was sent successfully
        db.otps.update_one(
            {"email": request.email},
            {"$set": {"email_sent": success, "email_error": error_msg if not success else None}}
        )
        
        # Always return success to user, but indicate if email wasn't sent
        if not success:
            print(f"⚠️  Email not sent to {request.email}: {error_msg}")
            print(f"🔐 OTP for testing: {otp}")
            
            return {
                "message": "OTP generated successfully",
                "email": request.email,
                "expires_in_minutes": 10,
                "email_sent": False,
                "warning": "Email service unavailable. Please check with administrator or use alternative verification.",
                "error_details": error_msg,
                "otp_for_testing": otp,  # Include OTP for development/testing
                "instructions": "Use the OTP code shown above to complete registration."
            }
        
        print(f"📧 OTP sent successfully to {request.email}")
        
        return {
            "message": "OTP sent successfully to your email",
            "email": request.email,
            "expires_in_minutes": 10,
            "email_sent": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        import traceback
        traceback.print_exc()
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
