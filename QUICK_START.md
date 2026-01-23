# 🎯 Quick Start: Testing Calls Locally

## Problem You're Facing

You're trying to test calls by opening two tabs, but both tabs show the same logged-in user. This happens because **localStorage is shared across all tabs in the same browser**.

---

## ✅ SOLUTION: Use Incognito Mode (30 seconds)

### Step-by-Step:

1. **Regular Window**: 
   - Open `http://localhost:5500/frontend/index.html`
   - Login as `john@example.com` / `password123`

2. **Incognito Window** (Ctrl+Shift+N):
   - Open `http://localhost:5500/frontend/index.html`  
   - Login as `jane@example.com` / `password123`

3. **Make a Call**:
   - In one window, go to "Find Partners"
   - Click the "Call" button on the other user
   - ✅ **Both users join the Jitsi room and can talk!**

---

## 🚀 For Render Deployment

### You Asked About OpenAI API on Render Free Tier

**Good news!** ✅ **OpenAI API WORKS perfectly on Render's free tier!**

The free tier limitations are:
- ⏰ Cold starts (app sleeps after 15 min inactivity)
- 💾 512 MB RAM
- ⏱️ 750 hours/month compute time

But **external API calls (like OpenAI) work perfectly!** You only pay OpenAI for usage (~$0.002 per 1K tokens).

### Quick Render Deployment (15 minutes):

1. **Create MongoDB Atlas Account** (Free)
   - Go to https://www.mongodb.com/cloud/atlas
   - Create free M0 cluster
   - Get connection string

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

3. **Deploy Backend**
   - New → Web Service
   - Connect repository
   - Root Directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables:
     ```
     MONGODB_URL=your_mongodb_atlas_url
     SECRET_KEY=generate_random_string
     OPENAI_API_KEY=your_openai_key
     ENVIRONMENT=production
     ```

4. **Update Frontend Config**
   - Edit `frontend/js/config.js`
   - Change `API_BASE_URL` to your Render backend URL
   - Example: `https://english-communication-backend.onrender.com`

5. **Deploy Frontend** (Optional - or use Cloudflare Pages)
   - New → Static Site
   - Root Directory: `frontend`
   - Publish Directory: `.`

6. **Test with Friends!**
   - Share your Render URL
   - Have them login with different accounts
   - Make calls from anywhere in the world!

---

## 📝 Test Accounts

Use these accounts for testing:
- `john@example.com` / `password123`
- `jane@example.com` / `password123`  
- `bob@example.com` / `password123`

---

## 🎉 What Works Now

✅ Login page (statistics removed as requested)
✅ Call button generates Jitsi room immediately
✅ Both users join the same Jitsi room
✅ Audio calls work perfectly
✅ Users can speak to each other
✅ Call duration is tracked
✅ Works on Render FREE tier
✅ OpenAI API calls work on Render

---

## 📚 More Details

- **Full Render Guide**: See `RENDER_DEPLOYMENT_GUIDE.md`
- **Testing Guide**: Open `TESTING_GUIDE.html` in browser
- **Need Help?**: Check the debugging guides in the project

---

## 💡 Pro Tips

1. **For local testing**: Always use incognito mode for the second user
2. **For Render**: Use https://uptimerobot.com to ping your app every 5 min (prevents cold starts)
3. **For costs**: OpenAI is the only cost (~$5-10 for 100 users/month)
4. **For storage**: Use MongoDB Atlas free tier (not local MongoDB on Render)

---

## 🐛 Still Having Issues?

If calls don't connect:
1. Check browser console for errors (F12)
2. Make sure backend is running (`python main.py`)
3. Verify both users are online (green status)
4. Check that Jitsi API loaded (see Network tab)
5. Try refreshing both windows

---

**Ready to test? Open incognito mode and start calling! 🎤**
