// js/profile.js - Fixed version
// API_BASE_URL is loaded from config.js

let profilePageInitialized = false;
let profileEnrollRecorder = null;
let profileEnrollChunks = [];
let profileEnrollTimer = null;
let profileEnrollSeconds = 0;
const PROFILE_ENROLL_TARGET_SECONDS = 25;
let profileVoiceEnrolled = false;
let profileVoiceRequired = false;
let profileVoiceSectionReady = false;
let profileLastEnrollmentTranscript = '';
let profileLastEnrollmentTranscriptConfidence = null;
let profileLastEnrollmentAudioUrl = '';
let profileVoiceIdLabel = '';
let profileEnrolledAt = '';

// Initialize profile page
async function initProfilePage() {
    if (profilePageInitialized) {
        return;
    }
    profilePageInitialized = true;

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

        // Voice enrollment entry point from profile for current user.
        await initVoiceEnrollmentProfile(token, userId);
        
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
            ? API_ENDPOINTS.userProfile(userId)
            : API_ENDPOINTS.me;
        
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
        
        const response = await fetch(API_ENDPOINTS.userStats, {
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
        
        const response = await fetch(API_ENDPOINTS.recentCalls, {
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
    // Update progress bars - ALL START AT ZERO until real data exists
    const analysisStats = stats.analysis_stats || {};
    
    // Only show real data when it exists, otherwise keep at 0
    const grammarPercent = analysisStats.avg_grammar_errors !== undefined 
        ? Math.min(100, 100 - analysisStats.avg_grammar_errors * 5) 
        : 0;
    const fluencyPercent = analysisStats.avg_fluency || 0;
    const vocabPercent = analysisStats.vocabulary_repetition !== undefined
        ? Math.min(100, 100 - analysisStats.vocabulary_repetition * 100)
        : 0;
    const pronunciationPercent = analysisStats.pronunciation_score || 0; // NO DEFAULT - start at 0
    
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

async function initVoiceEnrollmentProfile(token, userId) {
    const container = document.getElementById('voice-id-container');
    if (!container) return;

    // Voice setup is only for the logged-in user's own profile.
    if (userId) {
        container.style.display = 'none';
        return;
    }

    bindVoiceEnrollmentProfileEvents();
    await refreshVoiceEnrollmentProfileStatus(token);
}

function bindVoiceEnrollmentProfileEvents() {
    if (profileVoiceSectionReady) return;
    profileVoiceSectionReady = true;

    const openBtn = document.getElementById('voice-enroll-open-btn');
    const refreshBtn = document.getElementById('voice-enroll-refresh-btn');
    const startBtn = document.getElementById('profileEnrollStartBtn');
    const closeBtn = document.getElementById('profileEnrollCloseBtn');
    const transcriptToggleBtn = document.getElementById('profileEnrollTranscriptToggle');

    if (openBtn) {
        openBtn.addEventListener('click', () => {
            openProfileVoiceEnrollModal();
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            const token = localStorage.getItem('token');
            if (token) {
                await refreshVoiceEnrollmentProfileStatus(token);
                showToast('Voice ID status refreshed', 'info');
            }
        });
    }

    if (startBtn) {
        startBtn.addEventListener('click', startProfileVoiceEnrollment);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeProfileVoiceEnrollModal);
    }

    if (transcriptToggleBtn) {
        transcriptToggleBtn.addEventListener('click', toggleProfileEnrollTranscript);
    }

    const modal = document.getElementById('profileVoiceEnrollModal');
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeProfileVoiceEnrollModal();
            }
        });
    }
}

