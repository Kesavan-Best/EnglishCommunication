// Users page functionality
let allUsers = [];
let friends = [];
let currentUser = null;
let ws = null;
let heartbeatInterval = null;
let pendingCallsInterval = null;

// Initialize page
async function initUsersPage() {
    currentUser = JSON.parse(localStorage.getItem('user'));
    const token = localStorage.getItem('token');
    
    if (!token) {
        window.location.href = 'login.html';
        return;
    }
    
    // Check for active call (user might have navigated away)
    checkForActiveCall();
    
    // Setup tabs
    setupTabs();
    
    // Load initial data
    await Promise.all([
        loadAllUsers(),
        loadFriends(),
        loadPendingRequests()
    ]);
    
    // Setup WebSocket for live updates
    setupWebSocket();
    
    // Setup search
    setupSearch();
    
    // Start polling for pending call invites (cross-instance support)
    startPendingCallsPolling();
    
    // Refresh data every 10 seconds
    setInterval(() => {
        loadAllUsers();
        loadFriends();
        loadPendingRequests();
    }, 10000);
}

// Poll for pending call invites (works across server instances)
function startPendingCallsPolling() {
    // Check immediately
    checkPendingCallInvites();
    
    // Then poll every 2 seconds
    pendingCallsInterval = setInterval(checkPendingCallInvites, 2000);
}

