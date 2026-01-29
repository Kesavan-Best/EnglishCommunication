// config.js - API Configuration (Updated for Consistency)

// Auto-detect environment
const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE_URL = isProduction 
    ? 'https://english-communication-backend.onrender.com' 
    : 'http://localhost:8000';

const WS_BASE_URL = isProduction
    ? 'wss://english-communication-backend.onrender.com'
    : 'ws://localhost:8000';

const API_ENDPOINTS = {
    // User endpoints
    login: `${API_BASE_URL}/api/users/login`,
    register: `${API_BASE_URL}/api/users/register`,
    logout: `${API_BASE_URL}/api/users/logout`,
    me: `${API_BASE_URL}/api/users/me`,
    allUsers: `${API_BASE_URL}/api/users/all`,
    userStats: `${API_BASE_URL}/api/users/stats`,
    friends: `${API_BASE_URL}/api/users/friends`,
    friendRequests: `${API_BASE_URL}/api/users/friend-requests`,
    findRandomPartner: `${API_BASE_URL}/api/users/find-random-partner`,
    userProfile: (userId) => `${API_BASE_URL}/api/users/${userId}`,
    updateProfile: `${API_BASE_URL}/api/users/profile`,
    
    // Call endpoints
    inviteCall: `${API_BASE_URL}/api/calls/invite`,
    endCall: `${API_BASE_URL}/api/calls/end`,
    
    // Leaderboard endpoints
    leaderboard: `${API_BASE_URL}/api/leaderboard/top`,
    leaderboardTop: `${API_BASE_URL}/api/leaderboard/top`,
    
    // WebSocket
    ws: `${WS_BASE_URL}/ws`
};

// Auth checker for protected routes
function checkAuth() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (!token || !user.email) {
        // If we're not on login/register page, redirect to login
        if (!window.location.pathname.includes('login.html') && 
            !window.location.pathname.includes('register.html') &&
            !window.location.pathname.includes('index.html')) {
            window.location.href = '/frontend/templates/login.html';
            return false;
        }
    }
    
    return { token, user };
}

// Make authenticated API calls
async function apiCall(url, options = {}) {
    const { token } = checkAuth() || {};
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...options,
        headers
    };
    
    try {
        const response = await fetch(url, config);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            
            if (!window.location.pathname.includes('login.html')) {
                window.location.href = '/frontend/templates/login.html';
            }
            
            throw new Error('Session expired. Please login again.');
        }
        
        // Handle other errors
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API error: ${response.status}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('API call error:', error);
        
        // Show user-friendly error message
        if (error.message.includes('Failed to fetch')) {
            throw new Error('Cannot connect to server. Please check your connection and ensure the backend is running (python main.py).');
        }
        
        throw error;
    }
}

// Upload file with progress
async function uploadFile(url, file, onProgress = null) {
    const formData = new FormData();
    formData.append('file', file);
    
    const { token } = checkAuth() || {};
    
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.open('POST', url);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        
        xhr.upload.onprogress = (event) => {
            if (onProgress && event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                onProgress(percentComplete);
            }
        };
        
        xhr.onload = () => {
            if (xhr.status === 200) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(`Upload failed: ${xhr.statusText}`));
            }
        };
        
        xhr.onerror = () => reject(new Error('Network error during upload'));
        
        xhr.send(formData);
    });
}

// Initialize WebSocket connection
function initWebSocket(onMessage, onOpen, onClose) {
    const { token } = checkAuth() || {};
    
    if (!token) {
        console.error('No authentication token for WebSocket');
        return null;
    }
    
    const wsUrl = `${API_ENDPOINTS.ws}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = onOpen || (() => console.log('WebSocket connected'));
    ws.onclose = onClose || (() => console.log('WebSocket disconnected'));
    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (onMessage) onMessage(data);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    };
    
    return ws;
}

// Export for use in other files
window.API_ENDPOINTS = API_ENDPOINTS;
window.apiCall = apiCall;
window.checkAuth = checkAuth;
window.uploadFile = uploadFile;
window.initWebSocket = initWebSocket;