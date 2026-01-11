# Debugging "Unexpected token '<'" Error

## 🔍 What This Error Means

When you see `Unexpected token '<'`, it means:
- **Your JavaScript is trying to parse JSON** from an API response
- **But it received HTML instead** (which starts with `<`)

Example:
```javascript
// Expected JSON:
{"access_token": "abc123", "user": {...}}

// Got HTML instead:
<!DOCTYPE html>
<html>...

// Result: Error parsing '<' as JSON
```

## 🚨 Common Causes

### 1. Wrong API URL
```javascript
// ❌ Wrong - relative path when frontend is on different port/domain
fetch('/api/users/login')

// ✅ Correct - full URL
fetch('http://localhost:8000/api/users/login')
```

### 2. Backend Not Running
- Server is offline
- Returns 404 error page (HTML) instead of JSON

### 3. CORS Issues
- Browser blocks request
- Returns error page (HTML)

### 4. Wrong HTTP Method
```javascript
// If endpoint expects POST but you send GET
fetch('/api/users/login')  // ❌ Missing method: 'POST'
```

## 🛠️ How to Debug (Step by Step)

### Step 1: Open Browser DevTools
1. Press `F12` (Windows) or `Cmd+Option+I` (Mac)
2. Click on **Network** tab
3. Reproduce the error (try logging in)

### Step 2: Find the Failed Request
Look for the API request (e.g., `/api/users/login`)

Check these columns:

| Column | What to Look For | Meaning |
|--------|------------------|---------|
| **Status** | 200 = OK | 404 = Not Found |
| | 500 = Server Error | CORS = Cross-origin blocked |
| **Type** | should be `json` or `xhr` | if `document` = wrong URL |
| **Size** | should be small (few KB) | Large size = HTML error page |

### Step 3: Inspect the Response
Click on the request → **Response** tab

#### If you see JSON:
```json
{
  "access_token": "eyJ...",
  "user": {...}
}
```
✅ Backend is working! Problem is in frontend code.

#### If you see HTML:
```html
<!DOCTYPE html>
<html>
  <head><title>404 Not Found</title></head>
  ...
```
❌ Backend returned error page.

**Common HTML responses:**
- `404 Not Found` → Wrong URL
- `500 Internal Server Error` → Backend code error
- `CORS policy` → CORS configuration issue

### Step 4: Check Request Details
Click on the request → **Headers** tab

#### Check Request URL:
```
❌ file:///C:/project/frontend/api/users/login  (Wrong - file protocol)
❌ http://localhost:5500/api/users/login        (Wrong - frontend server)
✅ http://localhost:8000/api/users/login        (Correct - backend server)
```

#### Check Request Headers:
```
Content-Type: application/json  ✅
Authorization: Bearer abc123     ✅ (if needed)
```

### Step 5: Check Console
**Console** tab shows JavaScript errors:

```javascript
❌ SyntaxError: Unexpected token '<' in JSON at position 0
   at JSON.parse()
```

This confirms: tried to parse HTML as JSON.

## ✅ Solutions

### Solution 1: Use Full API URL
In your JavaScript:
```javascript
// Create config file (config.js)
const API_BASE_URL = 'http://localhost:8000';

// Use in fetch
fetch(`${API_BASE_URL}/api/users/login`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password})
})
```

### Solution 2: Serve Frontend from Backend
Instead of opening `file:///...`:

1. Start backend:
   ```bash
   cd backend
   python main.py
   ```

2. Open in browser:
   ```
   http://localhost:8000/frontend/templates/login.html
   ```

### Solution 3: Add Error Handling
Always check response before parsing:

```javascript
try {
    const response = await fetch(API_URL);
    
    // Check if response is OK
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Expected JSON, got:', text);
        throw new Error('Server returned non-JSON response');
    }
    
    const data = await response.json();
    // Use data...
    
} catch (error) {
    console.error('API Error:', error);
    alert(`Error: ${error.message}`);
}
```

## 📋 Quick Checklist

Before calling API:
- [ ] Backend server is running
- [ ] API URL includes full domain (http://localhost:8000)
- [ ] Content-Type header is set to 'application/json'
- [ ] Request body is stringified: `JSON.stringify(data)`
- [ ] CORS is enabled on backend
- [ ] Endpoint path is correct (/api/users/login)
- [ ] HTTP method matches backend (POST, GET, etc.)

## 🎯 Prevention Tips

### 1. Centralize API Configuration
Create `config.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';
const API_ENDPOINTS = {
    login: `${API_BASE_URL}/api/users/login`,
    register: `${API_BASE_URL}/api/users/register`,
    // ... more endpoints
};
```

### 2. Create API Helper Function
```javascript
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API Error');
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Usage:
const data = await apiCall(API_ENDPOINTS.login, {
    method: 'POST',
    body: JSON.stringify({email, password})
});
```

### 3. Always Check Response Type
```javascript
const response = await fetch(url);

// Log response type for debugging
console.log('Response type:', response.headers.get('content-type'));

// Only parse if JSON
if (response.headers.get('content-type')?.includes('json')) {
    const data = await response.json();
} else {
    const text = await response.text();
    console.error('Non-JSON response:', text);
}
```

## 🔧 Testing Your Fix

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Clear previous requests (🚫 icon)
4. Try the action (e.g., login)
5. Check the request:
   - Status should be **200**
   - Type should be **json** or **xhr**
   - Response should show JSON data

If all above are correct → Fixed! ✅

## 💡 Real-World Example

### Before (Broken):
```html
<script>
    // Direct relative path - WILL FAIL if opened as file://
    fetch('/api/users/login', {
        method: 'POST',
        body: JSON.stringify({email, password})
    })
    .then(res => res.json())  // ❌ Fails here if HTML response
    .then(data => console.log(data));
</script>
```

### After (Fixed):
```html
<script src="../js/config.js"></script>
<script>
    // Full URL with error handling
    fetch(API_ENDPOINTS.login, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password})
    })
    .then(async res => {
        if (!res.ok) {
            const text = await res.text();
            console.error('Response:', text);
            throw new Error(`HTTP ${res.status}`);
        }
        return res.json();  // ✅ Only parse if response OK
    })
    .then(data => {
        console.log('Success:', data);
        localStorage.setItem('token', data.access_token);
        window.location.href = 'dashboard.html';
    })
    .catch(error => {
        console.error('Error:', error);
        alert(`Login failed: ${error.message}`);
    });
</script>
```

## 🚀 Quick Fix for Your Project

You already have `config.js` created. To use it:

1. Add to HTML `<head>`:
   ```html
   <script src="../js/config.js"></script>
   ```

2. Replace fetch calls:
   ```javascript
   // Old:
   fetch('/api/users/login', ...)
   
   // New:
   fetch(API_ENDPOINTS.login, ...)
   ```

3. Access via backend URL:
   ```
   http://localhost:8000/frontend/templates/login.html
   ```

Done! 🎉
