# Gmail SMTP Setup Guide for OTP Feature

## 📧 How to Set Up Gmail for Sending OTP Emails

Follow these steps to configure Gmail SMTP for your application:

---

### **Step 1: Enable 2-Step Verification**

1. Go to your Google Account: https://myaccount.google.com/
2. Click on **"Security"** in the left sidebar
3. Scroll down to **"2-Step Verification"**
4. Click **"Get Started"** and follow the prompts
5. Complete the setup (you'll need your phone for verification)

---

### **Step 2: Generate App Password**

1. After enabling 2-Step Verification, go back to Security settings
2. Under "2-Step Verification", find **"App passwords"**
3. Click on **"App passwords"**
4. You might need to sign in again
5. In the "Select app" dropdown, choose **"Mail"**
6. In the "Select device" dropdown, choose **"Other (Custom name)"**
7. Enter a name like **"ImproveCommunication"**
8. Click **"Generate"**
9. Google will show you a **16-character password** (looks like: `abcd efgh ijkl mnop`)
10. **COPY THIS PASSWORD** - you won't see it again!

---

### **Step 3: Update Your .env File**

1. Open `backend/.env` file
2. Update the following variables with your Gmail credentials:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
FROM_EMAIL=your-email@gmail.com
FROM_NAME=ImproveCommunication
```

**Replace:**
- `your-email@gmail.com` - Your actual Gmail address
- `abcdefghijklmnop` - The 16-character App Password (remove spaces)

**Example:**
```env
SMTP_USER=kesavan@gmail.com
SMTP_PASSWORD=xyzhijklmnopqrst
FROM_EMAIL=kesavan@gmail.com
```

---

### **Step 4: Test Your Configuration**

1. Make sure your backend server is running
2. Try registering a new account
3. You should receive an OTP email within seconds

---

### **Step 5: Update Render Environment Variables**

For production (Render deployment):

1. Go to Render Dashboard: https://dashboard.render.com/
2. Click on your **"english-communication-backend"** service
3. Go to **"Environment"** tab
4. Add these environment variables:

```
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = your-email@gmail.com
SMTP_PASSWORD = abcdefghijklmnop
FROM_EMAIL = your-email@gmail.com
FROM_NAME = ImproveCommunication
```

5. Click **"Save Changes"**
6. Render will automatically redeploy

---

## 🚨 Important Notes:

### Security:
- ✅ **Never commit** your App Password to GitHub
- ✅ Keep your `.env` file in `.gitignore`
- ✅ Use different App Passwords for different applications
- ✅ You can revoke App Passwords anytime from Google Account settings

### Gmail Limits:
- 📧 Free Gmail accounts: ~500 emails/day
- 📧 Google Workspace: 2,000 emails/day
- 📧 If you exceed limits, consider switching to SendGrid or Resend

### Troubleshooting:
- ❌ **"Invalid credentials"** - Check your App Password is correct (no spaces)
- ❌ **"Less secure app access"** - You need App Password, not regular password
- ❌ **"Authentication failed"** - Make sure 2-Step Verification is enabled

---

## 🔄 Alternative: Use Resend (For Production)

If you want better deliverability for production:

1. Sign up at https://resend.com/
2. Get your API key
3. Update `.env`:
```env
EMAIL_SERVICE=resend
RESEND_API_KEY=re_your_api_key_here
FROM_EMAIL=onboarding@resend.dev
```

4. I can help you switch the email service code when you're ready!

---

## ✅ Quick Test

Run this command in your backend directory to test email sending:

```bash
python -c "from app.email_service import email_service; email_service.send_otp_email('your-test-email@gmail.com', '123456', 'Test User')"
```

Replace `your-test-email@gmail.com` with your actual email.

---

**Need Help?** Let me know if you encounter any issues!