async function checkPendingCallInvites() {
    try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const response = await fetch(`${API_BASE_URL}/api/calls/pending-invites`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.invites && data.invites.length > 0) {
                // Show the first pending invite
                const invite = data.invites[0];
                
                // Check if we're not already showing this notification
                if (!document.getElementById('incoming-call-notification')) {
                    console.log('📞 Found pending call invite via polling:', invite);
                    showIncomingCallNotification(invite.caller_name, invite.call_id, invite.caller_id);
                    
                    // Mark as seen so we don't show it again
                    await fetch(`${API_BASE_URL}/api/calls/mark-invite-seen?call_id=${invite.call_id}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                }
            }
        }
    } catch (error) {
        // Silently fail - polling will retry
        console.debug('Polling check failed:', error.message);
    }
}

// Check if user has an active call and show return banner
function checkForActiveCall() {
    const activeCallId = sessionStorage.getItem('activeCallId');
    const timestamp = parseInt(sessionStorage.getItem('activeCallTimestamp') || '0');
    const timeSince = Date.now() - timestamp;
    
    // If call was started less than 10 minutes ago, show return banner
    if (activeCallId && timeSince < 600000) {
        showActiveCallBanner(activeCallId);
    }
}

// Show banner to return to active call
function showActiveCallBanner(callId) {
    // Remove existing banner if any
    const existingBanner = document.getElementById('active-call-banner');
    if (existingBanner) existingBanner.remove();
    
    const banner = document.createElement('div');
    banner.id = 'active-call-banner';
    banner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 9999;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        animation: slideDown 0.3s ease-out;
    `;
    
    banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="font-size: 24px; animation: pulse 1.5s infinite;">📞</div>
            <div>
                <strong>You have an active call!</strong>
                <span style="opacity: 0.9; margin-left: 10px;">Click to return to your call</span>
            </div>
        </div>
        <div style="display: flex; gap: 10px;">
            <button onclick="returnToActiveCall('${callId}')" style="
                background: white;
                color: #667eea;
                border: none;
                padding: 10px 25px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            ">Return to Call</button>
            <button onclick="dismissActiveCallBanner()" style="
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 8px;
                cursor: pointer;
            ">✕</button>
        </div>
    `;
    
    // Add animation style
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideDown {
            from { transform: translateY(-100%); }
            to { transform: translateY(0); }
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
    `;
    document.head.appendChild(style);
    
    document.body.prepend(banner);
    
    // Adjust page content to not be hidden under banner
    document.body.style.paddingTop = '70px';
}

// Return to active call
function returnToActiveCall(callId) {
    window.location.href = `call.html?callId=${callId}&autoStart=true`;
}

// Dismiss active call banner (also clears session storage)
function dismissActiveCallBanner() {
    sessionStorage.removeItem('activeCallId');
    sessionStorage.removeItem('activeCallTimestamp');
    
    const banner = document.getElementById('active-call-banner');
    if (banner) {
        banner.style.animation = 'slideUp 0.3s ease-out forwards';
        setTimeout(() => {
            banner.remove();
            document.body.style.paddingTop = '0';
        }, 300);
    }
    
    // Add slideUp animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideUp {
            from { transform: translateY(0); }
            to { transform: translateY(-100%); }
        }
    `;
    document.head.appendChild(style);
}

function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
    
    // Load data for the active tab
    if (tabName === 'all') {
        loadAllUsers();
    } else if (tabName === 'friends') {
        loadFriends();
    } else if (tabName === 'random') {
        loadRandomPartner();
    }
}

async function loadAllUsers() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'login.html';
            return;
        }
        
        const response = await fetch(API_ENDPOINTS.allUsers, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            allUsers = await response.json();
            console.log('Loaded users:', allUsers);
            // Filter out current user
            if (currentUser) {
                allUsers = allUsers.filter(u => u.id !== currentUser.id);
            }
            displayUsers(allUsers, 'all-users-grid');
        } else {
            console.error('Failed to load users, status:', response.status);
            const container = document.getElementById('all-users-grid');
            if (container) {
                container.innerHTML = '<div style="text-align: center; padding: 40px;"><p>Failed to load users</p><button onclick="loadAllUsers()" class="btn">Retry</button></div>';
            }
        }
    } catch (error) {
        console.error('Error loading users:', error);
        const container = document.getElementById('all-users-grid');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 40px;"><p>Network error</p><button onclick="loadAllUsers()" class="btn">Retry</button></div>';
        }
    }
}

async function loadFriends() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.friends, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            friends = await response.json();
            // Filter out current user from friends list
            if (currentUser) {
                friends = friends.filter(f => f.id !== currentUser.id);
            }
            displayUsers(friends, 'friends-grid');
        }
    } catch (error) {
        console.error('Error loading friends:', error);
    }
}

async function loadPendingRequests() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.friendRequests, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const requests = await response.json();
            displayFriendRequests(requests);
        }
    } catch (error) {
        console.error('Error loading friend requests:', error);
    }
}

function displayFriendRequests(requests) {
    const container = document.getElementById('requests-container');
    const countBadge = document.getElementById('request-count');
    
    if (!container) return;
    
    // Update count badge
    if (countBadge) {
        if (requests.length > 0) {
            countBadge.textContent = requests.length;
            countBadge.style.display = 'inline';
        } else {
            countBadge.style.display = 'none';
        }
    }
    
    if (requests.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; background: white; border-radius: 15px;">
                <div style="font-size: 80px; margin-bottom: 20px;">📭</div>
                <h3 style="color: #333; margin-bottom: 10px;">No Friend Requests</h3>
                <p style="color: #666;">You don't have any pending friend requests at the moment.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div style="display: grid; gap: 15px;">
            ${requests.map(req => `
                <div style="background: white; padding: 20px; border-radius: 15px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 3px 20px rgba(0,0,0,0.08);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="${req.from_user.avatar_url || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(req.from_user.name) + '&background=667eea&color=fff&size=100'}" 
                             style="width: 60px; height: 60px; border-radius: 50%; border: 3px solid #667eea; object-fit: cover;">
                        <div>
                            <strong style="display: block; font-size: 18px; color: #333; margin-bottom: 5px;">${req.from_user.name}</strong>
                            <small style="color: #666; display: block;">${req.from_user.email}</small>
                            <small style="color: #999; display: block; margin-top: 5px;">⏱️ ${formatDate(req.created_at)}</small>
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="acceptFriendRequest('${req.request_id}')" 
                                style="padding: 10px 20px; background: linear-gradient(135deg, #38ef7d 0%, #11998e 100%); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                            ✓ Accept
                        </button>
                        <button onclick="rejectFriendRequest('${req.request_id}')" 
                                style="padding: 10px 20px; background: #f5f5f5; color: #666; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                            ✗ Reject
                        </button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function acceptFriendRequest(requestId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/users/friend-request/${requestId}/accept`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            showMessage('✅ Friend request accepted!', 'success');
            // Reload data
            loadPendingRequests();
            loadFriends();
        } else {
            showMessage('❌ Failed to accept request', 'error');
        }
    } catch (error) {
        console.error('Error accepting request:', error);
        showMessage('❌ Network error', 'error');
    }
}

async function rejectFriendRequest(requestId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/users/friend-request/${requestId}/reject`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            showMessage('Request rejected', 'info');
            loadPendingRequests();
        } else {
            showMessage('❌ Failed to reject request', 'error');
        }
    } catch (error) {
        console.error('Error rejecting request:', error);
        showMessage('❌ Network error', 'error');
    }
}

// Track if user is currently searching for random match
let isSearchingRandom = false;

async function loadRandomPartner() {
    const btn = document.getElementById('find-random-btn');
    const statusDiv = document.getElementById('random-status');
    
    // If already searching, cancel
    if (isSearchingRandom) {
        cancelRandomSearch();
        return;
    }
    
    // Check if WebSocket is connected
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn('⚠️ WebSocket not connected, reconnecting...');
        setupWebSocket();
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    isSearchingRandom = true;
    btn.disabled = false;
    btn.textContent = '❌ Cancel Search';
    btn.style.background = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
    
    statusDiv.innerHTML = `
        <div style="text-align: center; padding: 30px;">
            <div style="font-size: 50px; margin-bottom: 20px; animation: pulse 1.5s infinite;">🔍</div>
            <p style="font-size: 18px; color: #667eea; font-weight: 600;">Searching for a partner...</p>
            <p style="color: #666; margin-top: 10px;">When someone else clicks "Find Random Partner", you'll be matched!</p>
            <div style="margin-top: 20px; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 10px;">
                <p style="color: #667eea; font-size: 14px;">⏳ Waiting in queue...</p>
            </div>
        </div>
        <style>
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
        </style>
    `;
    
    // Send join queue message via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'join_random_queue',
            user_name: currentUser?.name || 'Anonymous'
        }));
        console.log('🎲 Joined random matching queue');
    }
}

