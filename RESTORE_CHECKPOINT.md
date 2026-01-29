# 🔖 RESTORE CHECKPOINT GUIDE

## Checkpoint Created: January 23, 2026

**Tag:** `checkpoint-before-webrtc`

### What's Working at This Checkpoint:

✅ User authentication
✅ WebSocket notifications (users receive call invites)
✅ Call notification popup appears
✅ Basic call page structure
✅ Backend running properly
✅ Database connected

### What's NOT Working:

❌ Jitsi iframe not loading (stuck on "Connecting...")
❌ End call button not responsive

---

## 🔄 How to Restore This Checkpoint

### Option 1: Restore Using Git Tag

```powershell
# Navigate to project directory
cd E:\english_communication

# View all checkpoints
git tag -l

# Restore to this checkpoint
git checkout checkpoint-before-webrtc

# If you want to create a new branch from this checkpoint
git checkout -b restore-branch checkpoint-before-webrtc
```

### Option 2: Restore Specific Files

If you only want to restore certain files:

```powershell
# Restore call.html
git checkout checkpoint-before-webrtc -- frontend/templates/call.html

# Restore calls.py
git checkout checkpoint-before-webrtc -- backend/app/api/calls.py

# Restore all frontend files
git checkout checkpoint-before-webrtc -- frontend/
```

### Option 3: View Checkpoint Changes

```powershell
# See what changed at this checkpoint
git show checkpoint-before-webrtc

# Compare current state with checkpoint
git diff checkpoint-before-webrtc
```

---

## 📋 File State at Checkpoint

### Backend Files Modified:

- `backend/app/api/calls.py` - Call endpoints with validation
- `backend/app/api/websocket.py` - WebSocket notifications
- `backend/app/models.py` - Call tracking fields
- `backend/app/api/users.py` - User management

### Frontend Files Modified:

- `frontend/templates/call.html` - Call page (iframe approach)
- `frontend/js/users.js` - WebSocket handling & notifications
- `frontend/js/dashboard.js` - Dashboard WebSocket

### New Files Created:

- `frontend/templates/call-results.html`
- `frontend/templates/quiz.html`
- `backend/reset_call_counts.py`

---

## 🚀 Quick Restore Commands

### Full Restore (Nuclear Option)

```powershell
cd E:\english_communication
git reset --hard checkpoint-before-webrtc
```

**⚠️ WARNING:** This will DESTROY all changes after checkpoint!

### Safe Restore (Recommended)

```powershell
cd E:\english_communication
git checkout -b safe-restore checkpoint-before-webrtc
```

This creates a new branch so you don't lose anything.

---

## 🔍 Verify Checkpoint

```powershell
# Check if tag exists
cd E:\english_communication
git tag -l | Select-String "checkpoint-before-webrtc"

# View checkpoint details
git show checkpoint-before-webrtc --stat
```

---

## 📦 Backup Current State Before Restoring

```powershell
# Always create a backup branch before restoring
cd E:\english_communication
git branch backup-$(Get-Date -Format "yyyy-MM-dd-HHmm")
git checkout -b restore-test checkpoint-before-webrtc
```

---

## 🛠️ After Restoring

1. **Restart Backend:**

   ```powershell
   cd E:\english_communication\backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
2. **Clear Browser Cache:**

   - Chrome: `Ctrl + Shift + Delete`
   - Firefox: `Ctrl + Shift + Delete`
3. **Test:**

   - Open 2 browsers
   - Login as different users
   - Test call notification

---

**Created:** January 23, 2026
**Commit:** d31eb26
**Tag:** checkpoint-before-webrtc
