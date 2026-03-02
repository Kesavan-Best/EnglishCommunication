"""
Email Service for sending OTP and notifications
Supports Brevo API, Resend API (HTTP) for Render deployment and SMTP fallback

RENDER FREE TIER: SMTP is blocked! Use Brevo or Resend API instead.
Setup (Brevo - RECOMMENDED - 300 emails/day FREE, no domain verification): 
1. Go to https://www.brevo.com and sign up
2. Get your API key from Settings > API Keys
3. Add BREVO_API_KEY and BREVO_FROM to Render environment variables

Alternative (Resend - requires domain verification):
1. Go to https://resend.com and sign up
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
from pathlib import Path
from dotenv import load_dotenv

# Load .env explicitly so API keys are always available
_env_file = Path(__file__).parent.parent / '.env'
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=True)

# Try to import requests for Brevo/Resend API
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def log_email_status(to_email: str, subject: str, status: str, method: str, error: str = None, extra_info: dict = None):
    """Log email delivery status with detailed information"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n" + "="*70)
    print(f"📧 EMAIL LOG - {timestamp}")
    print("="*70)
    print(f"  To:       {to_email}")
    print(f"  Subject:  {subject[:50]}..." if len(subject) > 50 else f"  Subject:  {subject}")
    print(f"  Method:   {method}")
    print(f"  Status:   {'✅ DELIVERED' if status == 'success' else '❌ FAILED'}")
    
    if error:
        print(f"  Error:    {error}")
    
    if extra_info:
        for key, value in extra_info.items():
            print(f"  {key}:  {value}")
    
    print("="*70 + "\n")
    
    # Also log to logger for file-based logging
    if status == 'success':
        logger.info(f"EMAIL DELIVERED | To: {to_email} | Method: {method} | Subject: {subject}")
    else:
        logger.error(f"EMAIL FAILED | To: {to_email} | Method: {method} | Error: {error} | Subject: {subject}")


