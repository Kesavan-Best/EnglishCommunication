"""
Email Service for sending OTP and notifications
Supports Gmail SMTP and can be easily switched to Resend/SendGrid
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "ImproveCommunication")
        
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Send email using SMTP"""
        try:
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
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            print(f"✅ Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_otp_email(self, to_email: str, otp: str, name: str = "") -> bool:
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
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_welcome_email(self, to_email: str, name: str) -> bool:
        """Send welcome email after successful registration"""
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
        
        return self.send_email(to_email, subject, html_content, text_content)

# Create singleton instance
email_service = EmailService()