function cancelRandomSearch() {
    const btn = document.getElementById('find-random-btn');
    const statusDiv = document.getElementById('random-status');
    
    isSearchingRandom = false;
    btn.textContent = '🔀 Find Random Partner';
    btn.style.background = '';
    statusDiv.innerHTML = '';
    
    // Send leave queue message via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'leave_random_queue'
        }));
        console.log('🎲 Left random matching queue');
    }
}

// Handle random match found (called from WebSocket message handler)
function handleRandomMatchFound(data) {
    console.log('🎲 Random match found!', data);
    
    const btn = document.getElementById('find-random-btn');
    const statusDiv = document.getElementById('random-status');
    
    isSearchingRandom = false;
    btn.textContent = '🔀 Find Random Partner';
    btn.style.background = '';
    
    statusDiv.innerHTML = `
        <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, rgba(17, 153, 142, 0.1) 0%, rgba(56, 239, 125, 0.1) 100%); border-radius: 15px;">
            <div style="font-size: 60px; margin-bottom: 20px;">🎉</div>
            <h3 style="color: #11998e; margin-bottom: 10px;">Match Found!</h3>
            <p style="font-size: 18px; color: #333; font-weight: 600;">${data.partner_name}</p>
            <p style="color: #666; margin: 15px 0;">Connecting you now...</p>
        </div>
    `;
    
    // Auto-redirect to call page
    setTimeout(() => {
        window.location.href = `call.html?callId=${data.call_id}&autoStart=true`;
    }, 1500);
}

