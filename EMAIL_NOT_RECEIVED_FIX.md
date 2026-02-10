# 🔍 EMAIL NOT RECEIVED - DEBUGGING GUIDE

## Problem: User doesn't receive OTP email

**Symptoms:**
- Registration shows "OTP sent successfully" 
- BUT user doesn't receive email
- Email not in inbox or spam folder

---

## 🎯 STEP 1: Check Render Logs (MOST IMPORTANT)

### Go to Render Dashboard:
1. https://dashboard.render.com
2. Click your service: "english-communication-backend"
3. Click **"Logs"** tab
4. Look for OTP sending attempts

### What to look for:

#### ✅ **SCENARIO A: Email Actually Sent**
```
🔄 Attempting to send OTP to user@example.com...
📧 Preparing OTP email for user@example.com
📧 Attempting to send email to user@example.com...
Connecting to smtp.gmail.com:587...
Starting TLS...
Logging in as your***@gmail.com...
Sending message...
✅ Email sent successfully to user@example.com
📬 Email should arrive in 1-2 minutes. Check spam folder if not in inbox.
✅ OTP email SUCCESSFULLY sent to user@example.com
📧 From: your-email@gmail.com
📨 Check inbox and spam folder
```

**If you see this:**
- Email WAS sent from your Gmail
- Check user's **SPAM/JUNK folder** (90% of time it's here!)
- Check Gmail's "Promotions" or "Updates" tab
- Email may take 1-5 minutes to arrive
- **Action:** Tell user to check spam folder

---

#### ❌ **SCENARIO B: Email NOT Configured**
```
⚠️  Email service not configured. Set SMTP_USER and SMTP_PASSWORD environment variables.
🔄 Attempting to send OTP to user@example.com...
⚠️  Email service not configured. Set SMTP_USER and SMTP_PASSWORD. - Skipping email to user@example.com
❌ Email FAILED to send to user@example.com
❌ Error: Email service not configured. Set SMTP_USER and SMTP_PASSWORD.
🔐 OTP for testing: 123456
```

**If you see this:**
- SMTP credentials NOT set in Render
- Email cannot be sent
- **FIX:** Add environment variables (see Step 2 below)

---

#### ❌ **SCENARIO C: Wrong Password**
```
📧 Attempting to send email to user@example.com...
Connecting to smtp.gmail.com:587...
Starting TLS...
Logging in as your***@gmail.com...
❌ Auth error: SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD. Error: (535, b'5.7.8 Username and Password not accepted')
❌ Email FAILED to send to user@example.com
❌ Error: SMTP authentication failed...
```

**If you see this:**
- Using wrong password (regular password instead of App Password?)
- **FIX:** Regenerate Gmail App Password (see Step 3 below)

---

#### ❌ **SCENARIO D: Connection Timeout**
```
📧 Attempting to send email to user@example.com...
Connecting to smtp.gmail.com:587...
❌ Timeout sending email to user@example.com: Connection timeout after 30s. Check network/firewall settings.
```

**If you see this:**
- Render can't reach Gmail SMTP server
- Possible firewall blocking
- **FIX:** Try alternative SMTP service (see Step 4 below)

---

## 🔧 STEP 2: Configure SMTP on Render

### Go to Render Environment Variables:
1. Dashboard → Your Service → **Environment** tab
2. Click **"Add Environment Variable"**

### Add ALL of these variables:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-actual-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
FROM_EMAIL=your-actual-email@gmail.com
FROM_NAME=ImproveCommunication
SMTP_TIMEOUT=30
```

⚠️ **CRITICAL:**
- Replace `your-actual-email@gmail.com` with YOUR real Gmail
- Replace `xxxx xxxx xxxx xxxx` with your GMAIL APP PASSWORD (see Step 3)
- Do NOT use your regular Gmail password - it won't work!
- Include the spaces in the app password (or remove them, both work)

### Save Changes:
- Click **"Save Changes"**
- Render will automatically redeploy (2-3 minutes)
- Wait for deployment to complete

---

## 🔑 STEP 3: Get Gmail App Password (NOT regular password!)

### Why you need this:
- Gmail blocks regular passwords from apps
- You MUST use an "App Password"
- It's a 16-character password specifically for apps

### How to get it:

#### A. Enable 2-Step Verification FIRST:
1. Go to: https://myaccount.google.com/security
2. Find "2-Step Verification"
3. Click "Get Started" and follow steps
4. **WAIT 24 hours** (Gmail requires this before App Passwords work)

#### B. Generate App Password:
1. Go to: https://myaccount.google.com/apppasswords
2. You may need to sign in again
3. Select:
   - **App:** "Mail"
   - **Device:** "Other (Custom name)" → type "Render App"
4. Click **"Generate"**
5. Copy the 16-character password (like: `abcd efgh ijkl mnop`)
6. **SAVE THIS** - you can't see it again!

#### C. Add to Render:
- Go back to Render Environment Variables
- Set `SMTP_PASSWORD=abcd efgh ijkl mnop`
- Click "Save Changes"

---

## 🧪 STEP 4: Test Email Configuration

### Option A: Check Render Logs After Registration

1. Try to register on your app
2. Immediately check Render logs
3. Look for the log patterns above
4. This tells you exactly what happened

### Option B: Test Locally

```powershell
# Set environment variables locally
$env:SMTP_USER="your-email@gmail.com"
$env:SMTP_PASSWORD="your-app-password"

