"""
Email Service for sending OTP and notifications
Supports Gmail SMTP and can be easily switched to Resend/SendGrid
Enhanced for Render deployment with better error handling
"""
import smtplib
import os
import socket
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "ImproveCommunication")
        self.timeout = int(os.getenv("SMTP_TIMEOUT", "30"))  # 30 second timeout
        self.is_configured = bool(self.smtp_user and self.smtp_password)
        
        # Log configuration status (without exposing credentials)
        if not self.is_configured:
            logger.warning("⚠️  Email service not configured. Set SMTP_USER and SMTP_PASSWORD environment variables.")
        else:
            logger.info(f"✅ Email service configured: {self.smtp_user[:3]}***@{self.smtp_user.split('@')[1] if '@' in self.smtp_user else 'unknown'}")
        
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> tuple[bool, str]:
        """
        Send email using SMTP
        Returns: (success: bool, error_message: str)
        """
        if not self.is_configured:
            error_msg = "Email service not configured. Set SMTP_USER and SMTP_PASSWORD."
            logger.warning(f"⚠️  {error_msg} - Skipping email to {to_email}")
            logger.info(f"📧 Subject: {subject}")
            return False, error_msg
            
        try:
            logger.info(f"📧 Attempting to send email to {to_email}...")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text version (fallback)
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_content, "html")
            message.attach(part2)
            
            # Send email with timeout
            logger.info(f"Connecting to {self.smtp_host}:{self.smtp_port}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                server.set_debuglevel(0)  # Set to 1 for verbose debugging
                
                logger.info("Starting TLS...")
                server.starttls()
                
                logger.info(f"Logging in as {self.smtp_user}...")
                server.login(self.smtp_user, self.smtp_password)
                
                logger.info("Sending message...")
                result = server.send_message(message)
                
                # Check if message was rejected
                if result:
                    # result is a dict of failed recipients
                    failed = ', '.join(result.keys())
                    error_msg = f"Email rejected by server for: {failed}"
                    logger.error(f"❌ {error_msg}")
                    return False, error_msg
            
            # Email sent successfully
            logger.info(f"✅ Email sent successfully to {to_email}")
            logger.info(f"📬 Email should arrive in 1-2 minutes. Check spam folder if not in inbox.")
            return True, ""
            
        except socket.timeout as e:
            error_msg = f"Connection timeout after {self.timeout}s. Check network/firewall settings."
            logger.error(f"❌ Timeout sending email to {to_email}: {error_msg}")
            return False, error_msg
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD. Error: {str(e)}"
            logger.error(f"❌ Auth error: {error_msg}")
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(f"❌ SMTP error sending to {to_email}: {error_msg}")
            return False, error_msg
        except socket.gaierror as e:
            error_msg = f"DNS resolution failed for {self.smtp_host}. Check internet connection."
            logger.error(f"❌ DNS error: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(f"❌ Failed to send email to {to_email}: {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return False, error_msg
    
    def send_otp_email(self, to_email: str, otp: str, name: str = "") -> tuple[bool, str]:
        """
        Send OTP verification email
        Returns: (success: bool, error_message: str)
        """
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
    
    def send_welcome_email(self, to_email: str, name: str) -> tuple[bool, str]:
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
