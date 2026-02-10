# 📧 Configure Email Service on Render

## Current Status
✅ Your app is now deployed and working!  
⚠️ Email verification works but emails aren't being sent yet.

**What happens now:**
- When users register, the OTP code will be shown directly in the success message
- Users can copy and paste the OTP to verify their email
- This allows full registration/login functionality without email setup

---

## To Enable Real Email Sending (Optional)

### Step 1: Get Gmail App Password
1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** (if not already enabled)
3. Go to **App passwords** (search for it in settings)
4. Generate a new app password for "Mail"
5. Copy the 16-character password

### Step 2: Configure Render Environment Variables
1. Go to https://dashboard.render.com
2. Click your **english-communication-backend** service
3. Go to **Environment** tab
4. Add these variables:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=ImproveCommunication
```

5. Click **Save Changes**
6. Render will automatically redeploy (takes 2-3 minutes)

### Step 3: Test
Once redeployed:
- Try registering with a new email
- You should receive the OTP code via email
- The code will also still show in the success message as a backup

---

## Alternative Email Services (Future)

If you need higher email limits:

### **Resend** (Recommended)
- 100 emails/day free
- 3,000 emails/month for $20
- Better deliverability than Gmail
- No 2FA required

### **SendGrid**
- 100 emails/day free forever
- Very reliable
- Industry standard

---

## Current Functionality

**Without Email Configuration:**
- ✅ Full registration works
- ✅ OTP shown in success message
- ✅ User can copy/paste OTP
- ✅ Complete account creation
- ✅ Login works perfectly

**With Email Configuration:**
- ✅ Everything above +
- ✅ Users receive OTP via email
- ✅ More professional experience
- ✅ Better for production use

---

## Your App URLs

**Frontend:** https://english-communication-backend.onrender.com/frontend/index.html  
**Backend API:** https://english-communication-backend.onrender.com/health  
**Register Page:** https://english-communication-backend.onrender.com/frontend/templates/register.html

---

## Support

For issues or questions:
1. Check Render logs: Dashboard → Your Service → Logs
2. Test backend health: Visit `/health` endpoint
3. Test locally first: `cd backend && python main.py`
