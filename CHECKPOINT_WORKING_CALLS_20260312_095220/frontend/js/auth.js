// js/auth.js
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/frontend/templates/login.html';
        return null;
    }
    
    // Return user object from localStorage
    const userStr = localStorage.getItem('user');
    if (userStr) {
        try {
            return JSON.parse(userStr);
        } catch (e) {
            console.error('Error parsing user data:', e);
            return null;
        }
    }
    return null;
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        // Call backend logout API to update online status
        const token = localStorage.getItem('token');
        if (token) {
            fetch(API_ENDPOINTS.logout, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }).catch(err => console.error('Logout API error:', err));
        }
        
        // Clear local storage and redirect
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/frontend/index.html';
    }
}