"""
Email Service for sending OTP and notifications
Supports Resend API (HTTP) for Render deployment and SMTP fallback for local dev

RENDER FREE TIER: SMTP is blocked! Use Resend API instead.
Setup: 
1. Go to https://resend.com and sign up (free - 100 emails/day)
2. Get your API key from dashboard
3. Add RESEND_API_KEY to Render environment variables
"""
import smtplib
import ssl
import os
import socket
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# Try to import requests for Resend API
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.last_error = None
        self.last_success_time = None
        self.total_sent = 0
        self.total_failed = 0
        self._reload_config()
    
    def _reload_config(self):
        """Reload configuration from environment variables."""
        # Resend API (recommended for Render - HTTP works, SMTP blocked)
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")
        self.resend_from = os.getenv("RESEND_FROM", "onboarding@resend.dev")
        
        # SMTP Configuration (fallback for local development)
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_ssl_port = int(os.getenv("SMTP_SSL_PORT", "465"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user or self.resend_from)
        self.from_name = os.getenv("FROM_NAME", "ImproveCommunication")
        self.timeout = int(os.getenv("SMTP_TIMEOUT", "30"))
        
        # Determine which service to use
        self.use_resend = bool(self.resend_api_key)
        self.use_smtp = bool(self.smtp_user and self.smtp_password)
        self.is_configured = self.use_resend or self.use_smtp
        
        # Log configuration
        if self.use_resend:
            logger.info(f"✅ Email via Resend API - From: {self.resend_from}")
        elif self.use_smtp:
            masked = f"{self.smtp_user[:3]}***" if self.smtp_user else "none"
            logger.info(f"✅ Email via SMTP: {masked}")
        else:
            logger.warning("⚠️ Email not configured. Set RESEND_API_KEY (for Render) or SMTP credentials")
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic info"""
        return {
            "configured": self.is_configured,
            "use_resend": self.use_resend,
            "use_smtp": self.use_smtp,
            "resend_api_key_set": bool(self.resend_api_key),
            "resend_from": self.resend_from if self.use_resend else None,
            "smtp_host": self.smtp_host,
            "smtp_user_set": bool(self.smtp_user),
            "last_error": self.last_error,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed
        }

    def _send_with_resend(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email using Resend API (HTTP - works on Render free tier)"""
        if not REQUESTS_AVAILABLE:
            return False, "requests library not installed"
        
        if not self.resend_api_key:
            return False, "RESEND_API_KEY not set"
        
        try:
            logger.info(f"📧 Resend: Sending to {to_email}...")
            
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": f"{self.from_name} <{self.resend_from}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content or ""
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Resend: Sent! ID: {result.get('id', 'ok')}")
                return True, ""
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', f"HTTP {response.status_code}")
                logger.error(f"❌ Resend: {error_msg}")
                return False, f"Resend: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "Resend timeout"
        except Exception as e:
            return False, f"Resend error: {str(e)}"

    def _send_with_smtp(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email using SMTP (for local development)"""
        if not self.smtp_user or not self.smtp_password:
            return False, "SMTP not configured"
        
        try:
            logger.info(f"📧 SMTP: {self.smtp_host}:{self.smtp_port}...")
            
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            if text_content:
                message.attach(MIMEText(text_content, "plain", "utf-8"))
            message.attach(MIMEText(html_content, "html", "utf-8"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
                logger.info(f"✅ SMTP: Sent to {to_email}")
                return True, ""
                
        except OSError as e:
            if "Network is unreachable" in str(e) or getattr(e, 'errno', 0) == 101:
                return False, "SMTP blocked on Render. Use RESEND_API_KEY instead."
            return False, f"SMTP network error: {str(e)}"
        except smtplib.SMTPAuthenticationError as e:
            return False, f"SMTP auth failed: Check credentials"
        except Exception as e:
            return False, f"SMTP error: {str(e)}"

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email - tries Resend API first (Render), then SMTP (local)"""
        self._reload_config()
        
        if not self.is_configured:
            self.last_error = "Email not configured. Set RESEND_API_KEY (Render) or SMTP credentials (local)"
            logger.warning(f"⚠️ {self.last_error}")
            return False, self.last_error
        
        if not to_email or '@' not in to_email:
            return False, f"Invalid email: {to_email}"
        
        # Try Resend API first (works on Render)
        if self.use_resend:
            success, error = self._send_with_resend(to_email, subject, html_content, text_content)
            if success:
                self.total_sent += 1
                self.last_success_time = datetime.utcnow()
                self.last_error = None
                return True, ""
            logger.warning(f"Resend failed: {error}")
        
        # Fallback to SMTP (local dev)
        if self.use_smtp:
            success, error = self._send_with_smtp(to_email, subject, html_content, text_content)
            if success:
                self.total_sent += 1
                self.last_success_time = datetime.utcnow()
                self.last_error = None
                return True, ""
            self.last_error = error
        
        self.total_failed += 1
        return False, self.last_error or "Email send failed"
    
    def send_otp_email(self, to_email: str, otp: str, name: str = "") -> Tuple[bool, str]:
        """Send OTP verification email"""
        subject = "Verify Your Email - ImproveCommunication"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: white; border: 2px dashed #667eea; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }}
                .otp-code {{ font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Email Verification</h1>
                </div>
                <div class="content">
                    <p>Hi {name or 'there'},</p>
                    <p>Use this code to verify your email:</p>
                    <div class="otp-box">
                        <div class="otp-code">{otp}</div>
                        <p style="color: #666;">Expires in 10 minutes</p>
                    </div>
                    <p style="color: #999; font-size: 12px;">If you didn't request this, ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Your verification code: {otp}\nExpires in 10 minutes."
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_welcome_email(self, to_email: str, name: str) -> Tuple[bool, str]:
        """Send welcome email"""
        subject = "Welcome to ImproveCommunication! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome!</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p>Your account is ready! Start practicing English with:</p>
                    <ul>
                        <li>📞 Live practice calls</li>
                        <li>🤖 AI-powered feedback</li>
                        <li>📊 Progress tracking</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Hi {name}, Welcome to ImproveCommunication! Your account is ready."
        
        return self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