function displayUsers(users, containerId) {
    const container = document.getElementById(containerId);
    
    if (!container) return;
    
    if (users.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px;">
                <div style="font-size: 64px; margin-bottom: 20px;">😔</div>
                <h3 style="color: #666;">No users found</h3>
                <p style="color: #999;">Check back later</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = users.map(user => createUserCard(user, containerId === 'friends-grid')).join('');
    
    // Add event listeners
    attachUserCardListeners();
}

function createUserCard(user, isFriend) {
    const onlineClass = user.is_online ? 'online-status' : 'offline-status';
    const onlineText = user.is_online ? 'Online' : 'Offline';
    
    // Check if user is already a friend
    const isAlreadyFriend = isFriend || friends.some(f => f.id === user.id);
    
    const callBtn = user.is_online ? 
        `<button class="btn-action btn-call" onclick="initiateCall('${user.id}')" title="Start Call">
            📞 Call
        </button>` :
        `<button class="btn-action btn-disabled" disabled title="User is offline">
            📞 Offline
        </button>`;
    
    const friendBtn = isAlreadyFriend ? 
        `<button class="btn-action btn-disabled" disabled title="Already Friends">
            ✅ Friends
        </button>` :
        `<button class="btn-action btn-add-friend" onclick="sendFriendRequest('${user.id}')" title="Send Friend Request">
            ➕ Add Friend
        </button>`;
    
    // Get user initials for avatar
    const getInitials = (name) => {
        if (!name) return '?';
        const parts = name.trim().split(' ');
        if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
        return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    };
    
    const initials = getInitials(user.name);
    
    return `
        <div class="user-card" data-user-id="${user.id}">
            <div class="${onlineClass}">${onlineText}</div>
            <div class="user-avatar" title="${user.name}">
                ${user.avatar_url ? 
                    `<img src="${user.avatar_url}" alt="${user.name}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">` :
                    `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 700;">${initials}</div>`
                }
            </div>
            <div class="user-info">
                <h3 class="user-name" title="${user.name}">${user.name}</h3>
                <p class="user-email" title="${user.email}">${user.email}</p>
            </div>
            <div class="user-stats-mini">
                <div class="stat-mini">
                    <span class="stat-label">AI Score</span>
                    <span class="stat-value">${user.ai_score.toFixed(1)}</span>
                </div>
                <div class="stat-mini">
                    <span class="stat-label">Calls</span>
                    <span class="stat-value">${user.total_calls}</span>
                </div>
            </div>
            <div class="user-actions">
                ${callBtn}
                ${friendBtn}
                <button class="btn-action btn-profile" onclick="viewProfile('${user.id}')" title="View Profile">
                    👤 Profile
                </button>
            </div>
        </div>
    `;
}

function displayRandomPartner(partner) {
    const statusDiv = document.getElementById('random-status');
    statusDiv.innerHTML = `
        <div class="random-partner-card">
            <div class="partner-found">
                <h3>✨ Partner Found!</h3>
                ${createUserCard(partner, false)}
            </div>
        </div>
    `;
    attachUserCardListeners();
}

async function sendFriendRequest(userId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/users/friend-request/${userId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            showMessage('✅ Friend request sent!', 'success');
            // Update button state
            const card = document.querySelector(`[data-user-id="${userId}"]`);
            if (card) {
                const btn = card.querySelector('.btn-add-friend');
                if (btn) {
                    btn.textContent = '⏳ Pending';
                    btn.disabled = true;
                    btn.classList.add('btn-disabled');
                }
            }
        } else {
            const error = await response.json();
            showMessage(`❌ ${error.detail || 'Failed to send friend request'}`, 'error');
        }
    } catch (error) {
        console.error('Error sending friend request:', error);
        showMessage('❌ Network error', 'error');
    }
}

async function initiateCall(userId) {
    try {
        console.log('🔵 Initiating call to user:', userId);
        
        // Ensure WebSocket is connected
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket not connected, reconnecting...');
            setupWebSocket();
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // Disable button to prevent double-clicks
        const callButtons = document.querySelectorAll(`[onclick="initiateCall('${userId}')"]`);
        callButtons.forEach(btn => {
            btn.disabled = true;
            btn.textContent = '⏳ Connecting...';
        });
        
        showMessage('📞 Creating call...', 'info');
        
        const token = localStorage.getItem('token');
        console.log('🔵 Token exists:', !!token);
        console.log('🔵 API Endpoint:', API_ENDPOINTS.inviteCall);
        console.log('🔵 Request payload:', { receiver_id: userId });
        
        const response = await fetch(API_ENDPOINTS.inviteCall, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ receiver_id: userId })
        });
        
        console.log('🔵 Response status:', response.status);
        console.log('🔵 Response ok:', response.ok);
        
        if (response.ok) {
            const call = await response.json();
            console.log('✅ Call created:', call);
            console.log('✅ Call ID:', call.id);
            
            // Validate call response
            if (!call.id || !call.jitsi_room_id) {
                throw new Error('Invalid call response from server');
            }
            
            showMessage('✅ Call invitation sent! Waiting for response...', 'success');
            
            // Store pending call ID for handling responses
            window.pendingCallId = call.id;
            window.pendingCallRoomId = call.jitsi_room_id;
            
            // Show a waiting UI
            const waitingDiv = document.createElement('div');
            waitingDiv.id = 'call-waiting';
            waitingDiv.dataset.callId = call.id;
            waitingDiv.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            `;
            waitingDiv.innerHTML = `
                <div style="background: white; padding: 40px; border-radius: 20px; text-align: center; max-width: 400px;">
                    <div style="font-size: 60px; margin-bottom: 20px;">📞</div>
                    <h2 style="color: #667eea; margin-bottom: 15px;">Calling...</h2>
                    <p style="color: #666; margin-bottom: 10px;">Waiting for the other person to answer</p>
                    <p style="color: #999; font-size: 14px; margin-bottom: 20px;">They will see your call invitation</p>
                    <div id="call-waiting-timer" style="color: #667eea; font-weight: bold; margin-bottom: 20px;">30</div>
                    <button onclick="cancelPendingCall('${call.id}')" 
                            style="background: #f5576c; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 16px;">
                        Cancel Call
                    </button>
                </div>
            `;
            document.body.appendChild(waitingDiv);
            
            // Start countdown timer (30 seconds) AND poll for acceptance
            let countdown = 30;
            window.callWaitingInterval = setInterval(async () => {
                countdown--;
                const timerEl = document.getElementById('call-waiting-timer');
                if (timerEl) {
                    timerEl.textContent = countdown;
                }
                
                // Poll call status every 2 seconds (for cross-instance support)
                if (countdown % 2 === 0) {
                    try {
                        const statusResponse = await fetch(`${API_BASE_URL}/api/calls/check-status/${call.id}`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                        });
                        if (statusResponse.ok) {
                            const statusData = await statusResponse.json();
                            if (statusData.status === 'active') {
                                // Call was accepted! Redirect to call page
                                console.log('✅ Call accepted (via polling)!');
                                clearInterval(window.callWaitingInterval);
                                handleCallAccepted(call.id);
                                return;
                            }
                        }
                    } catch (e) {
                        console.debug('Status check failed:', e.message);
                    }
                }
                
                if (countdown <= 0) {
                    // Auto-cancel after timeout
                    clearInterval(window.callWaitingInterval);
                    cancelPendingCall(call.id, true);
                }
            }, 1000);
            
        } else {
            const error = await response.json();
            console.error('❌ API Error:', error);
            
            // Re-enable button
            callButtons.forEach(btn => {
                btn.disabled = false;
                btn.textContent = '📞 Call';
            });
            
            showMessage(`❌ ${error.detail || 'Failed to start call'}`, 'error');
        }
    } catch (error) {
        console.error('❌ Network Error:', error);
        console.error('❌ Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        
        // Re-enable button
        const callButtons = document.querySelectorAll(`[onclick="initiateCall('${userId}')"]`);
        callButtons.forEach(btn => {
            btn.disabled = false;
            btn.textContent = '📞 Call';
        });
        
        showMessage(`❌ Network error: ${error.message}`, 'error');
    }
}

