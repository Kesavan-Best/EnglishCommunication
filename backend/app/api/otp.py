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
        print(f"🔄 Attempting to send OTP to {request.email}...")
        success, error_msg = email_service.send_otp_email(request.email, otp, request.name)
        
        # Store whether email was sent successfully
        db.otps.update_one(
            {"email": request.email},
            {"$set": {
                "email_sent": success, 
                "email_error": error_msg if not success else None,
                "smtp_user": email_service.smtp_user if success else None
            }}
        )
        
        # Log the actual result
        if not success:
            print(f"❌ Email FAILED to send to {request.email}")
            print(f"❌ Error: {error_msg}")
            print(f"🔐 OTP for testing: {otp}")
            
            # Return clear error with OTP for testing
            return {
                "message": "OTP generated but email failed to send",
                "email": request.email,
                "expires_in_minutes": 10,
                "email_sent": False,
                "warning": "⚠️ Email delivery failed. Use OTP below or check email configuration.",
                "error_details": error_msg,
                "otp_for_testing": otp,  # Include OTP for testing when email fails
                "instructions": f"Copy this OTP code to verify: {otp}",
                "troubleshooting": {
                    "issue": "Email not configured or delivery failed",
                    "smtp_configured": email_service.is_configured,
                    "smtp_host": email_service.smtp_host,
                    "smtp_user_set": bool(email_service.smtp_user),
                    "recommendation": "Contact administrator to configure SMTP settings in Render environment variables"
                }
            }
        
        # Email sent successfully
        print(f"✅ OTP email SUCCESSFULLY sent to {request.email}")
        print(f"📬 From: {email_service.smtp_user}")
        print(f"📨 Check inbox and spam folder")
        
        return {
            "message": f"✅ OTP sent successfully to {request.email}",
            "email": request.email,
            "expires_in_minutes": 10,
            "email_sent": True,
            "instructions": "Check your email inbox (and spam folder) for the verification code."
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


@router.get("/email-diagnostics")
async def email_diagnostics():
    """
    Debug endpoint to check email configuration on Render
    This helps diagnose why emails aren't being delivered
    """
    import os
    diagnostics = email_service.get_diagnostics()
    
    # Add environment variable check
    env_check = {
        "SMTP_HOST_set": bool(os.getenv("SMTP_HOST")),
        "SMTP_PORT_set": bool(os.getenv("SMTP_PORT")),
        "SMTP_USER_set": bool(os.getenv("SMTP_USER")),
        "SMTP_PASSWORD_set": bool(os.getenv("SMTP_PASSWORD")),
        "SMTP_PASSWORD_length": len(os.getenv("SMTP_PASSWORD", "")),
        "FROM_EMAIL_set": bool(os.getenv("FROM_EMAIL")),
        "FROM_NAME_set": bool(os.getenv("FROM_NAME")),
    }
    
    # Check if password looks like an App Password (16 chars, no spaces)
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    password_analysis = {
        "length": len(smtp_pass),
        "has_spaces": " " in smtp_pass,
        "looks_like_app_password": len(smtp_pass.replace(" ", "")) == 16 and smtp_pass.replace(" ", "").isalpha(),
        "warning": None
    }
    
    if password_analysis["length"] > 0:
        if password_analysis["length"] < 16:
            password_analysis["warning"] = "Password too short. Gmail App Passwords are 16 characters."
        elif password_analysis["has_spaces"]:
            password_analysis["warning"] = "Password contains spaces. Remove spaces from the App Password."
        elif not password_analysis["looks_like_app_password"]:
            password_analysis["warning"] = "Password doesn't look like a Gmail App Password. App Passwords are 16 lowercase letters."
    
    return {
        "status": "ok",
        "email_service": diagnostics,
        "environment_variables": env_check,
        "password_analysis": password_analysis,
        "troubleshooting_tips": [
            "1. Ensure 2-Step Verification is enabled on your Gmail account",
            "2. Generate App Password at https://myaccount.google.com/apppasswords",
            "3. Use the 16-character App Password (remove spaces if any)",
            "4. Set SMTP_USER to your full Gmail address (e.g., example@gmail.com)",
            "5. Set SMTP_PASSWORD to the 16-char App Password",
            "6. After changing env vars in Render, wait for redeploy to complete"
        ]
    }


@router.post("/test-smtp")
async def test_smtp_connection():
    """
    Test SMTP connection without sending an actual email
    This helps diagnose connection issues on Render
    """
    import socket
    import smtplib
    import ssl
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "smtp_host": email_service.smtp_host,
        "smtp_port": email_service.smtp_port,
        "smtp_ssl_port": email_service.smtp_ssl_port,
        "tests": {}
    }
    
    # Test 1: DNS Resolution
    try:
        ip = socket.gethostbyname(email_service.smtp_host)
        results["tests"]["dns_resolution"] = {"success": True, "ip": ip}
    except Exception as e:
        results["tests"]["dns_resolution"] = {"success": False, "error": str(e)}
    
    # Test 2: TCP Connection to port 587
    try:
        sock = socket.create_connection((email_service.smtp_host, email_service.smtp_port), timeout=10)
        sock.close()
        results["tests"]["tcp_587"] = {"success": True}
    except Exception as e:
        results["tests"]["tcp_587"] = {"success": False, "error": str(e)}
    
    # Test 3: TCP Connection to port 465
    try:
        sock = socket.create_connection((email_service.smtp_host, email_service.smtp_ssl_port), timeout=10)
        sock.close()
        results["tests"]["tcp_465"] = {"success": True}
    except Exception as e:
        results["tests"]["tcp_465"] = {"success": False, "error": str(e)}
    
    # Test 4: SMTP TLS Connection
    if email_service.is_configured:
        try:
            with smtplib.SMTP(email_service.smtp_host, email_service.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(email_service.smtp_user, email_service.smtp_password)
                results["tests"]["smtp_tls_auth"] = {"success": True}
        except smtplib.SMTPAuthenticationError as e:
            results["tests"]["smtp_tls_auth"] = {"success": False, "error": f"Authentication failed: {str(e)}", "hint": "Check if you're using Gmail App Password, not regular password"}
        except Exception as e:
            results["tests"]["smtp_tls_auth"] = {"success": False, "error": str(e)}
        
        # Test 5: SMTP SSL Connection
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(email_service.smtp_host, email_service.smtp_ssl_port, timeout=30, context=context) as server:
                server.login(email_service.smtp_user, email_service.smtp_password)
                results["tests"]["smtp_ssl_auth"] = {"success": True}
        except smtplib.SMTPAuthenticationError as e:
            results["tests"]["smtp_ssl_auth"] = {"success": False, "error": f"Authentication failed: {str(e)}"}
        except Exception as e:
            results["tests"]["smtp_ssl_auth"] = {"success": False, "error": str(e)}
    else:
        results["tests"]["smtp_auth"] = {"success": False, "error": "Email not configured - SMTP_USER or SMTP_PASSWORD not set"}
    
    # Summary
    all_passed = all(t.get("success", False) for t in results["tests"].values())
    results["overall_status"] = "PASS" if all_passed else "FAIL"
    
    return results
