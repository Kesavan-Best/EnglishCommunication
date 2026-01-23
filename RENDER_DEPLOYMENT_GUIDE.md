# 🚀 Render Deployment Guide

## Step 1: Prepare Your Backend for Render

### 1.1 Check/Update `requirements.txt`
Make sure all dependencies are listed in `backend/requirements.txt`

### 1.2 Create `render.yaml` (Optional but Recommended)
This file tells Render how to deploy your app.

### 1.3 Update CORS Settings
Your backend needs to accept requests from Render frontend URL.

### 1.4 Set Environment Variables
You'll need to configure these in Render dashboard.

---

## Step 2: Deploy Backend to Render

### 2.1 Create Render Account
1. Go to https://render.com
2. Sign up with GitHub (recommended)

### 2.2 Create New Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository (or use this project)
3. Configure:
   - **Name**: `english-communication-backend`
   - **Environment**: `Python 3`
   - **Region**: Choose closest to you
   - **Branch**: `main` (or your branch)
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### 2.3 Add Environment Variables
In Render dashboard, go to "Environment" and add:

```
MONGODB_URL=your_mongodb_connection_string
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-url.onrender.com,https://your-frontend-url.pages.dev
```

**Important**: 
- Get free MongoDB from https://www.mongodb.com/cloud/atlas (Free tier M0)
- Your OpenAI API key works on Render free tier!

### 2.4 Deploy
Click "Create Web Service" and wait for deployment (5-10 minutes)

---

## Step 3: Deploy Frontend

### Option A: Render Static Site (Recommended)

1. Click "New +" → "Static Site"
2. Configure:
   - **Name**: `english-communication-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: Leave empty (static files)
   - **Publish Directory**: `.` (current directory)

### Option B: Cloudflare Pages or Netlify
Both have better free tiers for static sites!

---

## Step 4: Update Frontend Configuration

After deployment, you'll have URLs like:
- Backend: `https://english-communication-backend.onrender.com`
- Frontend: `https://english-communication-frontend.onrender.com`

Update `frontend/js/config.js`:

```javascript
// Change from localhost to your Render URL
const API_BASE_URL = 'https://english-communication-backend.onrender.com';
```

---

## Step 5: Testing Calls on Render

### Two Users on Same Computer:
1. **Browser 1 (Regular)**: https://your-app.onrender.com → Login as john@example.com
2. **Browser 2 (Incognito)**: https://your-app.onrender.com → Login as jane@example.com
3. Click "Call" and both users join Jitsi Meet room!

### Two Users on Different Computers:
Just share your Render URL with a friend!

---

## 🔥 Important Notes for Render Free Tier

### ✅ WHAT WORKS:
- ✅ OpenAI API calls (external API calls work fine!)
- ✅ Jitsi Meet calls (uses P2P connection)
- ✅ WebSocket connections
- ✅ File uploads (limited storage)
- ✅ Background tasks

### ⚠️ LIMITATIONS:
- ⏰ **Cold starts**: App sleeps after 15 minutes of inactivity (first request takes ~30 seconds)
- 💾 **RAM**: 512 MB (enough for this app)
- ⏱️ **Compute**: 750 hours/month (enough for testing/small usage)
- 📦 **Storage**: Temporary (files deleted on restart)

### 💡 Solutions for Cold Starts:
1. Use https://uptimerobot.com (free) to ping your app every 5 minutes
2. Or accept 30-second delay on first request after inactivity

---

## 🎯 Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Render Backend | **FREE** | 750 hrs/month |
| Render Frontend | **FREE** | Unlimited bandwidth |
| MongoDB Atlas | **FREE** | 512 MB storage |
| OpenAI API | **Pay per use** | ~$0.002 per 1K tokens |
| Jitsi Meet | **FREE** | Peer-to-peer calls |

**Total for 100 users/month**: ~$5-10 (mostly OpenAI)

---

## 🐛 Troubleshooting

### Backend won't start:
- Check logs in Render dashboard
- Verify all environment variables are set
- Check `Start Command` is correct

### CORS errors:
- Add frontend URL to `CORS_ORIGINS` in Render environment variables
- Update backend `config.py` to use environment variable

### Calls not connecting:
- Check browser console for errors
- Verify Jitsi Meet external API is loaded
- Both users must be online and on the site

### OpenAI errors:
- Verify `OPENAI_API_KEY` is set in Render
- Check OpenAI account has credits
- Monitor usage at https://platform.openai.com/usage

---

## 📝 Quick Checklist

- [ ] MongoDB Atlas account created (free)
- [ ] MongoDB connection string copied
- [ ] OpenAI API key ready
- [ ] Render account created
- [ ] Backend deployed to Render
- [ ] Environment variables set in Render
- [ ] Frontend deployed (Render/Cloudflare/Netlify)
- [ ] `config.js` updated with Render backend URL
- [ ] Test with two incognito tabs
- [ ] Invite friend to test calls!

---

## 🎉 You're Done!

Your app is now live and can handle:
- ✅ Multiple users from anywhere in the world
- ✅ OpenAI API processing
- ✅ Real-time calls via Jitsi
- ✅ All for FREE (except OpenAI usage)

Share your Render URL with friends and start practicing English! 🗣️
