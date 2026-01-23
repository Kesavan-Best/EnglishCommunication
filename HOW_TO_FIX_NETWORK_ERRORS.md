# 🔧 How to Fix "Network error: Unexpected token '<'" Error

## ❌ What This Error Means

When you see: **"Network error: Unexpected token '<'"**

This means:
- Your **frontend** is expecting JSON data (like `{"success": true}`)
- But it's receiving **HTML** instead (which starts with `<html>` or `<!DOCTYPE...`)
- JavaScript's `response.json()` tries to parse HTML and fails because `<` is not valid JSON

---

## 🎯 The Root Cause in YOUR Application

Your backend server (FastAPI) is **NOT RUNNING** when you try to register/login.

When the frontend makes a request to:
- `http://localhost:8000/api/users/login`
- `http://localhost:8000/api/users/register`

And the server isn't running, the browser gets:
- Connection refused error
- Or an HTML error page from the browser
- Or a default "Cannot connect" page

---

## ✅ How to Fix It (Step-by-Step)

### **Step 1: Start Your Backend Server**

Open a terminal in VS Code and run:

```powershell
cd backend
python main.py
```

You should see output like:
```
Initializing database...
Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**⚠️ IMPORTANT:** Keep this terminal running! Don't close it.

---

### **Step 2: Open Your Frontend**

Now open your browser and go to:
- `http://localhost:8000/frontend/templates/login.html`
- Or `http://localhost:8000/frontend/templates/register.html`

---

### **Step 3: Test Registration/Login**

Try registering or logging in. It should work now!

---

## 🔍 How to Check If Backend Is Running

### Method 1: Check the Terminal
Look for the terminal running `python main.py` - it should show:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Method 2: Test the Health Endpoint
Open browser and go to: `http://localhost:8000/health`

You should see:
```json
{"status": "healthy"}
```

If you see this, your backend is running! ✅

If you get "This site can't be reached", your backend is NOT running! ❌

---

## 🛠️ Common Variations of This Error

| Error Message | What It Means | Solution |
|--------------|---------------|----------|
| `Unexpected token '<'` | Receiving HTML instead of JSON | Start backend server |
| `NetworkError` or `Failed to fetch` | Cannot connect to server | Start backend server |
| `CORS policy` | Server is running but CORS issue | Already fixed in your code |
| `500 Internal Server Error` | Server crashed | Check backend terminal for errors |
| `404 Not Found` | Wrong API endpoint URL | Check API_ENDPOINTS in config.js |

---

## 🔧 If Backend Won't Start

### Issue 1: Port 8000 Already in Use

**Error:**
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Solution:**
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with the number from above)
taskkill /PID <PID> /F

# Then start backend again
cd backend
python main.py
```

### Issue 2: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```powershell
cd backend
pip install -r requirements.txt
```

### Issue 3: MongoDB Connection Error

**Error:**
```
ServerSelectionTimeoutError: localhost:27017
```

**Solution:**
- Install MongoDB and start it
- Or update `backend/app/core/config.py` with your MongoDB connection string

---

## 📝 Code Places to Check (For Future Issues)

### 1. **Frontend: Where API Calls Happen**

**File:** `frontend/js/config.js`
```javascript
const API_BASE_URL = 'http://localhost:8000';  // ← Make sure this matches your backend
```

**Files:** `frontend/templates/login.html` and `register.html`
```javascript
// Around line 179 in login.html and line 279 in register.html
const response = await fetch(API_ENDPOINTS.login, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
});

const data = await response.json();  // ← This line fails if response is HTML
```

**🔧 How to Fix:** Add better error handling:

```javascript
const response = await fetch(API_ENDPOINTS.login, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
});

// Check if response is actually JSON before parsing
const contentType = response.headers.get('content-type');
if (!contentType || !contentType.includes('application/json')) {
    throw new Error('Server is not responding with JSON. Is the backend running?');
}

const data = await response.json();
```

---

### 2. **Backend: Where Responses Are Sent**

**File:** `backend/app/api/users.py`
```python
@router.post("/login")
async def login(user_data: UserLoginRequest):
    # This returns JSON automatically
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(...)
    }
```

**File:** `backend/main.py`
```python
# CORS is already configured correctly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🎓 Prevention Checklist

Before testing your app, ALWAYS check:

- [ ] Backend terminal is running with `python main.py`
- [ ] You see "Uvicorn running on http://0.0.0.0:8000"
- [ ] `http://localhost:8000/health` returns `{"status": "healthy"}`
- [ ] You're accessing frontend through backend: `http://localhost:8000/frontend/...`
- [ ] Database (MongoDB) is running

---

## 🚀 Quick Start Guide (Every Time)

```powershell
# Terminal 1: Start Backend
cd backend
python main.py

# Then open browser to:
# http://localhost:8000/frontend/templates/login.html
```

---

## 💡 Pro Tips

1. **Keep backend terminal visible** - You'll see errors immediately
2. **Check browser console (F12)** - Shows exact error details
3. **Check Network tab (F12 → Network)** - Shows if request even reached server
4. **Use http://localhost:8000/frontend/...** - Not file:/// URLs

---

## 🆘 Still Not Working?

1. **Check browser console (F12)** - Copy the full error message
2. **Check backend terminal** - Copy any error messages
3. **Test health endpoint** - `http://localhost:8000/health`
4. **Check if MongoDB is running**
5. **Restart everything:**
   ```powershell
   # Stop backend (Ctrl+C)
   # Then restart
   cd backend
   python main.py
   ```

---

## 📌 Remember

**The error "Unexpected token '<'" is 99% of the time because:**
- ❌ Backend server is not running
- ✅ Solution: Start backend with `python main.py`

**Always start backend FIRST, then test frontend!**
