// Dashboard functionality with live updates
let userData = null;
let ws = null;
let statsRefreshInterval = null;

// Initialize dashboard
async function initDashboard() {
    const currentUser = checkAuth();
    if (!currentUser) return;
    
    // Display welcome message
    displayWelcome(currentUser);
    
    // Load dashboard data
    await loadDashboardData();
    
    // Setup WebSocket for live updates
    setupWebSocket(currentUser.id);
    
    // Refresh stats periodically
    statsRefreshInterval = setInterval(loadDashboardData, 30000);
}

// Display welcome message
function displayWelcome(user) {
    const welcomeEl = document.getElementById('welcome-message');
    if (welcomeEl) {
        const hour = new Date().getHours();
        let greeting = 'Good morning';
        if (hour >= 12 && hour < 17) greeting = 'Good afternoon';
        else if (hour >= 17) greeting = 'Good evening';
        
        welcomeEl.textContent = `${greeting}, ${user.name}! 👋`;
    }
}

// Load dashboard data
async function loadDashboardData() {
    try {
        const token = localStorage.getItem('token');
        
        // Load user profile with stats - always fetch fresh from API
        const userResponse = await fetch(API_ENDPOINTS.me, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (userResponse.ok) {
            userData = await userResponse.json();
            
            // Update localStorage with fresh user data
            localStorage.setItem('user', JSON.stringify(userData));
            
            displayUserStats(userData);
        }
        
        // Load additional stats
        const statsResponse = await fetch(API_ENDPOINTS.userStats, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (statsResponse.ok) {
            const stats = await statsResponse.json();
            displayAdditionalStats(stats);
        }
        
        // Load online friends
        await loadOnlineFriends();
        
        // Load recent activity
        await loadRecentActivity();
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error loading dashboard data', 'error');
    }
}

// Display user stats
function displayUserStats(user) {
    // Update stat cards
    updateStatValue('ai-score', user.ai_score.toFixed(1));
    updateStatValue('total-calls', user.total_calls);
    updateStatValue('call-duration', formatDurationLong(user.total_call_duration || 0));
    updateStatValue('fluency-score', user.avg_fluency_score.toFixed(1) + '%');
    updateStatValue('rank', user.rank ? `#${user.rank}` : 'N/A');
    updateStatValue('weaknesses-count', user.weaknesses?.length || 0);
    
    // Update profile info
    const profileName = document.getElementById('profile-name');
    if (profileName) profileName.textContent = user.name;
    
    const profileEmail = document.getElementById('profile-email');
    if (profileEmail) profileEmail.textContent = user.email;
    
    const profileAvatar = document.getElementById('profile-avatar');
    if (profileAvatar) profileAvatar.src = getAvatarUrl(user);
    
    // Update online status
    const onlineStatus = document.getElementById('online-status');
    if (onlineStatus) {
        onlineStatus.innerHTML = user.is_online ? 
            '<span style="color: #38ef7d;">🟢 Online</span>' : 
            '<span style="color: #999;">⚫ Offline</span>';
    }
}

// Update stat value
function updateStatValue(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

// Display additional stats
function displayAdditionalStats(stats) {
    // Recent calls
    const recentCallsEl = document.getElementById('recent-calls');
    if (recentCallsEl && stats.recent_calls) {
        if (stats.recent_calls.length === 0) {
            recentCallsEl.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #999;">
                    <div style="font-size: 48px; margin-bottom: 15px;">📞</div>
                    <p>No calls yet</p>
                    <p style="font-size: 14px; margin-top: 10px;">Start practicing with partners!</p>
                    <button onclick="location.href='users.html'" style="margin-top: 20px; padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        Find Partners
                    </button>
                </div>
            `;
        } else {
            recentCallsEl.innerHTML = stats.recent_calls.slice(0, 5).map(call => `
                <div class="call-item">
                    <div class="call-info">
                        <div class="call-partner">${call.partner_name}</div>
                        <div class="call-date">${formatDate(call.created_at)}</div>
                    </div>
                    <div class="call-stats">
                        <div class="call-duration">${formatDuration(call.duration_seconds || 0)}</div>
                        ${call.ai_score ? `<div class="call-score">Score: ${call.ai_score.toFixed(1)}</div>` : ''}
                    </div>
                </div>
            `).join('');
        }
    }
    
    // Weaknesses
    const weaknessesEl = document.getElementById('weaknesses-list');
    if (weaknessesEl && stats.weaknesses) {
        if (stats.weaknesses.length === 0) {
            weaknessesEl.innerHTML = '<p style="color: #999; text-align: center;">No weaknesses identified yet</p>';
        } else {
            weaknessesEl.innerHTML = stats.weaknesses.map(weakness => `
                <div class="weakness-tag">${weakness}</div>
            `).join('');
        }
    }
    
    // Performance chart
    if (stats.performance_trend) {
        displayPerformanceChart(stats.performance_trend);
    }
}

// Display performance chart
function displayPerformanceChart(trend) {
    const chartEl = document.getElementById('performance-chart');
    if (!chartEl) return;
    
    if (!trend || trend.length === 0) {
        chartEl.innerHTML = '<p style="color: #999; text-align: center;">No performance data yet</p>';
        return;
    }
    
    const maxScore = Math.max(...trend.map(t => t.score), 100);
    
    chartEl.innerHTML = trend.map(item => {
        const height = (item.score / maxScore) * 100;
        return `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                <div style="font-size: 12px; color: #667eea; font-weight: 600;">${item.score.toFixed(0)}</div>
                <div style="width: 100%; background: #667eea; height: ${height}%; border-radius: 4px; min-height: 20px;"></div>
                <div style="font-size: 11px; color: #999;">${item.label}</div>
            </div>
        `;
    }).join('');
}

// Load online friends
async function loadOnlineFriends() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.friends, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const friends = await response.json();
            displayOnlineFriends(friends.filter(f => f.is_online));
        }
    } catch (error) {
        console.error('Error loading friends:', error);
    }
}

// Display online friends
function displayOnlineFriends(friends) {
    const container = document.getElementById('online-friends');
    if (!container) return;
    
    if (friends.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #999;">
                <p>No friends online</p>
                <button onclick="location.href='users.html'" style="margin-top: 10px; padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    Find Partners
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = friends.slice(0, 5).map(friend => `
        <div class="friend-item" style="display: flex; align-items: center; gap: 15px; padding: 15px; background: #f8f9fa; border-radius: 10px; margin-bottom: 10px;">
            <div style="width: 40px; height: 40px; border-radius: 50%; overflow: hidden;">
                <img src="${getAvatarUrl(friend)}" alt="${friend.name}" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #333;">${friend.name}</div>
                <div style="font-size: 12px; color: #38ef7d;">🟢 Online</div>
            </div>
            <button onclick="initiateCall('${friend.id}')" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                📞 Call
            </button>
        </div>
    `).join('');
}

// Load recent activity
async function loadRecentActivity() {
    // This can show recent friend requests, messages, etc.
    const activityEl = document.getElementById('recent-activity');
    if (!activityEl) return;
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.friendRequests, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const requests = await response.json();
            if (requests.length > 0) {
                activityEl.innerHTML = `
                    <div style="background: #fff3cd; padding: 15px; border-radius: 10px; border-left: 4px solid #ffc107;">
                        <strong>🔔 ${requests.length} new friend request${requests.length > 1 ? 's' : ''}!</strong>
                        <button onclick="location.href='users.html?tab=requests'" style="margin-left: 10px; padding: 6px 12px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                            View
                        </button>
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// Setup WebSocket for live updates
function setupWebSocket(userId) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        return;
    }
    
    if (!userId) {
        console.error('❌ No user ID for WebSocket');
        return;
    }
    
    try {
        console.log('🔌 Dashboard connecting to WebSocket for user:', userId);
        ws = new WebSocket(`${API_ENDPOINTS.ws}/${userId}`);
        
        ws.onopen = () => {
            console.log('✅ Dashboard WebSocket connected');
            console.log('📡 Ready to receive notifications');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('📨 *** DASHBOARD WEBSOCKET MESSAGE ***', data);
            handleWebSocketMessage(data);
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('⚠️ WebSocket closed, reconnecting...');
            setTimeout(() => setupWebSocket(userId), 5000);
        };
    } catch (error) {
        console.error('❌ Error setting up WebSocket:', error);
    }
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data);
    
    switch (data.type) {
        case 'user_online':
        case 'user_offline':
            // Refresh online friends when someone's status changes
            loadOnlineFriends();
            break;
        case 'friend_request':
            showToast('New friend request received!', 'success');
            loadRecentActivity();
            break;
        case 'friend_request_accepted':
            showToast('Friend request accepted!', 'success');
            loadOnlineFriends();
            break;
        case 'call_invitation':
        case 'call_invite':
            handleCallInvitation(data);
            break;
        default:
            // Refresh dashboard data for other updates
            loadDashboardData();
    }
}

// Handle call invitation
function handleCallInvitation(data) {
    console.log('📞 Incoming call from:', data.caller_name);
    
    const callerName = data.caller_name || 'Someone';
    const callId = data.call_id;
    
    // Show prominent notification
    showIncomingCallNotification(callerName, callId);
}

function showIncomingCallNotification(callerName, callId) {
    // Remove any existing call notification
    const existing = document.getElementById('incoming-call-notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification overlay
    const overlay = document.createElement('div');
    overlay.id = 'incoming-call-notification';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s;
    `;
    
    // Create notification content
    const notification = document.createElement('div');
    notification.style.cssText = `
        background: white;
        padding: 40px;
        border-radius: 20px;
        text-align: center;
        max-width: 400px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        animation: slideIn 0.3s;
    `;
    
    notification.innerHTML = `
        <div style="font-size: 80px; margin-bottom: 20px;">📞</div>
        <h2 style="margin: 0 0 10px 0; color: #667eea;">Incoming Call</h2>
        <p style="font-size: 20px; margin: 20px 0; font-weight: 600;">${callerName}</p>
        <p style="color: #666; margin-bottom: 30px;">wants to practice English with you</p>
        <div style="display: flex; gap: 15px; justify-content: center;">
            <button id="accept-call-btn" style="
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            ">
                ✓ Accept
            </button>
            <button id="reject-call-btn" style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            ">
                ✗ Decline
            </button>
        </div>
    `;
    
    overlay.appendChild(notification);
    document.body.appendChild(overlay);
    
    // Play notification sound
    try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGWS45+mjUAwPVqzn77BdGAk+ltryy3krBSl+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsI');
        audio.play().catch(e => console.log('Could not play sound'));
    } catch (e) {
        console.log('Audio not supported');
    }
    
    // Handle accept
    document.getElementById('accept-call-btn').onclick = () => {
        overlay.remove();
        window.location.href = `call.html?callId=${callId}`;
    };
    
    // Handle reject
    document.getElementById('reject-call-btn').onclick = () => {
        overlay.remove();
        showToast('Call declined', 'info');
    };
    
    // Auto-dismiss after 30 seconds
    setTimeout(() => {
        if (document.getElementById('incoming-call-notification')) {
            overlay.remove();
            showToast('Missed call from ' + callerName, 'info');
        }
    }, 30000);
}

// Initiate call to a user
async function initiateCall(userId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.inviteCall, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ partner_id: userId })
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Call initiated!', 'success');
            setTimeout(() => {
                window.location.href = `call.html?callId=${data.call_id}`;
            }, 1000);
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to initiate call', 'error');
        }
    } catch (error) {
        console.error('Error initiating call:', error);
        showToast('Network error', 'error');
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
    if (statsRefreshInterval) clearInterval(statsRefreshInterval);
});

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
