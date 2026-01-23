// js/profile.js - Fixed version
const API_BASE_URL = 'http://localhost:8000'; // Update with your backend URL

// Initialize profile page
async function initProfilePage() {
    console.log('Initializing profile page...');
    
    // Show loading
    showLoading(true);
    
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '../templates/login.html';
            return;
        }
        
        // Check if viewing another user's profile
        const urlParams = new URLSearchParams(window.location.search);
        const userId = urlParams.get('userId');
        
        // Load user data
        await loadUserData(token, userId);
        
        // Load user stats
        await loadUserStats(token, userId);
        
        // Load recent activity
        await loadRecentActivity(token, userId);
        
        // Hide loading
        showLoading(false);
        
    } catch (error) {
        console.error('Error initializing profile:', error);
        showLoading(false);
        showToast('Failed to load profile data', 'error');
    }
}

// Load user data
async function loadUserData(token, userId) {
    try {
        // Use specific user endpoint if userId is provided, otherwise use /me for current user
        const endpoint = userId 
            ? `${API_BASE_URL}/api/users/${userId}`
            : `${API_BASE_URL}/api/users/me`;
        
        console.log('Loading user from:', endpoint);
            
        const response = await fetch(endpoint, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            console.log('Loaded user data:', userData);
            // Store current profile user data
            window.currentProfileUser = userData;
            updateProfileUI(userData);
        } else {
            console.error('Failed to load user data:', response.status);
            showToast('Failed to load user profile', 'error');
        }
    } catch (error) {
        console.error('Error loading user data:', error);
        showToast('Error loading profile', 'error');
    }
}

