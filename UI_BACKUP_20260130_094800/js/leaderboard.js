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
    const table = document.getElementById('leaderboard-table');
    const emptyState = document.getElementById('empty-state');
    
    console.log('Container:', container, 'Table:', table, 'Empty:', emptyState);
    
    if (!container) {
        console.error('Leaderboard container not found!');
        return;
    }
    
    // Check if no data
    if (!data || data.length === 0) {
        console.log('No leaderboard data, showing empty state');
        if (table) table.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        
        // Clear position data
        const userRank = document.getElementById('user-rank');
        const userPercentile = document.getElementById('user-percentile');
        if (userRank) userRank.textContent = '-';
        if (userPercentile) userPercentile.textContent = '-';
        
        // Clear platform stats
        document.getElementById('total-learners').textContent = '-';
        document.getElementById('active-learners').textContent = '-';
        document.getElementById('total-calls').textContent = '-';
        document.getElementById('avg-score').textContent = '-';
        
        return;
    }
    
    // Show leaderboard
    console.log('Showing leaderboard with', data.length, 'entries');
    if (table) table.style.display = 'table';
    if (emptyState) emptyState.style.display = 'none';
    
    // Display entries
    const currentUser = getCurrentUser();
    container.innerHTML = data.map((entry, index) => {
        const isCurrentUser = entry.user_id === currentUser?.id;
        const initials = entry.name ? entry.name.charAt(0).toUpperCase() : 'U';
        
        return `
            <tr ${isCurrentUser ? 'style="background: rgba(102, 126, 234, 0.05);"' : ''}>
                <td class="rank-cell">${index + 1}</td>
                <td class="user-cell">
                    <div class="user-avatar">${initials}</div>
                    <div class="user-info">
                        <div class="user-name">${entry.name}${isCurrentUser ? ' (You)' : ''}</div>
                        <div class="user-email">${entry.email || ''}</div>
                    </div>
                </td>
                <td class="score-cell">${entry.ai_score ? entry.ai_score.toFixed(1) : '0.0'}</td>
                <td>${entry.total_calls || 0}</td>
                <td>${entry.avg_fluency_score ? entry.avg_fluency_score.toFixed(1) : '0.0'}%</td>
            </tr>
        `;
    }).join('');
    
    // Update user position
    const userEntry = data.find(entry => entry.user_id === currentUser?.id);
    if (userEntry) {
        const userRank = document.getElementById('user-rank');
        const userPercentile = document.getElementById('user-percentile');
        const rank = data.findIndex(entry => entry.user_id === currentUser?.id) + 1;
        const percentile = ((data.length - rank) / data.length * 100).toFixed(0);
        
        if (userRank) userRank.textContent = `#${rank}`;
        if (userPercentile) userPercentile.textContent = `${percentile}%`;
    }
    
    // Update platform stats (if backend provides them)
    // For now, calculate from data
    const totalCalls = data.reduce((sum, entry) => sum + (entry.total_calls || 0), 0);
    const avgScore = data.length > 0 ? (data.reduce((sum, entry) => sum + (entry.ai_score || 0), 0) / data.length).toFixed(1) : '0.0';
    
    document.getElementById('total-learners').textContent = data.length;
    document.getElementById('active-learners').textContent = data.filter(e => e.total_calls > 0).length;
    document.getElementById('total-calls').textContent = totalCalls;
    document.getElementById('avg-score').textContent = avgScore;
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLeaderboardPage);
} else {
    initLeaderboardPage();
}
