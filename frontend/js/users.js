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
        loadFriends()
    ]);
    
    // Setup WebSocket for live updates
    setupWebSocket();
    
    // Setup search
    setupSearch();
    
    // Refresh data every 10 seconds
    setInterval(() => {
        loadAllUsers();
        loadFriends();
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
        const response = await fetch(API_ENDPOINTS.allUsers, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            allUsers = await response.json();
            // Filter out current user
            allUsers = allUsers.filter(u => u.id !== currentUser.id);
            displayUsers(allUsers, 'all-users-grid');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showMessage('Failed to load users', 'error');
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
    const onlineClass = user.is_online ? 'online' : 'offline';
    const onlineText = user.is_online ? 'Online' : 'Offline';
    const onlineDot = user.is_online ? '🟢' : '⚫';
    
    const callBtn = user.is_online ? 
        `<button class="btn-action btn-call" onclick="initiateCall('${user.id}')" title="Start Call">
            📞 Call
        </button>` :
        `<button class="btn-action btn-disabled" disabled title="User is offline">
            📞 Offline
        </button>`;
    
    const friendBtn = isFriend ? '' : 
        `<button class="btn-action btn-add-friend" onclick="sendFriendRequest('${user.id}')" title="Send Friend Request">
            ➕ Add Friend
        </button>`;
    
    return `
        <div class="user-card" data-user-id="${user.id}">
            <div class="user-status-badge ${onlineClass}">${onlineDot} ${onlineText}</div>
            <div class="user-avatar">
                <img src="${user.avatar_url || '../assets/icons/user-avatar.png'}" alt="${user.name}">
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
        const token = localStorage.getItem('token');
        const response = await fetch(API_ENDPOINTS.inviteCall, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ receiver_id: userId })
        });
        
        if (response.ok) {
            const call = await response.json();
            // Redirect to call page
            window.location.href = `call.html?callId=${call.id}`;
        } else {
            const error = await response.json();
            showMessage(`❌ ${error.detail || 'Failed to start call'}`, 'error');
        }
    } catch (error) {
        console.error('Error initiating call:', error);
        showMessage('❌ Network error', 'error');
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
    ws = new WebSocket(`ws://localhost:8000/ws/connect?token=${token}`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed, reconnecting in 5s...');
        setTimeout(setupWebSocket, 5000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'user_status_changed') {
        updateUserStatus(data.user_id, data.is_online);
    } else if (data.type === 'friend_request') {
        showMessage(`🔔 New friend request from ${data.sender_name}`, 'info');
        // Reload friends list
        loadFriends();
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

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUsersPage);
} else {
    initUsersPage();
}
