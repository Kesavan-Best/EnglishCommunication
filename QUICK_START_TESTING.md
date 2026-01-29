# Quick Start Guide - Call System Testing

## 🚀 Start the System

### 1. Start MongoDB (if not running)
```powershell
# Check if MongoDB is running
Get-Process mongod

# If not running, start it
# Usually MongoDB runs as a service automatically
```

### 2. Start Backend
```powershell
cd e:\english_communication\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 3. Open Frontend
Open two browser windows:
- Window 1: `file:///e:/english_communication/frontend/index.html`
- Window 2: `file:///e:/english_communication/frontend/index.html` (Incognito mode)

---

## 👥 Create Test Users

### User A:
- **Email**: alice@test.com
- **Password**: password123
- **Name**: Alice

### User B:
- **Email**: bob@test.com
- **Password**: password123
- **Name**: Bob

**Register both users first!**

---

## 🎯 Quick Test Flow

### Window 1 (Alice):
1. Login as Alice
2. Go to **Users** page
3. Wait for Bob to appear as 🟢 Online
4. Click **"📞 Call"** button on Bob's card

### Window 2 (Bob):
1. Login as Bob
2. Stay on **Dashboard** or **Users** page
3. **Wait for popup**: "Incoming Call from Alice"
4. Click **"✓ Accept"**

### Both Windows:
- Should redirect to call page
- Should see "🟢 Connected"
- Timer starts
- **Start talking!**
- Watch "Live Conversation" section
- See messages appear in real-time

---

## 💬 Test Conversation

### Alice says:
```
"Hi Bob, how are you doing today?"
```

### Bob says:
```
"I'm doing great Alice, thanks for asking! How about you?"
```

### Alice says:
```
"I'm wonderful! Do you like the new transcription feature?"
```

### Bob says:
```
"Yes, it's amazing! I can see everything we're saying in real-time."
```

**Expected**: Both users see all 4 messages with correct labels.

---

## 🛑 End Call & View Results

### Both Users:
1. Click **"📞 End Call"** button
2. Automatically redirects to results page
3. See AI feedback with:
   - AI Rating (7-9 if you spoke 50+ words)
   - Strengths
   - Weaknesses
   - Recommended Topics
   - Quiz available

---

## ✅ Verify Everything Works

### 1. Call Invitation ✅
- [ ] Bob received notification within 1 second
- [ ] Notification showed "Alice" as caller
- [ ] Accept button worked immediately
- [ ] Both users connected automatically

### 2. Real-Time Transcription ✅
- [ ] Messages appeared as users spoke
- [ ] Correct speaker labels (You vs Partner)
- [ ] Auto-scrolled to latest message
- [ ] Stopped when muted

### 3. Data Storage ✅
Check MongoDB:
```javascript
db.calls.find({}).sort({created_at: -1}).limit(1).pretty()
```
- [ ] `caller_transcript` has Alice's text
- [ ] `receiver_transcript` has Bob's text
- [ ] `conversation` array has all messages
- [ ] Timestamps are correct

### 4. AI Analysis ✅
- [ ] Both users got individual feedback
- [ ] Feedback mentioned participation
- [ ] Ratings were different for each user
- [ ] Based on actual word count

---

## 🎉 Success!

If all checkboxes are marked, the system is working perfectly!

---

## 🔧 If Something Doesn't Work

### Backend Not Starting?
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# If needed, kill the process
taskkill /PID <process_id> /F
```

### WebSocket Not Connecting?
- Check browser console for errors
- Ensure backend is running on port 8000
- Try refreshing the page

### Transcription Not Working?
- Allow microphone permissions in browser
- Use Chrome or Edge (best support)
- Check if muted
- Speak clearly and wait 2 seconds

### MongoDB Connection Issues?
```powershell
# Check MongoDB service
Get-Service MongoDB

# Restart if needed
Restart-Service MongoDB
```

---

## 📝 Quick Commands Reference

### Backend:
```powershell
# Start backend
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Check if running
curl http://localhost:8000/docs
```

### MongoDB:
```powershell
# Connect to MongoDB
mongosh

# Use database
use english_communication

# Check recent calls
db.calls.find({}).sort({created_at: -1}).limit(3).pretty()

# Count calls with transcripts
db.calls.countDocuments({caller_transcript: {$exists: true, $ne: ""}})
```

### Frontend:
```
Just open in browser:
file:///e:/english_communication/frontend/index.html
```

---

## 🎬 Full Demo Video Script

1. **Show both browser windows side-by-side**
2. **Window 1**: Alice logs in, goes to Users
3. **Window 2**: Bob logs in, stays on Dashboard
4. **Window 1**: Alice clicks "Call" on Bob
5. **Window 2**: Popup appears instantly → Bob clicks "Accept"
6. **Both**: Connected, timer starts
7. **Alice speaks**: "Hi, how are you?"
8. **Show**: Message appears in both windows
9. **Bob speaks**: "I'm good, thanks!"
10. **Show**: Message appears in both windows
11. **Continue** conversation for 30 seconds
12. **Both**: Click "End Call"
13. **Show**: Results page with different feedback for each user

---

## 📊 Performance Benchmarks

### Expected Timings:
- Call invitation delivery: < 1 second
- Audio connection: 2-4 seconds
- Transcription delay: 1-2 seconds
- Message broadcast: < 0.5 seconds
- End call processing: < 2 seconds
- AI analysis: < 2 seconds

### Browser Performance:
- Chrome: Best (recommended)
- Edge: Excellent
- Safari: Good
- Firefox: Limited (speech recognition)

---

## 🎯 Next Steps After Testing

1. ✅ Test with real conversations
2. ✅ Try different accents and speeds
3. ✅ Test mute/unmute multiple times
4. ✅ Test long calls (5+ minutes)
5. ✅ Verify MongoDB data integrity
6. ✅ Check AI feedback quality
7. ✅ Test with multiple concurrent calls

---

**Ready to test? Let's go! 🚀**