// Load user statistics
async function loadUserStats(token, userId) {
    try {
        // For now, stats endpoint only works for current user
        // Skip if viewing another user's profile
        if (userId) {
            updateStatsUI({});
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/api/users/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const stats = await response.json();
            updateStatsUI(stats);
        } else {
            console.error('Failed to load stats:', response.status);
            // Use default values
            updateStatsUI({});
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        updateStatsUI({});
    }
}

// Load recent activity
async function loadRecentActivity(token, userId) {
    try {
        // For now, recent calls endpoint only works for current user
        // Skip if viewing another user's profile
        if (userId) {
            const recentCallsEl = document.getElementById('recent-calls');
            const noActivityEl = document.getElementById('no-activity');
            if (recentCallsEl) recentCallsEl.style.display = 'none';
            if (noActivityEl) noActivityEl.style.display = 'block';
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/api/calls/recent`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const recentCallsEl = document.getElementById('recent-calls');
        const noActivityEl = document.getElementById('no-activity');
        
        if (response.ok) {
            const calls = await response.json();
            if (calls.length > 0) {
                displayRecentCalls(calls);
                if (recentCallsEl) recentCallsEl.style.display = 'block';
                if (noActivityEl) noActivityEl.style.display = 'none';
            } else {
                if (recentCallsEl) recentCallsEl.style.display = 'none';
                if (noActivityEl) noActivityEl.style.display = 'block';
            }
        } else {
            if (recentCallsEl) recentCallsEl.style.display = 'none';
            if (noActivityEl) noActivityEl.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// Update profile UI
function updateProfileUI(user) {
    // Update profile header
    document.getElementById('profile-name').textContent = user.name || 'User';
    document.getElementById('profile-email').textContent = user.email || '';
    
    // Update avatar
    const avatar = document.getElementById('profile-avatar');
    if (user.avatar_url) {
        avatar.src = user.avatar_url;
    } else {
        // Generate avatar with initials using full name for proper initials
        const name = user.name || 'User';
        avatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=667eea&color=fff&size=120`;
    }
    
    // Update online status
    const statusEl = document.getElementById('online-status');
    if (user.is_online) {
        statusEl.style.background = '#38ef7d';
        statusEl.title = 'Online';
    } else {
        statusEl.style.background = '#999';
        statusEl.title = 'Offline';
    }
    
    // Update member since
    if (user.created_at) {
        const date = new Date(user.created_at);
        document.getElementById('member-since').textContent = 
            `Member since ${date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}`;
    }
    
    // Update stats
    document.getElementById('ai-score').textContent = (user.ai_score || 0).toFixed(1);
    document.getElementById('global-rank').textContent = user.rank ? `#${user.rank}` : '#0';
    document.getElementById('total-calls').textContent = user.total_calls || 0;
    
    // Format practice time
    const totalMinutes = Math.floor((user.total_call_duration || 0) / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    document.getElementById('practice-time').textContent = `${hours}h ${minutes}m`;
    
    document.getElementById('avg-fluency').textContent = (user.avg_fluency_score || 0).toFixed(1) + '%';
    
    // Calculate accuracy (placeholder - you can adjust this)
    const accuracy = user.ai_score ? Math.min(100, user.ai_score * 10) : 0;
    document.getElementById('accuracy').textContent = accuracy.toFixed(1) + '%';
    
    // Update weaknesses
    updateWeaknessesUI(user.weaknesses || []);
}

// Update statistics UI
function updateStatsUI(stats) {
    // Update progress bars
    const analysisStats = stats.analysis_stats || {};
    
    const grammarPercent = Math.min(100, 100 - (analysisStats.avg_grammar_errors || 0) * 5);
    const fluencyPercent = analysisStats.avg_fluency || 0;
    const vocabPercent = Math.min(100, 100 - (analysisStats.vocabulary_repetition || 0) * 100);
    const pronunciationPercent = analysisStats.pronunciation_score || 75; // Default
    
    // Animate progress bars
    setTimeout(() => {
        animateProgressBar('grammar-progress', grammarPercent);
        animateProgressBar('fluency-progress', fluencyPercent);
        animateProgressBar('vocab-progress', vocabPercent);
        animateProgressBar('pronunciation-progress', pronunciationPercent);
    }, 500);
    
    // Update percentages
    document.getElementById('grammar-percent').textContent = grammarPercent.toFixed(0) + '%';
    document.getElementById('fluency-percent').textContent = fluencyPercent.toFixed(1) + '%';
    document.getElementById('vocab-percent').textContent = vocabPercent.toFixed(0) + '%';
    document.getElementById('pronunciation-percent').textContent = pronunciationPercent.toFixed(0) + '%';
    
    // Update performance chart
    updatePerformanceChart(stats.improvement_timeline);
}

// Update weaknesses UI
function updateWeaknessesUI(weaknesses) {
    const weaknessesList = document.getElementById('weaknesses-list');
    const noWeaknessesEl = document.getElementById('no-weaknesses');
    
    if (weaknesses.length === 0) {
        weaknessesList.innerHTML = '';
        weaknessesList.style.display = 'none';
        noWeaknessesEl.style.display = 'block';
        return;
    }
    
    noWeaknessesEl.style.display = 'none';
    weaknessesList.style.display = 'flex';
    
    // Clear and update weaknesses
    weaknessesList.innerHTML = weaknesses.map(weakness => `
        <div class="weakness-tag">
            <i class="fas fa-exclamation-circle"></i>
            ${weakness.toUpperCase()}
        </div>
    `).join('');
}

// Update performance chart
function updatePerformanceChart(timelineData) {
    const chartContainer = document.getElementById('performance-chart');
    const noDataEl = document.getElementById('no-performance-data');
    
    if (!timelineData || timelineData.length === 0) {
        chartContainer.innerHTML = '';
        chartContainer.style.display = 'none';
        noDataEl.style.display = 'block';
        return;
    }
    
    noDataEl.style.display = 'none';
    chartContainer.style.display = 'flex';
    
    // Get max score for scaling
    const maxScore = Math.max(...timelineData.map(item => item.avg_score || 0), 100);
    
    // Generate chart bars
    chartContainer.innerHTML = timelineData.map(item => {
        const score = item.avg_score || 0;
        const height = (score / maxScore) * 100;
        const label = item._id || 'Month';
        
        return `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                <div class="chart-bar" style="height: ${height}%">
                    <span class="chart-value">${score.toFixed(0)}</span>
                </div>
                <div class="chart-label">${label}</div>
            </div>
        `;
    }).join('');
}

// Display recent calls
function displayRecentCalls(calls) {
    const container = document.getElementById('recent-calls');
    
    container.innerHTML = calls.slice(0, 5).map(call => `
        <div class="activity-item">
            <div class="activity-icon">
                <i class="fas fa-phone-alt"></i>
            </div>
            <div class="activity-details">
                <div class="activity-title">Call with ${call.partner_name || 'Partner'}</div>
                <div class="activity-time">${formatDate(call.created_at)} • ${formatDuration(call.duration_seconds || 0)}</div>
            </div>
            <div class="activity-score">${call.score ? call.score.toFixed(1) : 'N/A'}</div>
        </div>
    `).join('');
}

// Helper functions
function animateProgressBar(elementId, targetWidth) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.width = targetWidth + '%';
    }
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function formatDuration(seconds) {
    if (!seconds) return '0m';
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `${minutes}m`;
    } else {
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        return `${hours}h ${remainingMinutes}m`;
    }
}

function showLoading(show) {
    const loadingEl = document.getElementById('loading');
    const contentEl = document.querySelector('.profile-container');
    
    if (loadingEl) {
        loadingEl.style.display = show ? 'block' : 'none';
    }
    
    if (contentEl) {
        contentEl.style.display = show ? 'none' : 'block';
    }
}

function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // Add styles
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 10px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProfilePage);
} else {
    initProfilePage();
}