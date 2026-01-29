# Quick Testing Guide - Call System

## 🚀 How to Test the New Features

### Prerequisites
1. Backend running on `http://localhost:8000`
2. Two browser windows/tabs (or two different browsers)
3. Two user accounts registered

---

## Test 1: Call Invitation ✅

### Steps:
1. **Window 1** (User A):
   - Login as User A
   - Go to Users page
   - Find User B (should show "🟢 Online")
   - Click **"📞 Call"** button

2. **Window 2** (User B):
   - Login as User B
   - Stay on any page (Dashboard or Users)
   - **EXPECT**: Popup appears saying "Incoming Call from [User A]"
   - Click **"✓ Accept"**

3. **Result**:
   - Both users should be redirected to call.html
   - Connection established automatically
   - No manual clicking needed!

---

## Test 2: Real-Time Transcription 💬

### Steps:
1. **During the call** (both users):
   - Look for "Live Conversation" section below the timer
   - Start speaking into your microphone
   
2. **User A speaks**: "Hi, how are you?"
   - **User A sees**: "You: Hi, how are you?" (purple background)
   - **User B sees**: "Partner: Hi, how are you?" (lighter background)

3. **User B speaks**: "I'm good, thanks!"
   - **User B sees**: "You: I'm good, thanks!" (purple background)
   - **User A sees**: "Partner: I'm good, thanks!" (lighter background)

4. **Expected Behavior**:
   - Messages appear within 1-2 seconds
   - Auto-scrolls to show latest message
   - Works continuously during call
   - Stops when muted

---

## Test 3: Mute/Unmute Control 🔊

### Steps:
1. **Click "Mute" button**
   - Icon changes: 🔊 → 🔇
   - Text changes: "Mute" → "Unmute"
   - Transcription **stops** (no new messages)
   - Partner can't hear you

2. **Click "Unmute" button**
   - Icon changes: 🔇 → 🔊
   - Text changes: "Unmute" → "Mute"
   - Transcription **resumes**
   - Partner can hear you again

---

## Test 4: Conversation Storage 💾

### Steps:
1. Have a conversation for 30+ seconds
2. Speak several sentences each
3. End the call
4. **Check MongoDB**:
   ```javascript
   db.calls.find({}).sort({created_at: -1}).limit(1)
   ```
5. **Verify fields exist**:
   - `caller_transcript`: Full text of User A
   - `receiver_transcript`: Full text of User B
   - `conversation`: Array of message objects
   
6. **Example output**:
   ```json
   {
     "caller_transcript": "Hi how are you I'm doing well today...",
     "receiver_transcript": "I'm good thanks how about you That's great...",
     "conversation": [
       {"speaker": "caller", "text": "Hi how are you", "timestamp": "..."},
       {"speaker": "receiver", "text": "I'm good thanks", "timestamp": "..."}
     ]
   }
   ```

---

## Test 5: AI Analysis with Transcripts 🤖

### Steps:
1. Complete a call with meaningful conversation (50+ words each)
2. End the call
3. View results page
4. **Check AI Feedback**:
   - Should mention "You actively participated" or similar
   - Rating should reflect actual participation
   - If you spoke more, rating should be higher
   - Feedback should feel personalized

5. **Compare**:
   - User A's feedback ≠ User B's feedback
   - Each gets individual analysis
   - Based on their own transcript

---

## Troubleshooting 🔧

### Issue: "Speech recognition not supported"
**Solution**: Use Chrome, Edge, or Safari. Firefox has limited support.

### Issue: "No transcription appearing"
**Possible causes**:
1. Microphone not allowed → Check browser permissions
2. Muted → Click Unmute button
3. WebSocket disconnected → Check console for errors

### Issue: "Partner not receiving call invitation"
**Checks**:
1. Is User B actually online? (Check MongoDB: `is_online: true`)
2. Is WebSocket connected? (Check browser console)
3. Is backend running on port 8000?

