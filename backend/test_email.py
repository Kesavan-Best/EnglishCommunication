"""
Test Email Service Configuration
Run this to test email sending before deploying
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.email_service import email_service

def main():
    print("=" * 70)
    print("EMAIL SERVICE CONFIGURATION TEST")
    print("=" * 70)
    
    # Check configuration
    print("")
    print("📋 Configuration Status:")
    print(f"   SMTP Host: {email_service.smtp_host}")
    print(f"   SMTP Port: {email_service.smtp_port}")
    smtp_user_display = email_service.smtp_user if email_service.smtp_user else "(not set)"
    print(f"   SMTP User: {smtp_user_display}") 
    from_email_display = email_service.from_email if email_service.from_email else "(not set)"
    print(f"   From Email: {from_email_display}")
    print(f"   From Name: {email_service.from_name}")
    print(f"   Timeout: {email_service.timeout}s")
    configured_status = "YES" if email_service.is_configured else "NO"
    print(f"   Configured: {configured_status}")
    
    if not email_service.is_configured:
        print("\n" + "=" * 70)
        print("⚠️  EMAIL SERVICE NOT CONFIGURED")
        print("=" * 70)
        print("\nTo fix this, set these environment variables:")
        print("   SMTP_USER=your-email@gmail.com")
        print("   SMTP_PASSWORD=your-16-char-app-password")
        print("\nFor Gmail App Password:")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Enable 2-Step Verification first")
        print("   3. Generate App Password for 'Mail'")
        print("   4. Copy the 16-character password")
        print("\n" + "=" * 70)
        return
    
    # Email is configured, offer to send test
    print("\n" + "=" * 70)
    print("✅ EMAIL SERVICE IS CONFIGURED!")
    print("=" * 70)
    
    send_test = input("\nWould you like to send a test email? (y/n): ").lower().strip()
    
    if send_test == 'y':
        test_email = input("Enter recipient email address: ").strip()
        
        if not test_email or '@' not in test_email:
            print("❌ Invalid email address")
            return
        
        print(f"\n📧 Sending test OTP email to {test_email}...")
        print("   (This will take 5-30 seconds)")
        print()
        
        # Send test OTP email
        success, error_msg = email_service.send_otp_email(
            to_email=test_email,
            otp="123456",
            name="Test User"
        )
        
        print("\n" + "=" * 70)
        if success:
            print("✅ TEST EMAIL SENT SUCCESSFULLY!")
            print("=" * 70)
            print(f"\nCheck the inbox (and spam folder) of: {test_email}")
            print("You should receive an email with OTP code: 123456")
        else:
            print("❌ TEST EMAIL FAILED")
            print("=" * 70)
            print(f"\nError Details: {error_msg}")
            print("\nCommon Issues:")
            print("   1. Using regular Gmail password instead of App Password")
            print("   2. 2-Step Verification not enabled")
            print("   3. Gmail blocking the connection")
            print("   4. Network/firewall blocking SMTP")
            print("\nTry:")
            print("   • Regenerate Gmail App Password")
            print("   • Check SMTP_USER and SMTP_PASSWORD are correct")
            print("   • Increase SMTP_TIMEOUT (export SMTP_TIMEOUT=60)")
        print("=" * 70)
    
    else:
        print("\n✅ Configuration looks good!")
        print("   You can deploy to Render now.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        traceback.print_exc()
