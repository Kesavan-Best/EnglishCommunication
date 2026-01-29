// Users page functionality
let allUsers = [];
let friends = [];
let currentUser = null;
let ws = null;

// Initialize page
async function initUsersPage() {
    currentUser = JSON.parse(localStorage.getItem('user'));
    const token = localStorage.getItem('token');
    
    if (!token) {
        window.location.href = 'login.html';
        return;
    }
    
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
    
    // Refresh data every 10 seconds
    setInterval(() => {
        loadAllUsers();
        loadFriends();
        loadPendingRequests();
    }, 10000);
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


async function loadRandomPartner() {
    const btn = document.getElementById('find-random-btn');
    const statusDiv = document.getElementById('random-status');
    
    btn.disabled = true;
    btn.textContent = '🔍 Searching...';
    statusDiv.innerHTML = '<p class="searching">Looking for an online partner...</p>';
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.findRandomPartner, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const partner = await response.json();
            displayRandomPartner(partner);
        } else {
            const error = await response.json();
            statusDiv.innerHTML = `<p class="error">❌ ${error.detail || 'No online users available'}</p>`;
        }
    } catch (error) {
        console.error('Error finding random partner:', error);
        statusDiv.innerHTML = '<p class="error">❌ Error finding partner</p>';
    } finally {
        btn.disabled = false;
        btn.textContent = '🎲 Find Random Partner';
    }
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
    
    return `
        <div class="user-card" data-user-id="${user.id}">
            <div class="${onlineClass}">${onlineText}</div>
            <div class="user-avatar">
                <img src="${user.avatar_url || '../assets/icons/user-avatar.png'}" alt="${user.name}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">
            </div>
            <div class="user-info">
                <h3 class="user-name">${user.name}</h3>
                <p class="user-email">${user.email}</p>
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
            console.log('✅ Redirecting to call page...');
            
            // Validate call response
            if (!call.id || !call.jitsi_room_id) {
                throw new Error('Invalid call response from server');
            }
            
            showMessage('✅ Call invitation sent! Waiting for response...', 'success');
            
            // Show a waiting UI
            const waitingDiv = document.createElement('div');
            waitingDiv.id = 'call-waiting';
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
                <div style="background: white; padding: 40px; border-radius: 20px; text-align: center;">
                    <div style="font-size: 60px; margin-bottom: 20px;">📞</div>
                    <h2 style="color: #667eea; margin-bottom: 15px;">Calling...</h2>
                    <p style="color: #666; margin-bottom: 20px;">Waiting for the other person to answer</p>
                    <button onclick="document.getElementById('call-waiting').remove(); window.location.reload();" 
                            style="background: #f5576c; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 16px;">
                        Cancel Call
                    </button>
                </div>
            `;
            document.body.appendChild(waitingDiv);
            
            // Auto-redirect to call page after 2 seconds
            setTimeout(() => {
                const callUrl = `call.html?callId=${call.id}`;
                console.log('🔵 Redirecting to:', callUrl);
                window.location.href = callUrl;
            }, 2000);
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
        
        showMessage(`❌ Network error: ${error.message}. Make sure backend is running on http://localhost:8000`, 'error');
    }
}

function viewProfile(userId) {
    window.location.href = `profile.html?userId=${userId}`;
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
    
    const wsUrl = `ws://localhost:8000/api/ws/${userId}`;
    console.log('🔌 Connecting to WebSocket:', wsUrl);
    console.log('👤 User ID:', userId);
    console.log('👤 User Name:', currentUser.name);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('✅ WebSocket connected successfully');
        console.log('📡 Ready to receive call notifications');
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
    } else if (data.type === 'call_invite') {
        console.log('📞 ========== INCOMING CALL ==========');
        console.log('📞 Caller name:', data.caller_name);
        console.log('📞 Call ID:', data.call_id);
        console.log('📞 From user:', data.from_user_id);
        console.log('📞 ===================================');
        
        const callerName = data.caller_name || 'Someone';
        const callId = data.call_id;
        
        // Show a more prominent notification
        showIncomingCallNotification(callerName, callId);
        
        // Also play a sound and show browser notification if supported
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Incoming Call', {
                body: `${callerName} wants to practice English with you`,
                icon: '/assets/icons/call.png'
            });
        }
    } else if (data.type === 'call_rejected') {
        console.log('❌ Call was rejected by:', data.rejected_by_name);
        
        // Remove waiting overlay if exists
        const waitingDiv = document.getElementById('call-waiting');
        if (waitingDiv) {
            waitingDiv.remove();
        }
        
        // Show rejection message
        showMessage(`❌ ${data.rejected_by_name} declined your call`, 'error');
        
        // Re-enable call buttons
        const callButtons = document.querySelectorAll('.btn-call');
        callButtons.forEach(btn => {
            btn.disabled = false;
            btn.textContent = '📞 Call';
        });
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
    
    // Play notification sound (if you have one)
    try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGWS45+mjUAwPVqzn77BdGAk+ltryy3krBSl+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsIHGy96+mmUhEJTKXh8bllGgg2jdXxxn0pBSh+zPLaizsI');
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
        showMessage('Call declined', 'info');
        // Optionally notify backend about rejection
    };
    
    // Auto-dismiss after 30 seconds
    setTimeout(() => {
        if (document.getElementById('incoming-call-notification')) {
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