// Cancel a pending call
function cancelPendingCall(callId, isTimeout = false) {
    console.log('🔴 Cancelling pending call:', callId, isTimeout ? '(timeout)' : '(user cancelled)');
    
    // Clear interval
    if (window.callWaitingInterval) {
        clearInterval(window.callWaitingInterval);
        window.callWaitingInterval = null;
    }
    
    // Remove waiting overlay
    const waitingDiv = document.getElementById('call-waiting');
    if (waitingDiv) {
        waitingDiv.remove();
    }
    
    // Clear pending call
    window.pendingCallId = null;
    window.pendingCallRoomId = null;
    
    // Re-enable all call buttons
    document.querySelectorAll('.btn-call').forEach(btn => {
        btn.disabled = false;
        btn.textContent = '📞 Call';
    });
    
    // Show appropriate message
    if (isTimeout) {
        showMessage('📞 Call timed out - no answer', 'info');
    } else {
        showMessage('📞 Call cancelled', 'info');
    }
}

// Handle call being accepted by receiver
function handleCallAccepted(callId) {
    console.log('✅ Call accepted! Redirecting to call page...');
    
    // Clear waiting interval
    if (window.callWaitingInterval) {
        clearInterval(window.callWaitingInterval);
        window.callWaitingInterval = null;
    }
    
    // Remove waiting overlay
    const waitingDiv = document.getElementById('call-waiting');
    if (waitingDiv) {
        waitingDiv.remove();
    }
    
    // Clear pending call state
    window.pendingCallId = null;
    window.pendingCallRoomId = null;
    
    // Redirect to WebRTC call page
    showMessage('✅ Call accepted! Connecting...', 'success');
    setTimeout(() => {
        window.location.href = `call.html?callId=${callId}`;
    }, 500);
}

