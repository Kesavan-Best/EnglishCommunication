// call.js - WebRTC calling logic (separated from HTML)

const CallManager = {
    // Configuration
    config: {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            { urls: 'stun:stun2.l.google.com:19302' },
            { urls: 'stun:stun3.l.google.com:19302' },
            { urls: 'stun:stun4.l.google.com:19302' },
            // Free TURN servers via Metered
            {
                urls: 'turn:a.relay.metered.ca:80',
                username: 'e8dd65b92add87306a510286',
                credential: 'DjxR8C/gCPJAL8DR'
            },
            {
                urls: 'turn:a.relay.metered.ca:80?transport=tcp',
                username: 'e8dd65b92add87306a510286',
                credential: 'DjxR8C/gCPJAL8DR'
            },
            {
                urls: 'turn:a.relay.metered.ca:443',
                username: 'e8dd65b92add87306a510286',
                credential: 'DjxR8C/gCPJAL8DR'
            },
            {
                urls: 'turns:a.relay.metered.ca:443?transport=tcp',
                username: 'e8dd65b92add87306a510286',
                credential: 'DjxR8C/gCPJAL8DR'
            }
        ],
        sdpSemantics: 'unified-plan',
        iceCandidatePoolSize: 10,
        iceTransportPolicy: 'all',
        bundlePolicy: 'max-bundle',
        rtcpMuxPolicy: 'require'
    },
    
    // State
    state: {
        peerConnection: null,
        localStream: null,
        remoteStream: null,
        ws: null,
        callTimer: null,
        callStartTime: null,
        isMuted: false,
        currentUser: null,
        partnerUser: null,
        callId: null,
        isCaller: false,
        reconnectAttempts: 0,
        maxReconnectAttempts: 3,
        wsReconnectAttempts: 0,
        maxWsReconnectAttempts: 5,
        remoteDescriptionSet: false,
        iceCandidateBuffer: [],
        partnerJoined: false
    },
    
    // Initialize call
    async initialize(callId, currentUser) {
        this.state.callId = callId;
        this.state.currentUser = currentUser;
        
        console.log('📞 Initializing call with ID:', callId);
        
        try {
            // Fetch call details
            await this.fetchCallDetails();
            
            // Update UI
            this.updateUI();
            
            return true;
        } catch (error) {
            console.error('❌ Initialization failed:', error);
            this.showError('Failed to initialize call', true);
            return false;
        }
    },
    
    // Fetch call details from backend
    async fetchCallDetails() {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/calls/my-calls`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const calls = await response.json();
        const call = calls.find(c => c.id === this.state.callId);
        
        if (!call) {
            throw new Error('Call not found');
        }
        
        // Determine role
        this.state.isCaller = call.caller_id === this.state.currentUser.id;
        const partnerId = this.state.isCaller ? call.receiver_id : call.caller_id;
        
        // Fetch partner details
        await this.fetchPartnerDetails(partnerId);
        
        // Store additional call info if needed
        this.state.roomId = call.jitsi_room_id;
        
        return call;
    },
    
    // Fetch partner details
    async fetchPartnerDetails(partnerId) {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/users/${partnerId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            this.state.partnerUser = await response.json();
        } else {
            this.state.partnerUser = { id: partnerId, name: 'Partner' };
        }
    },
    
    // Start WebRTC call
    async startCall() {
        console.log('🎬 Starting WebRTC call...');
        
        try {
            // Get microphone access
            await this.getLocalStream();
            
            // Connect to signaling server
            await this.connectWebSocket();
            
            // Initialize WebRTC
            await this.initializeWebRTC();
            
            // If caller, create offer after a delay to give partner time to connect.
            // If partner_joined was already received, createOffer fires immediately
            // from the message handler instead.
            if (this.state.isCaller && !this.state.partnerJoined) {
                setTimeout(() => {
                    if (!this.state.partnerJoined) {
                        console.log('⏳ Partner not yet joined, sending offer anyway');
                        this.createOffer();
                    }
                }, 2000);
            } else if (this.state.isCaller && this.state.partnerJoined) {
                this.createOffer();
            }
            
            this.updateStatus('Waiting for partner...', '⏳');
            
        } catch (error) {
            console.error('❌ Failed to start call:', error);
            this.showError(`Failed to start call: ${error.message}`, false);
        }
    },
    
    // Get local microphone stream with fallback
    async getLocalStream() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Microphone API not available. Make sure you are using HTTPS.');
        }
        
        const constraintSets = [
            { audio: { echoCancellation: { ideal: true }, noiseSuppression: { ideal: true }, autoGainControl: { ideal: true } }, video: false },
            { audio: true, video: false }
        ];
        
        let lastError = null;
        for (const constraints of constraintSets) {
            try {
                this.state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
                console.log('✅ Microphone access granted');
                return;
            } catch (error) {
                lastError = error;
                console.warn('⚠️ getUserMedia failed:', error.name, error.message);
            }
        }
        
        console.error('❌ Microphone access denied:', lastError);
        throw new Error('Microphone access is required. Please allow microphone permissions.');
    },
    
    // Connect to WebSocket signaling server
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                // Build WS URL - use WS_BASE_URL from config.js if available,
                // otherwise derive from current page protocol
                let wsUrl;
                if (typeof WS_BASE_URL !== 'undefined' && WS_BASE_URL) {
                    wsUrl = `${WS_BASE_URL}/api/ws/${this.state.currentUser.id}`;
                } else {
                    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
                    wsUrl = `${protocol}://${window.location.host}/api/ws/${this.state.currentUser.id}`;
                }
                
                console.log('🔌 Connecting to WebSocket:', wsUrl);
                
                this.state.ws = new WebSocket(wsUrl);
                this.state.wsReconnectAttempts = 0;
                
                this.state.ws.onopen = () => {
                    console.log('✅ WebSocket connected');
                    resolve();
                    
                    // Send join call message
                    this.state.ws.send(JSON.stringify({
                        type: 'join-call',
                        call_id: this.state.callId,
                        partner_id: this.state.partnerUser.id
                    }));
                    
                    // Start heartbeat to keep connection alive on Render
                    this._startHeartbeat();
                };
                
                this.state.ws.onmessage = this.handleWebSocketMessage.bind(this);
                
                this.state.ws.onerror = (error) => {
                    console.error('❌ WebSocket error:', error);
                    reject(new Error('Failed to connect to signaling server'));
                };
                
                this.state.ws.onclose = () => {
                    console.log('🔌 WebSocket closed');
                    this._stopHeartbeat();
                    this._attemptWsReconnect();
                };
                
            } catch (error) {
                reject(error);
            }
        });
    },
    
    // WebSocket heartbeat to prevent Render from dropping idle connections
    _startHeartbeat() {
        this._stopHeartbeat();
        this._heartbeatInterval = setInterval(() => {
            if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
                this.state.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 15000);
    },
    
    _stopHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }
    },
    
    // Auto-reconnect WebSocket on unexpected close
    _attemptWsReconnect() {
        if (this.state.wsReconnectAttempts >= this.state.maxWsReconnectAttempts) return;
        if (!this.state.callId) return; // call ended, don't reconnect
        
        this.state.wsReconnectAttempts++;
        const delay = 1500 * this.state.wsReconnectAttempts;
        console.log(`🔄 WS reconnect attempt ${this.state.wsReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.state.callId) return;
            
            let wsUrl;
            if (typeof WS_BASE_URL !== 'undefined' && WS_BASE_URL) {
                wsUrl = `${WS_BASE_URL}/api/ws/${this.state.currentUser.id}`;
            } else {
                const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
                wsUrl = `${protocol}://${window.location.host}/api/ws/${this.state.currentUser.id}`;
            }
            
            this.state.ws = new WebSocket(wsUrl);
            
            this.state.ws.onopen = () => {
                console.log('✅ WebSocket reconnected');
                this.state.wsReconnectAttempts = 0;
                this._startHeartbeat();
            };
            this.state.ws.onmessage = this.handleWebSocketMessage.bind(this);
            this.state.ws.onerror = () => {};
            this.state.ws.onclose = () => {
                this._stopHeartbeat();
                this._attemptWsReconnect();
            };
        }, delay);
    },
    
    // Handle WebSocket messages
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('📨 WebSocket:', data.type);
            
            switch(data.type) {
                case 'webrtc_signal':
                    this.handleWebRTCSignal(data.signal);
                    break;
                    
                case 'partner_joined':
                    console.log('✅ Partner joined call');
                    this.state.partnerJoined = true;
                    // If we're the caller, now create the offer (partner is ready)
                    if (this.state.isCaller && this.state.peerConnection) {
                        this.createOffer();
                    }
                    break;
                    
                case 'call_accepted':
                    console.log('✅ Call accepted by partner');
                    this.state.partnerJoined = true;
                    if (this.state.isCaller && this.state.peerConnection) {
                        this.createOffer();
                    }
                    break;
                    
                case 'call_ended':
                    console.log('📞 Call ended by partner');
                    this.endCall();
                    break;
                    
                case 'signal_ack':
                    console.log('✅ Signal acknowledged');
                    break;
                    
                case 'pong':
                    // heartbeat response
                    break;
            }
        } catch (error) {
            console.error('❌ Error handling WebSocket message:', error);
        }
    },
    
    // Initialize WebRTC peer connection
    async initializeWebRTC() {
        try {
            this.state.peerConnection = new RTCPeerConnection(this.config);
            
            // Add local tracks
            this.state.localStream.getTracks().forEach(track => {
                this.state.peerConnection.addTrack(track, this.state.localStream);
            });
            
            // Handle incoming audio
            this.state.peerConnection.ontrack = (event) => {
                this.state.remoteStream = event.streams[0];
                const remoteAudio = document.getElementById('remoteAudio');
                
                if (remoteAudio) {
                    remoteAudio.srcObject = this.state.remoteStream;
                    remoteAudio.autoplay = true;
                    remoteAudio.playsInline = true;
                    
                    // Show active call screen
                    this.showActiveCallScreen();
                    
                    // Start timer
                    this.startCallTimer();
                    
                    // Mark user as joined
                    this.markUserJoined();
                }
            };
            
            // Handle ICE candidates
            this.state.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    console.log('🧊 ICE candidate generated:', event.candidate.type, event.candidate.protocol);
                    this.sendWebRTCSignal({
                        type: 'ice-candidate',
                        candidate: event.candidate,
                        to_user_id: this.state.partnerUser.id,
                        from_user_id: this.state.currentUser.id,
                        call_id: this.state.callId
                    });
                } else {
                    console.log('✅ ICE gathering complete');
                }
            };
            
            // Monitor ICE connection state (critical for debugging Render issues)
            this.state.peerConnection.oniceconnectionstatechange = () => {
                console.log('🧊 ICE connection state:', this.state.peerConnection.iceConnectionState);
            };
            
            // Monitor ICE candidate errors (reveals TURN/STUN failures)
            this.state.peerConnection.onicecandidateerror = (event) => {
                console.error('🧊 ICE candidate error:', event.errorCode, event.errorText, event.url);
            };
            
            // Monitor connection state
            this.state.peerConnection.onconnectionstatechange = () => {
                const state = this.state.peerConnection.connectionState;
                console.log('🔗 Connection state:', state);
                
                switch(state) {
                    case 'connected':
                        this.updateStatus('Call connected!', '🎉');
                        break;
                    case 'connecting':
                        this.updateStatus('Connecting...', '🔄');
                        break;
                    case 'disconnected':
                        this.updateStatus('Disconnected', '⚠️');
                        break;
                    case 'failed':
                        this.attemptReconnect();
                        break;
                }
            };
            
            console.log('✅ Peer connection initialized');
            
        } catch (error) {
            console.error('❌ Error initializing WebRTC:', error);
            throw error;
        }
    },
    
    // Create WebRTC offer
    async createOffer() {
        try {
            const offer = await this.state.peerConnection.createOffer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: false
            });
            
            await this.state.peerConnection.setLocalDescription(offer);
            
            this.sendWebRTCSignal({
                type: 'offer',
                offer: offer,
                to_user_id: this.state.partnerUser.id,
                from_user_id: this.state.currentUser.id,
                call_id: this.state.callId
            });
            
            console.log('✅ Offer created and sent');
            
        } catch (error) {
            console.error('❌ Error creating offer:', error);
            this.showError('Failed to start call. Please try again.', false);
        }
    },
    
    // Handle WebRTC signals (with ICE candidate buffering)
    async handleWebRTCSignal(signal) {
        try {
            if (!this.state.peerConnection) {
                // Buffer ICE candidates if peer connection isn't ready yet
                if (signal.type === 'ice-candidate' && signal.candidate) {
                    this.state.iceCandidateBuffer.push(signal.candidate);
                }
                return;
            }
            
            switch(signal.type) {
                case 'offer':
                    await this.state.peerConnection.setRemoteDescription(signal.offer);
                    this.state.remoteDescriptionSet = true;
                    
                    // Flush buffered ICE candidates
                    await this._processBufferedIceCandidates();
                    
                    const answer = await this.state.peerConnection.createAnswer();
                    await this.state.peerConnection.setLocalDescription(answer);
                    
                    this.sendWebRTCSignal({
                        type: 'answer',
                        answer: answer,
                        to_user_id: signal.from || signal.from_user_id,
                        from_user_id: this.state.currentUser.id,
                        call_id: signal.call_id || this.state.callId
                    });
                    break;
                    
                case 'answer':
                    await this.state.peerConnection.setRemoteDescription(signal.answer);
                    this.state.remoteDescriptionSet = true;
                    
                    // Flush buffered ICE candidates
                    await this._processBufferedIceCandidates();
                    break;
                    
                case 'ice-candidate':
                    if (!signal.candidate) return;
                    
                    // Buffer if remote description not set yet
                    if (!this.state.remoteDescriptionSet) {
                        console.log('⏳ Buffering ICE candidate (waiting for remote description)');
                        this.state.iceCandidateBuffer.push(signal.candidate);
                        return;
                    }
                    
                    try {
                        await this.state.peerConnection.addIceCandidate(
                            new RTCIceCandidate(signal.candidate)
                        );
                    } catch (e) {
                        console.warn('⚠️ Failed to add ICE candidate:', e.message);
                    }
                    break;
                    
                case 'call-end':
                    this.endCall();
                    break;
            }
            
        } catch (error) {
            console.error('❌ Error handling signal:', error);
        }
    },
    
    // Process buffered ICE candidates after remote description is set
    async _processBufferedIceCandidates() {
        if (this.state.iceCandidateBuffer.length === 0) return;
        
        console.log(`🧊 Processing ${this.state.iceCandidateBuffer.length} buffered ICE candidates`);
        for (const candidate of this.state.iceCandidateBuffer) {
            try {
                await this.state.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            } catch (e) {
                console.warn('⚠️ Failed to add buffered ICE candidate:', e.message);
            }
        }
        this.state.iceCandidateBuffer = [];
    },
    
    // Send WebRTC signal via WebSocket
    sendWebRTCSignal(signal) {
        // Ensure from_user_id is always present
        if (!signal.from_user_id && this.state.currentUser) {
            signal.from_user_id = this.state.currentUser.id;
        }
        
        if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
            this.state.ws.send(JSON.stringify({
                type: 'webrtc_signal',
                signal: signal
            }));
        } else {
            console.warn('⚠️ WebSocket not open, signal not sent:', signal.type);
        }
    },
    
    // Toggle mute
    toggleMute() {
        if (!this.state.localStream) return;
        
        const audioTracks = this.state.localStream.getAudioTracks();
        if (audioTracks.length > 0) {
            this.state.isMuted = !audioTracks[0].enabled;
            audioTracks[0].enabled = !this.state.isMuted;
            
            return this.state.isMuted;
        }
        return false;
    },
    
    // End call
    async endCall() {
        console.log('📞 Ending call...');
        
        const callId = this.state.callId;
        this.state.callId = null; // prevent WS reconnect
        
        // Stop heartbeat
        this._stopHeartbeat();
        
        // Stop timer
        if (this.state.callTimer) {
            clearInterval(this.state.callTimer);
            this.state.callTimer = null;
        }
        
        // Send call end signal
        if (this.state.ws && this.state.partnerUser) {
            this.sendWebRTCSignal({
                type: 'call-end',
                to_user_id: this.state.partnerUser.id,
                call_id: callId
            });
        }
        
        // Close connections
        if (this.state.ws) {
            this.state.ws.close();
            this.state.ws = null;
        }
        
        if (this.state.peerConnection) {
            this.state.peerConnection.close();
            this.state.peerConnection = null;
        }
        
        if (this.state.localStream) {
            this.state.localStream.getTracks().forEach(track => track.stop());
            this.state.localStream = null;
        }
        
        // Reset state
        this.state.remoteDescriptionSet = false;
        this.state.iceCandidateBuffer = [];
        this.state.partnerJoined = false;
        
        // Save call data
        if (this.state.callStartTime) {
            const duration = Math.floor((Date.now() - this.state.callStartTime) / 1000);
            await this.saveCallData(duration);
        }
        
        return callId;
    },
    
    // Save call data
    async saveCallData(duration) {
        try {
            const token = localStorage.getItem('token');
            await fetch(`${API_BASE_URL}/api/calls/end`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    call_id: this.state.callId,
                    duration_seconds: duration
                })
            });
        } catch (error) {
            console.error('❌ Error saving call data:', error);
        }
    },
    
    // Mark user as joined
    async markUserJoined() {
        try {
            const token = localStorage.getItem('token');
            await fetch(`${API_BASE_URL}/api/calls/mark-joined?call_id=${this.state.callId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error('❌ Error marking joined:', error);
        }
    },
    
    // Start call timer
    startCallTimer() {
        this.state.callStartTime = Date.now();
        const MAX_CALL_DURATION = 300; // 5 minutes in seconds
        
        this.state.callTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.state.callStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            
            const timerElement = document.getElementById('callTimer');
            if (timerElement) {
                timerElement.textContent = `${minutes}:${seconds}`;
                
                // Warn at 4 minutes (240 seconds)
                if (elapsed === 240) {
                    alert('⏰ You have 1 minute remaining! Free users have a 5-minute call limit.');
                }
                
                // End call at 5 minutes (300 seconds)
                if (elapsed >= MAX_CALL_DURATION) {
                    clearInterval(this.state.callTimer);
                    alert('⏱️ Call time limit reached (5 minutes).\n\nUpgrade to Premium for unlimited call duration!');
                    this.endCall();
                }
            }
        }, 1000);
    },
    
    // Show active call screen
    showActiveCallScreen() {
        // This should update your UI to show call is active
        console.log('🎉 Call is now active!');
    },
    
    // Update status
    updateStatus(message, emoji = '') {
        console.log(`📝 Status: ${message}`);
        // Update UI elements here
    },
    
    // Update UI
    updateUI() {
        if (this.state.partnerUser) {
            const partnerNameElement = document.getElementById('partnerName');
            const partnerAvatarElement = document.getElementById('partnerAvatar');
            
            if (partnerNameElement) {
                partnerNameElement.textContent = this.state.partnerUser.name;
            }
            
            if (partnerAvatarElement) {
                partnerAvatarElement.textContent = this.state.partnerUser.name?.charAt(0)?.toUpperCase() || '?';
            }
        }
    },
    
    // Show error
    showError(message, redirect = false) {
        console.error('❌ Error:', message);
        
        if (redirect) {
            setTimeout(() => {
                window.location.href = 'users.html';
            }, 3000);
        }
    },
    
    // Attempt reconnect - properly renegotiate
    attemptReconnect() {
        if (this.state.reconnectAttempts < this.state.maxReconnectAttempts) {
            this.state.reconnectAttempts++;
            console.log(`🔄 Reconnect attempt ${this.state.reconnectAttempts}`);
            
            setTimeout(() => {
                if (this.state.peerConnection && this.state.peerConnection.connectionState === 'failed') {
                    // Close old connection
                    this.state.peerConnection.close();
                    this.state.peerConnection = null;
                    
                    // Reset ICE state
                    this.state.remoteDescriptionSet = false;
                    this.state.iceCandidateBuffer = [];
                    
                    // Re-initialize and renegotiate
                    this.initializeWebRTC().then(() => {
                        if (this.state.isCaller) {
                            setTimeout(() => this.createOffer(), 1000);
                        }
                    }).catch(console.error);
                }
            }, 2000 * this.state.reconnectAttempts);
        }
    }
};

// Add this to your call.js file if you have one
function handleCallRejection(data) {
    console.log('❌ Call rejected while on call page');
    
    // Show rejection message
    const overlay = document.createElement('div');
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
    `;
    
    overlay.innerHTML = `
        <div style="background: white; padding: 40px; border-radius: 20px; text-align: center;">
            <div style="font-size: 80px; margin-bottom: 20px;">❌</div>
            <h2 style="color: #ef4444; margin-bottom: 15px;">Call Declined</h2>
            <p style="color: #666; margin-bottom: 30px;">
                ${data.message || 'The other person declined your call invitation'}
            </p>
            <button onclick="window.location.href = 'users.html'" 
                    style="background: #667eea; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 16px;">
                Return to Users Page
            </button>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Auto-redirect after 5 seconds
    setTimeout(() => {
        window.location.href = 'users.html';
    }, 5000);
}

// Export for use in HTML
window.CallManager = CallManager;