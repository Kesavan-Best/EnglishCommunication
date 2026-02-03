// js/auth.js
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../templates/login.html';
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
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '../index.html';
    }
}