// Handle call being rejected by receiver
function handleCallRejected(rejectorName) {
    console.log('❌ Call rejected by:', rejectorName);
    
    // Clear waiting interval
    if (window.callWaitingInterval) {
        clearInterval(window.callWaitingInterval);
        window.callWaitingInterval = null;
    }
    
    // Remove waiting overlay
    const waitingDiv = document.getElementById('call-waiting');
    if (waitingDiv) {
        waitingDiv.remove();
    }
    
    // Clear pending call
    window.pendingCallId = null;
    window.pendingCallRoomId = null;
    
    // Re-enable all call buttons
    document.querySelectorAll('.btn-call').forEach(btn => {
        btn.disabled = false;
        btn.textContent = '📞 Call';
    });
    
    // Show a prominent rejection notification overlay
    showCallRejectedOverlay(rejectorName);
}

// Show call rejected overlay with clear message
function showCallRejectedOverlay(rejecterName) {
    const overlay = document.createElement('div');
    overlay.id = 'call-rejected-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10001;
        animation: fadeIn 0.3s;
    `;
    
    overlay.innerHTML = `
        <div style="background: white; padding: 40px 50px; border-radius: 20px; text-align: center; max-width: 400px; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
            <div style="font-size: 80px; margin-bottom: 20px;">❌</div>
            <h2 style="color: #ef4444; margin-bottom: 15px; font-size: 24px;">Call Declined</h2>
            <p style="color: #666; margin-bottom: 10px; font-size: 18px;">
                <strong>${rejecterName || 'The user'}</strong> declined your call.
            </p>
            <p style="color: #999; margin-bottom: 30px; font-size: 14px;">They may be busy right now. Try again later!</p>
            <button onclick="document.getElementById('call-rejected-overlay').remove()" 
                    style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 14px 40px; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: 600; transition: all 0.3s;">
                OK, Got it
            </button>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        const el = document.getElementById('call-rejected-overlay');
        if (el) el.remove();
    }, 8000);
}

function viewProfile(userId) {
    window.location.href = `/frontend/templates/profile.html?userId=${userId}`;
}

function setupSearch() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            filterUsers(query);
        });
    }
}

function filterUsers(query) {
    const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
    const users = activeTab === 'friends' ? friends : allUsers;
    
    const filtered = users.filter(user => 
        user.name.toLowerCase().includes(query) || 
        user.email.toLowerCase().includes(query)
    );
    
    const containerId = activeTab === 'friends' ? 'friends-grid' : 'all-users-grid';
    displayUsers(filtered, containerId);
}

