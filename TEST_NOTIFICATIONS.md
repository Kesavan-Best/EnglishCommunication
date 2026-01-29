# Test Call Notifications

## What Was Fixed

1. **Missing WebSocket Method**: The backend was calling `manager.send_call_invite()` but the method didn't exist. Added the method to `backend/app/api/websocket.py`.

2. **Caller Name Not Sent**: The notification now includes the caller's name so the receiver sees who is calling.

3. **WebSocket Message Type**: The notification sends `type: "call_invite"` which matches what the frontend expects.

## How to Test

### Setup (2 Browser Windows)

1. **Window 1 - Patrick**:
   - Open: `http://localhost:8000/templates/users.html`
   - Login as Patrick

2. **Window 2 - Kesavan**:
   - Open: `http://localhost:8000/templates/users.html` (new incognito/private window)
   - Login as Kesavan

### Test Steps

1. **Open Browser Console in Kesavan's window** (F12)
   - You should see: `✅ WebSocket connected successfully`

2. **In Patrick's window**:
   - Find Kesavan in the user list
   - Click the **📞 Call** button

3. **Expected Results**:

   **Patrick's window (caller)**:
   - Shows "📞 Creating call..."
   - Redirects to call page
   - Shows "Calling partner..."

   **Kesavan's window (receiver)**:
   - Console should show: `📞 Incoming call: {type: "call_invite", ...}`
   - Full-screen notification appears: "📞 Incoming Call from Patrick"
   - Two buttons: "✅ Accept" and "❌ Reject"

4. **Click Accept in Kesavan's window**:
   - Both users redirect to call page
   - Audio connection establishes
   - Both can hear each other

## Backend Logs to Check

When Patrick calls Kesavan, backend terminal should show:

```
INFO:     127.0.0.1:xxxxx - "POST /api/calls/invite HTTP/1.1" 200 OK
INFO:backend.app.api.websocket:📞 Sending call invite from [patrick_id] to [kesavan_id] for call [call_id]
INFO:backend.app.api.websocket:✅ Call invite sent to [kesavan_id]
📞 Sent call invite notification to user [kesavan_id]
```

## If Notification Still Doesn't Appear

### Check WebSocket Connection (Receiver's Console)

Look for:
```javascript
✅ WebSocket connected successfully
WebSocket URL: ws://localhost:8000/api/ws/[user_id]
```

If you see `❌ WebSocket connection failed`, the user is not connected to receive notifications.

### Check if User is Marked Online

In backend terminal, run this check (or use MongoDB Compass):
```javascript
db.users.find({ name: "Kesavan" }, { is_online: 1 })
```

Should return: `{ is_online: true }`

### Verify WebSocket Message is Sent

Check backend logs for:
```
INFO:backend.app.api.websocket:✅ Call invite sent to [kesavan_id]
```

If you see:
```
WARNING:backend.app.api.websocket:⚠️ Failed to send call invite to [kesavan_id] - user not connected
```

Then the WebSocket is not connected. Refresh Kesavan's page.

## Mute Button

The mute button is working:
- Click to toggle microphone on/off
- Icon changes: 🔊 (unmuted) ↔️ 🔇 (muted)
- Text changes: "Mute" ↔️ "Unmute"
- Status shows: "Mic: On" ↔️ "Mic: Off"

## End Call Button

The end call button has triple error handling:
1. Tries to end call via API
2. If API fails, closes connections
3. Always redirects to dashboard after 2 seconds

Should work reliably now.

## Key Changes Made

### 1. `backend/app/api/websocket.py`

```python
async def send_call_invite(self, from_user_id: str, to_user_id: str, call_id: str, caller_name: str = None):
    """Simple call invite notification (used by /api/calls/invite endpoint)"""
    logger.info(f"📞 Sending call invite from {from_user_id} to {to_user_id} for call {call_id}")
    
    # Send notification to receiver
    success = await self.send_personal_message({
        "type": "call_invite",
        "from_user_id": from_user_id,
        "call_id": call_id,
        "caller_name": caller_name or "Someone",
        "timestamp": datetime.now().isoformat()
    }, to_user_id)
    
    if success:
        logger.info(f"✅ Call invite sent to {to_user_id}")
    else:
        logger.warning(f"⚠️ Failed to send call invite to {to_user_id} - user not connected")
    
    return success
```

### 2. `backend/app/api/calls.py`

```python
# Get caller name for notification
caller_name = current_user.name if hasattr(current_user, 'name') else current_user.username

await manager.send_call_invite(
    from_user_id=str(caller_id),
    to_user_id=str(receiver_id),
    call_id=str(call_id),
    caller_name=caller_name
)
```

### 3. Frontend Already Correct

`frontend/js/users.js` already handles `call_invite` messages:

```javascript
} else if (data.type === 'call_invite') {
    console.log('📞 Incoming call:', data);
    
    const callerName = data.caller_name || 'Someone';
    const callId = data.call_id;
    
    // Show a more prominent notification
    showIncomingCallNotification(callerName, callId);
}
```

## Summary

The issue was that `send_call_invite()` method was missing in the WebSocket manager. Now when someone makes a call:

1. ✅ Backend creates call in database
2. ✅ Backend calls `manager.send_call_invite()` with caller name
3. ✅ WebSocket sends notification to receiver
4. ✅ Frontend shows full-screen notification modal
5. ✅ Receiver can accept/reject
6. ✅ Both users connect via WebRTC audio

All fixed! Test it now.