# Run test
cd backend
python test_email.py
```

Enter a test email and see if it arrives.

---

## 📧 STEP 5: Check Where Emails Go

### If logs show "Email sent successfully" but user doesn't receive:

#### Check 1: Spam Folder
- 90% of OTP emails go here first time
- Tell user to check **Spam/Junk** folder
- Mark as "Not Spam" to fix for future

#### Check 2: Gmail Tabs
- Gmail has tabs: Primary, Social, Promotions, Updates
- OTP emails often go to **Promotions** tab
- Check all tabs

#### Check 3: Email Address Typo
- Did user type email correctly?
- Check Render logs for the exact email address used
- Common mistakes: @gamil.com, @gmai.com

#### Check 4: Email Blocks
- Some organizations block external emails
- Corporate emails may have strict filters
- Try with a personal Gmail/Yahoo

#### Check 5: Delivery Time
- Emails can take 1-5 minutes
- Wait a bit and check spam folder

---

## 🔄 ALTERNATIVE: Use Better Email Service

Gmail has limitations. Consider these alternatives:

### Option A: Resend (Recommended)
**Why:** Better deliverability, rarely goes to spam

```bash
# 1. Sign up: https://resend.com (free 3,000 emails/month)
# 2. Get API key from dashboard
# 3. Update Render Environment Variables:

SMTP_HOST=smtp.resend.com
SMTP_PORT=465
SMTP_USER=resend
SMTP_PASSWORD=re_your_api_key_here
FROM_EMAIL=onboarding@resend.dev
```

### Option B: SendGrid
```bash
# 1. Sign up: https://sendgrid.com
# 2. Get API key
# 3. Update Render:

SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your_sendgrid_api_key
FROM_EMAIL=your-verified-sender@yourdomain.com
```

---

## 🐛 STEP 6: Common Issues & Fixes

### Issue: "Email sent successfully" but nothing arrives

**Possible causes:**
1. Email in spam folder (check there FIRST!)
2. Gmail tabs (check Promotions/Updates)
3. Email address typo
4. Corporate email blocking
5. Takes 1-5 minutes to arrive

**Fix:**
- Wait 5 minutes
- Check spam thoroughly
- Try different email address
- Check all Gmail tabs

### Issue: "SMTP authentication failed"

**Causes:**
1. Using regular password instead of App Password
2. 2-Step Verification not enabled
3. Typo in email or password
4. App Password not generated

**Fix:**
1. Regenerate App Password
2. Double-check SMTP_USER email is correct
3. Copy App Password EXACTLY (all 16 chars)
4. Make sure 2-Step Verification is enabled

### Issue: "Email service not configured"

**Causes:**
- SMTP_USER or SMTP_PASSWORD not set in Render

**Fix:**
1. Go to Render Dashboard → Environment
2. Add both SMTP_USER and SMTP_PASSWORD
3. Save and redeploy

### Issue: "Connection timeout"

**Causes:**
- Render can't reach Gmail servers
- Firewall blocking port 587
- Network issues

**Fix:**
1. Increase timeout: `SMTP_TIMEOUT=60`
2. Try port 465 instead of 587: `SMTP_PORT=465`
3. Switch to Resend or SendGrid (more reliable)

---

## 📊 Debugging Checklist

Go through this checklist:

- [ ] Checked Render logs for exact error
- [ ] SMTP_USER is set in Render Environment
- [ ] SMTP_PASSWORD is set (App Password, not regular)
- [ ] 2-Step Verification enabled in Gmail
- [ ] App Password generated correctly
- [ ] Waited 24 hours after enabling 2-Step (if new)
- [ ] Checked user's spam/junk folder
- [ ] Checked all Gmail tabs (Promotions, etc.)
- [ ] Verified email address spelling is correct
- [ ] Waited 5 minutes for email to arrive
- [ ] Tested with different email address
- [ ] Render service redeployed after adding variables

---

## 🎯 Quick Fix Steps

### If email shows "sent" but not received:

1. **First:** Check Render logs - see EXACT error
2. **Second:** Tell user to check SPAM folder (90% here!)
3. **Third:** Wait 5 minutes - emails can be delayed
4. **Fourth:** Check environment variables are set
5. **Fifth:** Try alternative email service (Resend)

### Most Common Solution:
> **"Check spam folder!"** - This solves 90% of cases

---

## 📞 Still Not Working?

### Debug in Render Logs:

Search for these patterns:
- `OTP to` - Shows registration attempts
- `❌` - Shows errors
- `✅ Email sent` - Shows successes
- `SMTP` - Shows email sending details

### Copy This From Logs:

When asking for help, include:
```
[Time] 🔄 Attempting to send OTP to [email]
[Time] [Success/Error message]
[Time] [Any ❌ error details]
```

This shows exactly what's happening!

---

## ✅ Success Indicators

You'll know it's working when:

**Render Logs Show:**
```
✅ Email service configured: you***@gmail.com
🔄 Attempting to send OTP to user@test.com...
✅ Email sent successfully to user@test.com
📬 Email should arrive in 1-2 minutes
✅ OTP email SUCCESSFULLY sent to user@test.com
```

**User Receives:**
- Email with OTP code
- In inbox or spam folder
- Within 1-5 minutes
- From your configured email

---

## 🎉 Summary

**The #1 thing to check:** RENDER LOGS!

They tell you EXACTLY what happened:
- ✅ Email sent → Check spam folder
- ❌ Not configured → Add environment variables
- ❌ Auth failed → Fix App Password
- ❌ Timeout → Try alternative service

**90% of "not received" emails are in SPAM folder!**

---

*Last Updated: February 10, 2026*
*Fixes Applied: Enhanced logging + verification*