function setupWebSocket() {
    const token = localStorage.getItem('token');
    const userId = currentUser ? currentUser.id : null;
    
    if (!userId) {
        console.error('❌ No user ID for WebSocket connection');
        return;
    }
    
    // Close existing connection if any
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
    
    // Clear existing heartbeat interval
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
    
    // Use dynamic WebSocket URL from config (handles localhost vs production)
    const wsUrl = `${API_ENDPOINTS.ws}/${userId}`;
    console.log('🔌 Connecting to WebSocket:', wsUrl);
    console.log('👤 User ID:', userId);
    console.log('👤 User Name:', currentUser.name);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('✅ WebSocket connected successfully');
        console.log('📡 Ready to receive call notifications');
        
        // Start heartbeat to keep online status updated across environments
        // Sends ping every 2 minutes to update last_seen in database
        heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
                console.log('💓 Heartbeat sent');
            }
        }, 120000); // Every 2 minutes
        
        // Send initial ping immediately
        ws.send(JSON.stringify({ type: 'ping' }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('📨 *** INCOMING WEBSOCKET MESSAGE ***', data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('⚠️ WebSocket closed, reconnecting in 5s...');
        // Clear heartbeat interval on close
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
        setTimeout(setupWebSocket, 5000);
    };
}

function handleWebSocketMessage(data) {
    console.log('📨 ==========================================');
    console.log('📨 WebSocket message received:', data);
    console.log('📨 Message type:', data.type);
    console.log('📨 ==========================================');
    
    if (data.type === 'welcome') {
        console.log('✅ Welcome message received - WebSocket is working!');
    } else if (data.type === 'user_online') {
        console.log(`✅ User ${data.user_id} is now ONLINE`);
        updateUserStatus(data.user_id, true);
        // Reload user lists to reflect online status
        loadAllUsers();
        loadFriends();
    } else if (data.type === 'user_offline') {
        console.log(`⚫ User ${data.user_id} is now OFFLINE`);
        updateUserStatus(data.user_id, false);
        // Reload user lists to reflect offline status
        loadAllUsers();
        loadFriends();
    } else if (data.type === 'user_status_changed') {
        console.log(`🔄 User ${data.user_id} status changed: ${data.is_online ? 'ONLINE' : 'OFFLINE'}`);
        updateUserStatus(data.user_id, data.is_online);
    } else if (data.type === 'friend_request') {
        showMessage(`🔔 New friend request from ${data.sender_name}`, 'info');
        loadPendingRequests();
    } else if (data.type === 'friend_request_accepted') {
        // Friend request was accepted by the recipient
        showMessage(`🎉 ${data.accepter_name || 'User'} accepted your friend request!`, 'success');
        loadFriends(); // Refresh friends list
        loadAllUsers(); // Refresh all users to update button states
    } else if (data.type === 'call_invite') {
        console.log('📞 ========== INCOMING CALL ==========');
        console.log('📞 Caller name:', data.caller_name);
        console.log('📞 Call ID:', data.call_id);
        console.log('📞 From user:', data.from_user_id);
        console.log('📞 ===================================');
        
        const callerName = data.caller_name || 'Someone';
        const callId = data.call_id;
        const fromUserId = data.from_user_id;
        
        // Show a more prominent notification
        showIncomingCallNotification(callerName, callId, fromUserId);
        
        // Also play a sound and show browser notification if supported
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Incoming Call', {
                body: `${callerName} wants to practice English with you`,
                icon: '/assets/icons/call.png'
            });
        }
    } else if (data.type === 'call_accepted') {
        console.log('✅ ========== CALL ACCEPTED ==========');
        console.log('✅ Call ID:', data.call_id);
        console.log('✅ Partner ID:', data.partner_id);
        console.log('✅ ===================================');
        
        // Check if this is for our pending call
        if (window.pendingCallId === data.call_id) {
            handleCallAccepted(data.call_id);
        }
    } else if (data.type === 'call_rejected') {
        console.log('❌ ========== CALL REJECTED ==========');
        console.log('❌ Call was rejected by:', data.rejected_by_name);
        console.log('❌ Call ID:', data.call_id);
        console.log('❌ ===================================');
        
        // Use the new handler function
        handleCallRejected(data.rejected_by_name);
    } else if (data.type === 'random_match_found') {
        console.log('🎲 ========== RANDOM MATCH FOUND ==========');
        console.log('🎲 Call ID:', data.call_id);
        console.log('🎲 Partner:', data.partner_name);
        console.log('🎲 =========================================');
        
        // Handle the random match
        handleRandomMatchFound(data);
    } else if (data.type === 'random_queue_status') {
        console.log('🎲 Queue status:', data.data);
        if (data.data.status === 'waiting') {
            // Still waiting in queue
            console.log('🎲 Position in queue:', data.data.position);
        } else if (data.data.status === 'already_in_queue') {
            showMessage('You are already in the queue', 'info');
        }
    } else if (data.type === 'random_queue_left') {
        console.log('🎲 Left queue:', data.data);
    } else {
        console.log('⚠️ Unknown message type:', data.type);
    }
}