async function refreshVoiceEnrollmentProfileStatus(token) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/users/voice-enrollment-status`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`Voice status request failed: ${response.status}`);
        }

        const data = await response.json();
        profileVoiceEnrolled = Boolean(data.enrolled);
        profileVoiceRequired = Boolean(data.required) && !profileVoiceEnrolled;
        profileLastEnrollmentTranscript = (data.last_enrollment_transcription || '').trim();
        profileLastEnrollmentTranscriptConfidence = data.last_enrollment_transcription_confidence;
        profileLastEnrollmentAudioUrl = (data.last_enrollment_audio_url || '').trim();
        profileVoiceIdLabel = (data.voice_id_label || '').trim();
        profileEnrolledAt = (data.enrolled_at || '').trim();

        localStorage.setItem('voice_fingerprint_enrolled', profileVoiceEnrolled ? 'true' : 'false');
        localStorage.setItem('voice_enrollment_required', profileVoiceRequired ? 'true' : 'false');

        updateVoiceEnrollmentProfileUI(data);
    } catch (error) {
        console.error('Voice enrollment status check failed:', error);
        updateVoiceEnrollmentProfileErrorState();
    }
}

function updateVoiceEnrollmentProfileUI(data) {
    const badge = document.getElementById('voice-enrollment-badge');
    const state = document.getElementById('voice-enrollment-state');
    const meta = document.getElementById('voice-enrollment-meta');
    const openBtn = document.getElementById('voice-enroll-open-btn');

    if (badge) {
        badge.classList.remove('required', 'optional', 'enrolled');
        if (profileVoiceEnrolled) {
            badge.classList.add('enrolled');
            badge.textContent = 'Enrolled';
        } else if (profileVoiceRequired) {
            badge.classList.add('required');
            badge.textContent = 'Required';
        } else {
            badge.classList.add('optional');
            badge.textContent = 'Optional';
        }
    }

    if (state) {
        if (profileVoiceEnrolled) {
            state.textContent = 'Voice ID is set. You can re-record any time from this page.';
        } else if (profileVoiceRequired) {
            state.textContent = 'Voice ID setup is required for random matching. Complete it here now.';
        } else {
            state.textContent = 'Voice ID is not set yet. You can set it now from your profile.';
        }
    }

    if (meta) {
        if (data.enrolled_at) {
            const dt = new Date(data.enrolled_at);
            meta.textContent = `Last enrolled: ${dt.toLocaleString()}`;
        } else {
            meta.textContent = 'Recommended recording length: 20-30 seconds in a quiet place.';
        }
    }

    if (openBtn) {
        openBtn.innerHTML = profileVoiceEnrolled
            ? '<i class="fas fa-redo"></i> Re-Record Voice ID'
            : '<i class="fas fa-microphone"></i> Set Up Voice ID';
    }

    updateVoiceEnrollmentTranscriptPreview(
        data.last_enrollment_transcription,
        data.last_enrollment_transcription_confidence,
        data.last_enrollment_audio_url,
        data.voice_id_label,
        data.enrolled_at
    );
}

function updateVoiceEnrollmentTranscriptPreview(transcript, confidence, audioUrl, voiceIdLabel, enrolledAt) {
    const preview = document.getElementById('voice-enrollment-transcript-preview');
    const textEl = document.getElementById('voice-enrollment-transcript-preview-text');
    const metaEl = document.getElementById('voice-enrollment-transcript-preview-meta');
    const audioEl = document.getElementById('voice-enrollment-transcript-preview-audio');

    if (!preview || !textEl || !metaEl || !audioEl) return;

    const safeTranscript = (transcript || '').trim();
    const safeAudioUrl = (audioUrl || '').trim();
    if (!safeTranscript && !safeAudioUrl) {
        preview.style.display = 'none';
        textEl.textContent = '';
        metaEl.textContent = '';
        audioEl.style.display = 'none';
        audioEl.removeAttribute('src');
        return;
    }

    preview.style.display = 'block';
    if (safeAudioUrl) {
        audioEl.src = safeAudioUrl;
        audioEl.style.display = 'block';
    } else {
        audioEl.style.display = 'none';
        audioEl.removeAttribute('src');
    }
    textEl.textContent = safeTranscript || 'Transcription is unavailable for this recording.';
    const confidenceText = (typeof confidence === 'number' && !Number.isNaN(confidence))
        ? `Confidence: ${Math.round(confidence * 100)}%`
        : 'Confidence: not available';
    const labelText = voiceIdLabel ? `Voice ID: ${voiceIdLabel}` : '';
    const enrolledText = enrolledAt ? `Enrolled: ${new Date(enrolledAt).toLocaleString()}` : '';
    metaEl.textContent = [labelText, enrolledText, confidenceText].filter(Boolean).join(' | ');
}

function updateVoiceEnrollmentProfileErrorState() {
    const badge = document.getElementById('voice-enrollment-badge');
    const state = document.getElementById('voice-enrollment-state');
    const meta = document.getElementById('voice-enrollment-meta');

    if (badge) {
        badge.classList.remove('required', 'optional', 'enrolled');
        badge.textContent = 'Unavailable';
    }
    if (state) {
        state.textContent = 'Could not load Voice ID status right now.';
    }
    if (meta) {
        meta.textContent = 'Please check connection and click Refresh Status.';
    }
}

function openProfileVoiceEnrollModal() {
    const modal = document.getElementById('profileVoiceEnrollModal');
    const status = document.getElementById('profileEnrollStatus');
    const timerBar = document.getElementById('profileTimerBar');
    const timerFill = document.getElementById('profileTimerFill');
    const startBtn = document.getElementById('profileEnrollStartBtn');

    if (modal) {
        modal.style.display = 'flex';
    }

    if (status) {
        status.textContent = profileVoiceEnrolled
            ? 'You are re-enrolling your Voice ID. This will replace the previous fingerprint.'
            : 'Record 20-30 seconds of natural English speech.';
        status.style.color = '#4361ee';
    }

    if (timerBar) {
        timerBar.style.display = 'none';
    }
    if (timerFill) {
        timerFill.style.width = '0%';
    }
    if (startBtn) {
        startBtn.disabled = false;
        startBtn.textContent = profileVoiceEnrolled ? '🎤 Re-Record Voice ID' : '🎤 Start Recording';
    }

    updateProfileEnrollTranscriptPanel(
        profileLastEnrollmentTranscript,
        profileLastEnrollmentTranscriptConfidence,
        profileLastEnrollmentAudioUrl,
        profileVoiceIdLabel,
        profileEnrolledAt,
        profileLastEnrollmentTranscript ? 'This is the latest saved enrollment transcription.' : ''
    );
}

function closeProfileVoiceEnrollModal() {
    const modal = document.getElementById('profileVoiceEnrollModal');
    if (modal) {
        modal.style.display = 'none';
    }

    if (profileEnrollTimer) {
        clearInterval(profileEnrollTimer);
        profileEnrollTimer = null;
    }

    if (profileEnrollRecorder && profileEnrollRecorder.state !== 'inactive') {
        try {
            profileEnrollRecorder.stop();
        } catch (e) {
            // Ignore recorder stop race.
        }
    }
}

function setProfileEnrollStatus(message, color = '#4361ee') {
    const status = document.getElementById('profileEnrollStatus');
    if (!status) return;
    status.textContent = message;
    status.style.color = color;
}

function toggleProfileEnrollTranscript() {
    const box = document.getElementById('profileEnrollTranscriptBox');
    const btn = document.getElementById('profileEnrollTranscriptToggle');
    if (!box || !btn) return;

    const isOpen = box.style.display === 'block';
    box.style.display = isOpen ? 'none' : 'block';
    btn.textContent = isOpen ? 'Show Captured Speech Text' : 'Hide Captured Speech Text';
}

function updateProfileEnrollTranscriptPanel(transcript, confidence, audioUrl, voiceIdLabel, enrolledAt, note = '') {
    const wrap = document.getElementById('profileEnrollTranscriptWrap');
    const box = document.getElementById('profileEnrollTranscriptBox');
    const textEl = document.getElementById('profileEnrollTranscriptText');
    const metaEl = document.getElementById('profileEnrollTranscriptMeta');
    const btn = document.getElementById('profileEnrollTranscriptToggle');
    const audioEl = document.getElementById('profileEnrollTranscriptAudio');

    if (!wrap || !box || !textEl || !metaEl || !btn || !audioEl) return;

    const safeTranscript = (transcript || '').trim();
    const safeNote = (note || '').trim();
    const safeAudioUrl = (audioUrl || '').trim();
    if (!safeTranscript && !safeNote && !safeAudioUrl) {
        wrap.style.display = 'none';
        box.style.display = 'none';
        btn.textContent = 'Show Captured Speech Text';
        textEl.textContent = '';
        metaEl.textContent = '';
        audioEl.style.display = 'none';
        audioEl.removeAttribute('src');
        return;
    }

    wrap.style.display = 'block';
    box.style.display = 'none';
    btn.textContent = 'Show Captured Speech Text';
    if (safeAudioUrl) {
        audioEl.src = safeAudioUrl;
        audioEl.style.display = 'block';
    } else {
        audioEl.style.display = 'none';
        audioEl.removeAttribute('src');
    }
    textEl.textContent = safeTranscript || 'Transcription is unavailable for this recording.';

    const confidenceText = (typeof confidence === 'number' && !Number.isNaN(confidence))
        ? `Confidence: ${Math.round(confidence * 100)}%`
        : 'Confidence: not available';
    const labelText = voiceIdLabel ? `Voice ID: ${voiceIdLabel}` : '';
    const enrolledText = enrolledAt ? `Enrolled: ${new Date(enrolledAt).toLocaleString()}` : '';
    const baseMeta = [labelText, enrolledText, confidenceText].filter(Boolean).join(' | ');
    metaEl.textContent = safeNote ? `${baseMeta} | ${safeNote}` : baseMeta;
}

async function startProfileVoiceEnrollment() {
    const startBtn = document.getElementById('profileEnrollStartBtn');
    if (startBtn) {
        startBtn.disabled = true;
    }

    if (!window.MediaRecorder) {
        setProfileEnrollStatus('❌ This browser does not support voice recording.', '#e53e3e');
        if (startBtn) {
            startBtn.disabled = false;
        }
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        profileEnrollChunks = [];

        const preferredMimeTypes = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4'
        ];

        let selectedMimeType = '';
        for (const mime of preferredMimeTypes) {
            if (MediaRecorder.isTypeSupported(mime)) {
                selectedMimeType = mime;
                break;
            }
        }

        profileEnrollRecorder = selectedMimeType
            ? new MediaRecorder(stream, { mimeType: selectedMimeType })
            : new MediaRecorder(stream);

        window.__profileVoiceEnrollMimeType = profileEnrollRecorder.mimeType || selectedMimeType || 'audio/webm';

        profileEnrollRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                profileEnrollChunks.push(event.data);
            }
        };

        profileEnrollRecorder.onstop = async () => {
            stream.getTracks().forEach(track => track.stop());
            await uploadProfileVoiceEnrollment();
        };

        profileEnrollRecorder.start();
        updateProfileEnrollTranscriptPanel('', null, '', '', '', '');

        const timerBar = document.getElementById('profileTimerBar');
        if (timerBar) {
            timerBar.style.display = 'block';
        }

        profileEnrollSeconds = 0;
        setProfileEnrollStatus('🔴 Recording... speak naturally in English', '#e53e3e');

        profileEnrollTimer = setInterval(() => {
            profileEnrollSeconds += 1;
            const progress = Math.min((profileEnrollSeconds / PROFILE_ENROLL_TARGET_SECONDS) * 100, 100);
            const fill = document.getElementById('profileTimerFill');
            if (fill) {
                fill.style.width = `${progress}%`;
            }

            setProfileEnrollStatus(`🔴 Recording... ${profileEnrollSeconds}s / ${PROFILE_ENROLL_TARGET_SECONDS}s`, '#e53e3e');

            if (profileEnrollSeconds >= PROFILE_ENROLL_TARGET_SECONDS) {
                clearInterval(profileEnrollTimer);
                profileEnrollTimer = null;
                profileEnrollRecorder.stop();
            }
        }, 1000);
    } catch (error) {
        console.error('Profile voice enrollment start failed:', error);
        setProfileEnrollStatus('❌ Microphone access denied. Please allow microphone permission.', '#e53e3e');
        if (startBtn) {
            startBtn.disabled = false;
        }
    }
}

async function uploadProfileVoiceEnrollment() {
    const token = localStorage.getItem('token');
    const startBtn = document.getElementById('profileEnrollStartBtn');

    if (!token) {
        setProfileEnrollStatus('❌ You are not logged in. Please log in again.', '#e53e3e');
        if (startBtn) {
            startBtn.disabled = false;
        }
        return;
    }

    setProfileEnrollStatus('⏳ Processing your voice...', '#4361ee');

    const mimeType = window.__profileVoiceEnrollMimeType || 'audio/webm';
    const blob = new Blob(profileEnrollChunks, { type: mimeType });
    const formData = new FormData();

    let filename = 'profile_enrollment.webm';
    if (mimeType.includes('wav')) filename = 'profile_enrollment.wav';
    else if (mimeType.includes('ogg')) filename = 'profile_enrollment.ogg';
    else if (mimeType.includes('mp4') || mimeType.includes('m4a')) filename = 'profile_enrollment.mp4';

    formData.append('audio', blob, filename);

    try {
        const response = await fetch(`${API_BASE_URL}/api/users/enroll-voice`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            localStorage.setItem('voice_fingerprint_enrolled', 'true');
            localStorage.setItem('voice_enrollment_required', 'false');
            profileLastEnrollmentTranscript = (data.enrollment_transcription || '').trim();
            profileLastEnrollmentTranscriptConfidence = data.transcription_confidence;
            profileLastEnrollmentAudioUrl = (data.enrollment_audio_url || '').trim();
            profileVoiceIdLabel = (data.voice_id_label || '').trim();
            profileEnrolledAt = (data.enrolled_at || '').trim();

            setProfileEnrollStatus('✅ Voice ID enrolled successfully!', '#38a169');
            await refreshVoiceEnrollmentProfileStatus(token);
            updateProfileEnrollTranscriptPanel(
                data.enrollment_transcription,
                data.transcription_confidence,
                data.enrollment_audio_url,
                data.voice_id_label,
                data.enrolled_at,
                data.transcription_note
            );

            if (startBtn) {
                startBtn.textContent = '🎤 Re-Record Voice ID';
                startBtn.disabled = false;
            }

            const closeBtn = document.getElementById('profileEnrollCloseBtn');
            if (closeBtn) {
                closeBtn.textContent = 'Done';
            }

            showToast('Voice ID saved to your profile successfully', 'success');
        } else {
            setProfileEnrollStatus(`❌ ${data.detail || 'Voice enrollment failed. Please try again.'}`, '#e53e3e');
            if (startBtn) {
                startBtn.disabled = false;
            }
        }
    } catch (error) {
        console.error('Profile voice enrollment upload failed:', error);
        setProfileEnrollStatus('❌ Network error while uploading voice. Please try again.', '#e53e3e');
        if (startBtn) {
            startBtn.disabled = false;
        }
    }
}