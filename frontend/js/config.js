// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// API Endpoints
const API_ENDPOINTS = {
    // User endpoints
    login: `${API_BASE_URL}/api/users/login`,
    register: `${API_BASE_URL}/api/users/register`,
    logout: `${API_BASE_URL}/api/users/logout`,
    me: `${API_BASE_URL}/api/users/me`,
    allUsers: `${API_BASE_URL}/api/users/all`,
    userProfile: `${API_BASE_URL}/api/users/profile`,
    userStats: `${API_BASE_URL}/api/users/stats`,
    friends: `${API_BASE_URL}/api/users/friends`,
    friendRequests: `${API_BASE_URL}/api/users/friend-requests`,
    findRandomPartner: `${API_BASE_URL}/api/users/find-random-partner`,
    
    // Call endpoints
    inviteCall: `${API_BASE_URL}/api/calls/invite`,
    endCall: `${API_BASE_URL}/api/calls/end`,
    
    // Leaderboard endpoints
    leaderboardTop: `${API_BASE_URL}/api/leaderboard/top`,
    
    // WebSocket
    ws: `ws://localhost:8000/ws`
};

// Helper function to make API calls with authentication
async function apiCall(url, options = {}) {
    const token = localStorage.getItem('token');
    
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
        
        // If unauthorized, redirect to login
        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/frontend/templates/login.html';
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('API call error:', error);
        throw error;
    }
}