function updateUserStatus(userId, isOnline) {
    const card = document.querySelector(`[data-user-id="${userId}"]`);
    if (card) {
        const badge = card.querySelector('.user-status-badge');
        badge.className = `user-status-badge ${isOnline ? 'online' : 'offline'}`;
        badge.textContent = `${isOnline ? '🟢' : '⚫'} ${isOnline ? 'Online' : 'Offline'}`;
        
        // Update call button
        const callBtn = card.querySelector('.btn-call, .btn-disabled');
        if (callBtn) {
            if (isOnline) {
                callBtn.className = 'btn-action btn-call';
                callBtn.disabled = false;
                callBtn.textContent = '📞 Call';
                callBtn.title = 'Start Call';
            } else {
                callBtn.className = 'btn-action btn-disabled';
                callBtn.disabled = true;
                callBtn.textContent = '📞 Offline';
                callBtn.title = 'User is offline';
            }
        }
    }
    
    // Update in arrays
    const userInAll = allUsers.find(u => u.id === userId);
    if (userInAll) userInAll.is_online = isOnline;
    
    const userInFriends = friends.find(u => u.id === userId);
    if (userInFriends) userInFriends.is_online = isOnline;
}

function attachUserCardListeners() {
    // Event listeners are already attached via onclick attributes
}

function showMessage(text, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `toast-message ${type}`;
    messageDiv.textContent = text;
    document.body.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        messageDiv.classList.remove('show');
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

function showIncomingCallNotification(callerName, callId, fromUserId) {
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
    
    // Play notification sound (if you have one)
    try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGWS45+mjUAwPVqzn77BdGAk+ltryy3krBSl+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsI');
        audio.play().catch(e => console.log('Could not play sound'));
    } catch (e) {
        console.log('Audio not supported');
    }
    
    // Handle accept
    document.getElementById('accept-call-btn').onclick = async () => {
        console.log('✅ Accepting call:', callId);
        
        // Send accept message via WebSocket to notify the caller
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'accept_call',
                call_id: callId,
                from_user_id: fromUserId
            }));
            console.log('📤 Sent call accept notification to caller');
        }
        
        overlay.remove();
        showMessage('✅ Call accepted! Connecting...', 'success');
        
        // Call accept endpoint to update DB, then redirect
        try {
            const token = localStorage.getItem('token');
            await fetch(`${API_BASE_URL}/api/calls/accept`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ call_id: callId })
            });
        } catch (e) {
            console.log('Accept API call failed, continuing anyway:', e);
        }
        
        // Redirect to WebRTC call page
        setTimeout(() => {
            window.location.href = `call.html?callId=${callId}`;
        }, 500);
    };
    
    // Handle reject
    document.getElementById('reject-call-btn').onclick = () => {
        console.log('❌ Rejecting call:', callId);
        
        // Send reject message via WebSocket to notify the caller
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'reject_call_invitation',
                call_id: callId,
                from_user_id: fromUserId
            }));
            console.log('📤 Sent call rejection notification to caller');
        }
        
        overlay.remove();
        showMessage('Call declined', 'info');
    };
    
    // Auto-dismiss after 30 seconds
    setTimeout(() => {
        if (document.getElementById('incoming-call-notification')) {
            // Send missed call notification
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'call_missed',
                    call_id: callId,
                    from_user_id: fromUserId
                }));
            }
            overlay.remove();
            showMessage('Missed call from ' + callerName, 'info');
        }
    }, 30000);
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUsersPage);
} else {
    initUsersPage();
}

// Handle page unload - close WebSocket connection
window.addEventListener('beforeunload', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
});
