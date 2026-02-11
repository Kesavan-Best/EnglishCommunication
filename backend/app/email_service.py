"""
Email Service for sending OTP and notifications
Supports Gmail SMTP and can be easily switched to Resend/SendGrid
Enhanced for Render deployment with better error handling
"""
import smtplib
import ssl
import os
import socket
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Track last error for diagnostics
        self.last_error = None
        self.last_success_time = None
        self.total_sent = 0
        self.total_failed = 0
        
        # Load configuration from environment
        self._reload_config()
    
    def _reload_config(self):
        """Reload SMTP configuration from environment variables.
        This is called on init and can be called again to pick up new env vars.
        """
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_ssl_port = int(os.getenv("SMTP_SSL_PORT", "465"))  # SSL port for fallback
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "ImproveCommunication")
        self.timeout = int(os.getenv("SMTP_TIMEOUT", "60"))  # 60 seconds timeout
        self.max_retries = int(os.getenv("SMTP_MAX_RETRIES", "3"))
        self.use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        self.is_configured = bool(self.smtp_user and self.smtp_password)
        
        # Log configuration status (without exposing credentials)
        if not self.is_configured:
            logger.warning("⚠️  Email service not configured. Set SMTP_USER and SMTP_PASSWORD environment variables.")
        else:
            masked_email = f"{self.smtp_user[:3]}***@{self.smtp_user.split('@')[1] if '@' in self.smtp_user else 'unknown'}"
            logger.info(f"✅ Email service configured: {masked_email}")
            logger.info(f"📧 SMTP: {self.smtp_host}:{self.smtp_port} (TLS) / {self.smtp_ssl_port} (SSL fallback)")
        
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic info about email service"""
        return {
            "configured": self.is_configured,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_ssl_port": self.smtp_ssl_port,
            "smtp_user_set": bool(self.smtp_user),
            "smtp_user_preview": f"{self.smtp_user[:3]}***" if self.smtp_user else None,
            "smtp_password_set": bool(self.smtp_password),
            "smtp_password_length": len(self.smtp_password) if self.smtp_password else 0,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "use_ssl": self.use_ssl,
            "last_error": self.last_error,
            "last_success_time": str(self.last_success_time) if self.last_success_time else None,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed
        }

    def _send_with_tls(self, message: MIMEMultipart, to_email: str) -> Tuple[bool, str]:
        """Send email using STARTTLS (port 587)"""
        logger.info(f"📧 TLS: Connecting to {self.smtp_host}:{self.smtp_port}...")
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
            server.set_debuglevel(1)  # Enable debug for troubleshooting
            
            # Say hello first
            server.ehlo()
            
            logger.info("📧 TLS: Starting TLS encryption...")
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()  # Re-identify after TLS
            
            logger.info(f"📧 TLS: Authenticating as {self.smtp_user}...")
            server.login(self.smtp_user, self.smtp_password)
            
            logger.info(f"📧 TLS: Sending to {to_email}...")
            result = server.send_message(message)
            
            if result:
                failed = ', '.join(result.keys())
                return False, f"Rejected for: {failed}"
            
            return True, ""

    def _send_with_ssl(self, message: MIMEMultipart, to_email: str) -> Tuple[bool, str]:
        """Send email using SSL directly (port 465)"""
        logger.info(f"📧 SSL: Connecting to {self.smtp_host}:{self.smtp_ssl_port}...")
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_ssl_port, timeout=self.timeout, context=context) as server:
            server.set_debuglevel(1)  # Enable debug
            
            logger.info(f"📧 SSL: Authenticating as {self.smtp_user}...")
            server.login(self.smtp_user, self.smtp_password)
            
            logger.info(f"📧 SSL: Sending to {to_email}...")
            result = server.send_message(message)
            
            if result:
                failed = ', '.join(result.keys())
                return False, f"Rejected for: {failed}"
            
            return True, ""

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> Tuple[bool, str]:
        """
        Send email using SMTP with retry and fallback logic
        Returns: (success: bool, error_message: str)
        """
        if not self.is_configured:
            error_msg = "Email service not configured. Set SMTP_USER and SMTP_PASSWORD."
            logger.warning(f"⚠️  {error_msg} - Skipping email to {to_email}")
            logger.info(f"📧 Subject: {subject}")
            self.last_error = error_msg
            return False, error_msg
        
        # Validate email format
        if not to_email or '@' not in to_email:
            error_msg = f"Invalid email address: {to_email}"
            self.last_error = error_msg
            return False, error_msg
            
        try:
            logger.info(f"📧 ========================================")
            logger.info(f"📧 SENDING EMAIL TO: {to_email}")
            logger.info(f"📧 Subject: {subject}")
            logger.info(f"📧 From: {self.from_email}")
            logger.info(f"📧 SMTP: {self.smtp_host}")
            logger.info(f"📧 ========================================")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Reply-To"] = self.from_email
            message["X-Priority"] = "1"  # High priority
            
            # Add text version (fallback)
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                message.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_content, "html", "utf-8")
            message.attach(part2)
            
            last_error = None
            
            # Try sending with retries and fallback
            for attempt in range(self.max_retries):
                logger.info(f"📧 Attempt {attempt + 1}/{self.max_retries}...")
                
                try:
                    # First try TLS (port 587)
                    if not self.use_ssl:
                        success, error = self._send_with_tls(message, to_email)
                        if success:
                            self.total_sent += 1
                            self.last_success_time = datetime.utcnow()
                            self.last_error = None
                            logger.info(f"✅ Email sent successfully via TLS to {to_email}")
                            return True, ""
                        last_error = f"TLS: {error}"
                    
                    # Fallback to SSL (port 465)
                    logger.info("📧 TLS failed, trying SSL fallback...")
                    success, error = self._send_with_ssl(message, to_email)
                    if success:
                        self.total_sent += 1
                        self.last_success_time = datetime.utcnow()
                        self.last_error = None
                        logger.info(f"✅ Email sent successfully via SSL to {to_email}")
                        return True, ""
                    last_error = f"SSL: {error}"
                    
                except smtplib.SMTPAuthenticationError as e:
                    error_msg = f"Authentication failed: {str(e)}. Check SMTP_USER and SMTP_PASSWORD (use Gmail App Password, not regular password)"
                    logger.error(f"❌ {error_msg}")
                    self.last_error = error_msg
                    self.total_failed += 1
                    return False, error_msg
                    
                except smtplib.SMTPRecipientsRefused as e:
                    error_msg = f"Recipient rejected: {to_email} - {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    self.last_error = error_msg
                    self.total_failed += 1
                    return False, error_msg
                    
                except smtplib.SMTPSenderRefused as e:
                    error_msg = f"Sender rejected: {self.from_email} - {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    self.last_error = error_msg
                    self.total_failed += 1
                    return False, error_msg
                    
                except socket.timeout as e:
                    last_error = f"Connection timeout after {self.timeout}s"
                    logger.warning(f"⚠️  Attempt {attempt + 1} timeout, retrying...")
                    
                except socket.gaierror as e:
                    last_error = f"DNS resolution failed for {self.smtp_host}"
                    logger.warning(f"⚠️  Attempt {attempt + 1} DNS error, retrying...")
                    
                except ConnectionRefusedError as e:
                    last_error = f"Connection refused by {self.smtp_host}"
                    logger.warning(f"⚠️  Attempt {attempt + 1} connection refused, retrying...")
                    
                except smtplib.SMTPException as e:
                    last_error = f"SMTP error: {str(e)}"
                    logger.warning(f"⚠️  Attempt {attempt + 1} SMTP error, retrying...")
                
                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"📧 Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
            
            # All retries failed
            error_msg = f"All {self.max_retries} attempts failed. Last error: {last_error}"
            logger.error(f"❌ {error_msg}")
            self.last_error = error_msg
            self.total_failed += 1
            return False, error_msg
            
        except Exception as e:
            import traceback
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(f"❌ Failed to send email to {to_email}: {error_msg}")
            logger.error(traceback.format_exc())
            self.last_error = error_msg
            self.total_failed += 1
            return False, error_msg
    
    def send_otp_email(self, to_email: str, otp: str, name: str = "") -> Tuple[bool, str]:
        """
        Send OTP verification email
        Returns: (success: bool, error_message: str)
        """
        # Reload config to pick up any new environment variables (important for Render)
        self._reload_config()
        logger.info(f"📧 Preparing OTP email for {to_email}")
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
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                .button {{ background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Email Verification</h1>
                </div>
                <div class="content">
                    <p>Hi {name or 'there'},</p>
                    <p>Thank you for signing up for <strong>ImproveCommunication</strong>! To complete your registration, please verify your email address using the OTP code below:</p>
                    
                    <div class="otp-box">
                        <div class="otp-code">{otp}</div>
                        <p style="margin: 10px 0 0 0; color: #666;">This code expires in 10 minutes</p>
                    </div>
                    
                    <p>If you didn't request this code, please ignore this email.</p>
                    
                    <p style="margin-top: 30px;">
                        <strong>Why verify?</strong><br>
                        • Secure your account<br>
                        • Enable password recovery<br>
                        • Get important notifications
                    </p>
                </div>
                <div class="footer">
                    <p>© 2026 ImproveCommunication. All rights reserved.</p>
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Email Verification - ImproveCommunication
        
        Hi {name or 'there'},
        
        Your verification code is: {otp}
        
        This code expires in 10 minutes.
        
        If you didn't request this code, please ignore this email.
        
        © 2026 ImproveCommunication
        """
        
        success, error_msg = self.send_email(to_email, subject, html_content, text_content)
        if not success:
            logger.error(f"Failed to send OTP email: {error_msg}")
        return success, error_msg
    
    def send_welcome_email(self, to_email: str, name: str) -> Tuple[bool, str]:
        """
        Send welcome email after successful registration
        Returns: (success: bool, error_message: str)
        """
        logger.info(f"📧 Preparing welcome email for {to_email}")
        subject = "Welcome to ImproveCommunication! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
                .feature {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to ImproveCommunication!</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p>Your account has been successfully created! We're excited to have you join our community of English learners.</p>
                    
                    <h3>What's Next?</h3>
                    <div class="feature">📞 <strong>Start Practice Calls</strong> - Connect with learners worldwide</div>
                    <div class="feature">🤖 <strong>Get AI Feedback</strong> - Improve with instant analysis</div>
                    <div class="feature">📊 <strong>Track Progress</strong> - Monitor your improvement</div>
                    <div class="feature">🏆 <strong>Join Leaderboards</strong> - Compete and stay motivated</div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <a href="https://english-communication-backend.onrender.com/frontend/templates/login.html" class="button">Get Started Now</a>
                    </p>
                    
                    <p style="margin-top: 20px; color: #666;">
                        Need help? Contact us at support@improvecommunication.com
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to ImproveCommunication!
        
        Hi {name},
        
        Your account has been successfully created!
        
        What's Next?
        - Start Practice Calls - Connect with learners worldwide
        - Get AI Feedback - Improve with instant analysis
        - Track Progress - Monitor your improvement
        - Join Leaderboards - Compete and stay motivated
        
        Get started: https://english-communication-backend.onrender.com/frontend/templates/login.html
        
        © 2026 ImproveCommunication
        """
        
        success, error_msg = self.send_email(to_email, subject, html_content, text_content)
        if not success:
            logger.error(f"Failed to send welcome email: {error_msg}")
        return success, error_msg

# Create singleton instance
email_service = EmailService()