class EmailService:
    def __init__(self):
        self.last_error = None
        self.last_success_time = None
        self.total_sent = 0
        self.total_failed = 0
        self._reload_config()
    
    def _reload_config(self):
        """Reload configuration from environment variables."""
        # Brevo API (RECOMMENDED - 300 emails/day FREE, no domain verification needed)
        self.brevo_api_key = os.getenv("BREVO_API_KEY", "")
        self.brevo_from = os.getenv("BREVO_FROM", "")
        
        # Resend API (requires domain verification for production)
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")
        self.resend_from = os.getenv("RESEND_FROM", "onboarding@resend.dev")
        
        # SMTP Configuration (fallback for local development)
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_ssl_port = int(os.getenv("SMTP_SSL_PORT", "465"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.brevo_from or self.smtp_user or self.resend_from)
        self.from_name = os.getenv("FROM_NAME", "ImproveCommunication")
        self.timeout = int(os.getenv("SMTP_TIMEOUT", "30"))
        
        # Determine which service to use (priority: Brevo > Resend > SMTP)
        self.use_brevo = bool(self.brevo_api_key and self.brevo_from)
        self.use_resend = bool(self.resend_api_key)
        self.use_smtp = bool(self.smtp_user and self.smtp_password)
        self.is_configured = self.use_brevo or self.use_resend or self.use_smtp
        
        # Log configuration
        if self.use_brevo:
            logger.info(f"✅ Email via Brevo API - From: {self.brevo_from}")
        elif self.use_resend:
            logger.info(f"✅ Email via Resend API - From: {self.resend_from}")
        elif self.use_smtp:
            masked = f"{self.smtp_user[:3]}***" if self.smtp_user else "none"
            logger.info(f"✅ Email via SMTP: {masked}")
        else:
            logger.warning("⚠️ Email not configured. Set BREVO_API_KEY+BREVO_FROM (recommended) or SMTP credentials")
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic info"""
        return {
            "configured": self.is_configured,
            "use_brevo": self.use_brevo,
            "use_resend": self.use_resend,
            "use_smtp": self.use_smtp,
            "brevo_api_key_set": bool(self.brevo_api_key),
            "brevo_from": self.brevo_from if self.use_brevo else None,
            "resend_api_key_set": bool(self.resend_api_key),
            "resend_from": self.resend_from if self.use_resend else None,
            "smtp_host": self.smtp_host,
            "smtp_user_set": bool(self.smtp_user),
            "last_error": self.last_error,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed
        }

    def _send_with_brevo(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email using Brevo API (HTTP - works on Render, 300 emails/day FREE)"""
        print(f"\n[BREVO API] Attempting to send email to: {to_email}")
        
        if not REQUESTS_AVAILABLE:
            error = "requests library not installed"
            log_email_status(to_email, subject, 'failed', 'Brevo API', error)
            return False, error
        
        if not self.brevo_api_key:
            error = "BREVO_API_KEY not set"
            log_email_status(to_email, subject, 'failed', 'Brevo API', error)
            return False, error
        
        if not self.brevo_from:
            error = "BREVO_FROM not set (use your verified email)"
            log_email_status(to_email, subject, 'failed', 'Brevo API', error)
            return False, error
        
        try:
            logger.info(f"📧 Brevo: Sending to {to_email}...")
            print(f"[BREVO API] Making HTTP POST request to api.brevo.com...")
            
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": self.brevo_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "sender": {
                        "name": self.from_name,
                        "email": self.brevo_from
                    },
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "htmlContent": html_content,
                    "textContent": text_content or ""
                },
                timeout=30
            )
            
            print(f"[BREVO API] Response Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                message_id = result.get('messageId', 'ok')
                logger.info(f"✅ Brevo: Sent! ID: {message_id}")
                log_email_status(to_email, subject, 'success', 'Brevo API', extra_info={'Message ID': message_id})
                return True, ""
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', f"HTTP {response.status_code}")
                logger.error(f"❌ Brevo: {error_msg}")
                log_email_status(to_email, subject, 'failed', 'Brevo API', error_msg, {'HTTP Code': response.status_code})
                return False, f"Brevo: {error_msg}"
                
        except requests.exceptions.Timeout:
            error = "Brevo timeout - request took too long"
            log_email_status(to_email, subject, 'failed', 'Brevo API', error)
            return False, error
        except Exception as e:
            error = f"Brevo error: {str(e)}"
            log_email_status(to_email, subject, 'failed', 'Brevo API', error)
            return False, error

    def _send_with_resend(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email using Resend API (HTTP - works on Render free tier)"""
        print(f"\n[RESEND API] Attempting to send email to: {to_email}")
        
        if not REQUESTS_AVAILABLE:
            error = "requests library not installed"
            log_email_status(to_email, subject, 'failed', 'Resend API', error)
            return False, error
        
        if not self.resend_api_key:
            error = "RESEND_API_KEY not set"
            log_email_status(to_email, subject, 'failed', 'Resend API', error)
            return False, error
        
        try:
            logger.info(f"📧 Resend: Sending to {to_email}...")
            print(f"[RESEND API] Making HTTP POST request to api.resend.com...")
            
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
            
            print(f"[RESEND API] Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                email_id = result.get('id', 'ok')
                logger.info(f"✅ Resend: Sent! ID: {email_id}")
                log_email_status(to_email, subject, 'success', 'Resend API', extra_info={'Email ID': email_id})
                return True, ""
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', f"HTTP {response.status_code}")
                logger.error(f"❌ Resend: {error_msg}")
                log_email_status(to_email, subject, 'failed', 'Resend API', error_msg, {'HTTP Code': response.status_code})
                return False, f"Resend: {error_msg}"
                
        except requests.exceptions.Timeout:
            error = "Resend timeout - request took too long"
            log_email_status(to_email, subject, 'failed', 'Resend API', error)
            return False, error
        except Exception as e:
            error = f"Resend error: {str(e)}"
            log_email_status(to_email, subject, 'failed', 'Resend API', error)
            return False, error

    def _send_with_smtp(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email using SMTP (tries SSL port 465 first, then TLS port 587)"""
        print(f"\n[SMTP] Attempting to send email to: {to_email}")
        
        if not self.smtp_user or not self.smtp_password:
            error = "SMTP not configured"
            log_email_status(to_email, subject, 'failed', 'SMTP', error)
            return False, error
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        
        if text_content:
            message.attach(MIMEText(text_content, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))
        
        # Try SSL (port 465) first - more likely to work on cloud platforms
        try:
            logger.info(f"📧 SMTP SSL: {self.smtp_host}:465...")
            print(f"[SMTP] Trying SSL connection to {self.smtp_host}:465...")
            
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, 465, timeout=self.timeout, context=context) as server:
                print("[SMTP SSL] Connected! Authenticating...")
                server.login(self.smtp_user, self.smtp_password)
                print("[SMTP SSL] Authenticated. Sending message...")
                server.send_message(message)
                logger.info(f"✅ SMTP SSL: Sent to {to_email}")
                log_email_status(to_email, subject, 'success', 'SMTP SSL', extra_info={'Server': f"{self.smtp_host}:465"})
                return True, ""
                
        except Exception as ssl_error:
            logger.warning(f"⚠️ SMTP SSL failed: {ssl_error}")
            print(f"[SMTP] SSL failed: {ssl_error}, trying TLS on port 587...")
        
        # Fallback to TLS (port 587)
        try:
            logger.info(f"📧 SMTP TLS: {self.smtp_host}:{self.smtp_port}...")
            print(f"[SMTP] Trying TLS connection to {self.smtp_host}:{self.smtp_port}...")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                print("[SMTP TLS] Connected! Starting TLS handshake...")
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                print("[SMTP TLS] TLS established. Authenticating...")
                server.login(self.smtp_user, self.smtp_password)
                print("[SMTP TLS] Authenticated. Sending message...")
                server.send_message(message)
                logger.info(f"✅ SMTP TLS: Sent to {to_email}")
                log_email_status(to_email, subject, 'success', 'SMTP TLS', extra_info={'Server': f"{self.smtp_host}:{self.smtp_port}"})
                return True, ""
                
        except OSError as e:
            if "Network is unreachable" in str(e) or "Connection refused" in str(e) or getattr(e, 'errno', 0) in [101, 111]:
                error = "SMTP blocked (both SSL 465 and TLS 587). Set BREVO_API_KEY for cloud deployment."
            else:
                error = f"SMTP network error: {str(e)}"
            log_email_status(to_email, subject, 'failed', 'SMTP', error)
            return False, error
        except smtplib.SMTPAuthenticationError as e:
            error = f"SMTP auth failed: Check credentials"
            log_email_status(to_email, subject, 'failed', 'SMTP', error)
            return False, error
        except Exception as e:
            error = f"SMTP error: {str(e)}"
            log_email_status(to_email, subject, 'failed', 'SMTP', error)
            return False, error

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
        """Send email - tries Brevo API first (Render), then Resend, then SMTP (local)"""
        self._reload_config()
        
        print("\n" + "*"*70)
        print(f"📨 EMAIL SEND REQUEST")
        print(f"   Recipient: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Brevo API: {'Enabled' if self.use_brevo else 'Disabled'}")
        print(f"   Resend API: {'Enabled' if self.use_resend else 'Disabled'}")
        print(f"   SMTP: {'Enabled' if self.use_smtp else 'Disabled'}")
        print("*"*70)
        
        if not self.is_configured:
            self.last_error = "Email not configured. Set BREVO_API_KEY+BREVO_FROM (recommended) or SMTP credentials"
            logger.warning(f"⚠️ {self.last_error}")
            print(f"❌ EMAIL NOT CONFIGURED: {self.last_error}")
            log_email_status(to_email, subject, 'failed', 'None', self.last_error)
            return False, self.last_error
        
        if not to_email or '@' not in to_email:
            error = f"Invalid email: {to_email}"
            print(f"❌ INVALID EMAIL ADDRESS: {error}")
            log_email_status(to_email, subject, 'failed', 'Validation', error)
            return False, error
        
        # Try Brevo API first (RECOMMENDED - works on Render, 300 emails/day FREE)
        if self.use_brevo:
            success, error = self._send_with_brevo(to_email, subject, html_content, text_content)
            if success:
                self.total_sent += 1
                self.last_success_time = datetime.utcnow()
                self.last_error = None
                print(f"\n✅ EMAIL SUCCESSFULLY SENT via Brevo API")
                print(f"   Total emails sent: {self.total_sent}")
                return True, ""
            logger.warning(f"Brevo failed: {error}")
            print(f"\n⚠️ Brevo API failed, trying Resend fallback...")
        
        # Try Resend API (requires domain verification)
        if self.use_resend:
            success, error = self._send_with_resend(to_email, subject, html_content, text_content)
            if success:
                self.total_sent += 1
                self.last_success_time = datetime.utcnow()
                self.last_error = None
                print(f"\n✅ EMAIL SUCCESSFULLY SENT via Resend API")
                print(f"   Total emails sent: {self.total_sent}")
                return True, ""
            logger.warning(f"Resend failed: {error}")
            print(f"\n⚠️ Resend API failed, trying SMTP fallback...")
        
        # Fallback to SMTP (local dev)
        if self.use_smtp:
            success, error = self._send_with_smtp(to_email, subject, html_content, text_content)
            if success:
                self.total_sent += 1
                self.last_success_time = datetime.utcnow()
                self.last_error = None
                print(f"\n✅ EMAIL SUCCESSFULLY SENT via SMTP")
                print(f"   Total emails sent: {self.total_sent}")
                return True, ""
            self.last_error = error
        
        self.total_failed += 1
        print(f"\n❌ EMAIL SEND FAILED")
        print(f"   Total failed: {self.total_failed}")
        print(f"   Last error: {self.last_error}")
        return False, self.last_error or "Email send failed"
    
    def send_otp_email(self, to_email: str, otp: str, name: str = "") -> Tuple[bool, str]:
        """Send OTP verification email"""
        print(f"\n🔐 OTP EMAIL REQUEST")
        print(f"   To: {to_email}")
        print(f"   Name: {name or 'Not provided'}")
        print(f"   OTP: {otp}")
        
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
        
        success, error = self.send_email(to_email, subject, html_content, text_content)
        if success:
            print(f"\n✅ OTP EMAIL DELIVERED to {to_email}")
        else:
            print(f"\n❌ OTP EMAIL FAILED to {to_email}: {error}")
        return success, error
    
    def send_welcome_email(self, to_email: str, name: str) -> Tuple[bool, str]:
        """Send welcome email"""
        print(f"\n🎉 WELCOME EMAIL REQUEST")
        print(f"   To: {to_email}")
        print(f"   Name: {name}")
        
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
        
        success, error = self.send_email(to_email, subject, html_content, text_content)
        if success:
            print(f"\n✅ WELCOME EMAIL DELIVERED to {to_email}")
        else:
            print(f"\n❌ WELCOME EMAIL FAILED to {to_email}: {error}")
        return success, error


# Singleton instance
email_service = EmailService()
