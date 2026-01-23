// Leaderboard page functionality
let leaderboardData = [];
let currentTimeframe = 'all';
let currentSkillFilter = 'all';

// Initialize leaderboard page
async function initLeaderboardPage() {
    const currentUser = checkAuth();
    if (!currentUser) return;
    
    // Setup filters
    setupFilters();
    
    // Load leaderboard
    await loadLeaderboard();
    
    // Refresh every 30 seconds
    setInterval(loadLeaderboard, 30000);
}

// Get current user helper
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// Setup filters
function setupFilters() {
    const timeframeSelect = document.getElementById('timeframe-filter');
    const skillSelect = document.getElementById('skill-filter');
    
    if (timeframeSelect) {
        timeframeSelect.addEventListener('change', (e) => {
            currentTimeframe = e.target.value;
            loadLeaderboard();
        });
    }
    
    if (skillSelect) {
        skillSelect.addEventListener('change', (e) => {
            currentSkillFilter = e.target.value;
            loadLeaderboard();
        });
    }
}

// Load leaderboard
async function loadLeaderboard() {
    console.log('Loading leaderboard...');
    
    try {
        const token = localStorage.getItem('token');
        const params = new URLSearchParams({
            timeframe: currentTimeframe,
            skill_filter: currentSkillFilter,
            limit: 20
        });
        
        const url = `${API_ENDPOINTS.leaderboard}?${params}`;
        console.log('Fetching leaderboard from:', url);
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        console.log('Leaderboard response status:', response.status);
        
        if (response.ok) {
            leaderboardData = await response.json();
            console.log('Leaderboard data:', leaderboardData);
            displayLeaderboard(leaderboardData);
        } else {
            const errorText = await response.text();
            console.error('Leaderboard API error:', response.status, errorText);
            displayLeaderboard([]);
        }
    } catch (error) {
        console.error('Error loading leaderboard:', error);
        displayLeaderboard([]);
    }
}

// Display leaderboard
function displayLeaderboard(data) {
    console.log('Displaying leaderboard with data:', data);
    
    const container = document.getElementById('leaderboard-list');
    const emptyState = document.getElementById('empty-state');
    const loadingState = document.getElementById('loading-state');
    
    console.log('Container:', container, 'Empty:', emptyState, 'Loading:', loadingState);
    
    if (!container) {
        console.error('Leaderboard container not found!');
        return;
    }
    
    // Hide loading
    if (loadingState) {
        loadingState.style.display = 'none';
        console.log('Loading state hidden');
    }
    
    // Check if no data
    if (!data || data.length === 0) {
        console.log('No leaderboard data, showing empty state');
        container.style.display = 'none';
        if (emptyState) {
            emptyState.style.display = 'block';
            emptyState.innerHTML = `
                <div style="text-align: center; padding: 60px 20px;">
                    <div style="font-size: 80px; margin-bottom: 20px;">🏆</div>
                    <h2 style="color: #333; margin-bottom: 10px;">No Rankings Yet</h2>
                    <p style="color: #666; font-size: 18px; margin-bottom: 30px;">
                        Be the first to make calls and climb to the top!
                    </p>
                    <p style="color: #999;">
                        Rankings are based on AI scores from practice calls.<br>
                        Start practicing with your friends or random partners to appear here.
                    </p>
                    <button onclick="window.location.href='users.html'" class="btn-primary" style="margin-top: 30px; padding: 15px 30px; border: none; border-radius: 8px; background: #667eea; color: white; font-weight: 600; cursor: pointer; font-size: 16px;">
                        🎯 Find Practice Partners
                    </button>
                </div>
            `;
        }
        return;
    }
    
    // Show leaderboard
    console.log('Showing leaderboard with', data.length, 'entries');
    container.style.display = 'block';
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    
    // Display entries
    const currentUser = getCurrentUser();
    container.innerHTML = data.map((entry, index) => {
        const isCurrentUser = entry.user_id === currentUser?.id;
        const rankClass = index < 3 ? `rank-${index + 1}` : '';
        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '';
        
        return `
            <div class="leaderboard-entry ${rankClass} ${isCurrentUser ? 'current-user' : ''}">
                <div class="rank">
                    ${medal || `#${entry.rank}`}
                </div>
                <div class="user-avatar">
                    <img src="${getAvatarUrl(entry)}" alt="${entry.name}">
                </div>
                <div class="user-info">
                    <div class="user-name">${entry.name} ${isCurrentUser ? '<span style="color: #667eea; font-weight: 600;">(You)</span>' : ''}</div>
                    <div class="user-stats-mini">
                        <span>📞 ${entry.total_calls} calls</span>
                        <span>🎯 ${entry.avg_fluency_score.toFixed(1)}% fluency</span>
                    </div>
                </div>
                <div class="score">
                    <div class="score-value">${entry.ai_score.toFixed(1)}</div>
                    <div class="score-label">AI Score</div>
                </div>
            </div>
        `;
    }).join('');
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLeaderboardPage);
} else {
    initLeaderboardPage();
}