### Issue: "Transcripts not saved to MongoDB"
**Checks**:
1. Check browser console for API errors
2. Verify `/api/calls/save-transcription` endpoint is working
3. Check MongoDB connection

---

## Browser Console Commands 🖥️

### Check WebSocket Status:
```javascript
console.log('WebSocket:', ws ? ws.readyState : 'Not connected');
// OPEN = 1, CLOSED = 3
```

### Check if Transcribing:
```javascript
console.log('Transcribing:', isTranscribing);
```

### Check Current Call:
```javascript
console.log('Call ID:', callId);
console.log('Is Caller:', isCaller);
console.log('Partner:', partnerUser);
```

---

## Expected Timeline ⏱️

### Call Setup (Should take < 5 seconds):
- Click "Call": Instant
- Receive notification: < 1 second
- Accept call: Instant
- Audio connection: 2-4 seconds
- Transcription start: 1-2 seconds after audio

### During Call:
- Speech → Text: 1-2 seconds delay
- Text → Partner sees: < 0.5 seconds
- Saving to DB: Background, no delay

### End Call:
- Click "End Call": Instant
- Save data: < 1 second
- AI analysis: < 2 seconds
- Redirect to results: Automatic

---

## Success Indicators ✅

### Call Invitation Working:
- ✅ Notification popup appears automatically
- ✅ No manual refresh needed
- ✅ Shows correct caller name
- ✅ Accept button works immediately

### Transcription Working:
- ✅ Messages appear as you speak
- ✅ Partner sees your messages
- ✅ You see partner's messages
- ✅ Correct speaker labels
- ✅ Auto-scrolls smoothly

### Storage Working:
- ✅ MongoDB has `caller_transcript`
- ✅ MongoDB has `receiver_transcript`
- ✅ MongoDB has `conversation` array
- ✅ Data persists after call

### AI Analysis Working:
- ✅ Feedback mentions participation
- ✅ Rating reflects actual content
- ✅ Each user gets different feedback
- ✅ Weaknesses are relevant
- ✅ Topics are useful

---

## Demo Script 🎬

### Perfect Testing Scenario:

**User A**: "Hi, how are you doing today?"
**User B**: "I'm doing great, thanks for asking! How about you?"
**User A**: "I'm wonderful! The weather is beautiful today."
**User B**: "Yes, it's perfect weather for a walk outside."
**User A**: "Absolutely! Do you have any plans for the weekend?"
**User B**: "I'm planning to visit a museum and then have dinner with friends."

**Expected Results**:
- 6 messages in transcription
- ~60-80 words total
- Clear conversation flow
- High AI ratings (7-8+)
- Positive feedback for both users

---

## Common Questions ❓

**Q: How long should I wait for transcription to appear?**
A: 1-2 seconds after you stop speaking. If nothing appears after 5 seconds, check your microphone.

**Q: Can I test with just one browser?**
A: Yes, but you'll need two tabs and two user accounts. Open one in regular mode, one in incognito.

**Q: Does the transcription save if I don't speak?**
A: No transcription is saved if you're silent or muted.

**Q: What if my accent isn't recognized well?**
A: Speech recognition accuracy varies. Speak clearly and at moderate speed. The system will improve over time.

**Q: Can I see the raw transcription data?**
A: Yes, check MongoDB `calls` collection or add a console.log in the frontend.

---

## Need Help? 🆘

**Backend Logs**:
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Watch console for logs
```

**Frontend Console**:
- F12 → Console tab
- Look for errors in red
- WebSocket messages logged as "📨"

**MongoDB Check**:
```javascript
// Check recent calls
db.calls.find({}).sort({created_at: -1}).limit(5).pretty()

// Check specific call
db.calls.findOne({_id: ObjectId("...")})

// Check user transcripts
db.calls.find({
  $or: [
    {caller_transcript: {$exists: true, $ne: ""}},
    {receiver_transcript: {$exists: true, $ne: ""}}
  ]
}).count()
```

---

**Happy Testing! 🎉**
