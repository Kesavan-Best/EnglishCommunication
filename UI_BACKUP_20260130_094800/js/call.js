// call.js - WebRTC calling logic (separated from HTML)

const CallManager = {
    // Configuration
    config: {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            { urls: 'stun:stun2.l.google.com:19302' },
            { urls: 'stun:stun3.l.google.com:19302' },
            { urls: 'stun:stun4.l.google.com:19302' }
        ],
        sdpSemantics: 'unified-plan'
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
        maxReconnectAttempts: 3
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
            
            // If caller, create offer
            if (this.state.isCaller) {
                setTimeout(() => this.createOffer(), 1000);
            }
            
            this.updateStatus('Waiting for partner...', '⏳');
            
        } catch (error) {
            console.error('❌ Failed to start call:', error);
            this.showError(`Failed to start call: ${error.message}`, false);
        }
    },
    
    // Get local microphone stream
    async getLocalStream() {
        try {
            this.state.localStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
                video: false
            });
            
            console.log('✅ Microphone access granted');
            
        } catch (error) {
            console.error('❌ Microphone access denied:', error);
            throw new Error('Microphone access is required. Please allow microphone permissions.');
        }
    },
    
    // Connect to WebSocket signaling server
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/api/ws/${this.state.currentUser.id}`;
                
                console.log('🔌 Connecting to WebSocket:', wsUrl);
                
                this.state.ws = new WebSocket(wsUrl);
                
                this.state.ws.onopen = () => {
                    console.log('✅ WebSocket connected');
                    resolve();
                    
                    // Send join call message
                    this.state.ws.send(JSON.stringify({
                        type: 'join-call',
                        call_id: this.state.callId,
                        partner_id: this.state.partnerUser.id
                    }));
                };
                
                this.state.ws.onmessage = this.handleWebSocketMessage.bind(this);
                
                this.state.ws.onerror = (error) => {
                    reject(new Error('Failed to connect to signaling server'));
                };
                
                this.state.ws.onclose = () => {
                    console.log('🔌 WebSocket closed');
                };
                
            } catch (error) {
                reject(error);
            }
        });
    },
    
    // Handle WebSocket messages
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'webrtc-signal':
                    this.handleWebRTCSignal(data.signal);
                    break;
                    
                case 'partner_joined':
                    console.log('✅ Partner joined call');
                    break;
                    
                case 'signal_ack':
                    console.log('✅ Signal acknowledged');
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
                if (event.candidate && this.state.ws) {
                    this.sendWebRTCSignal({
                        type: 'ice-candidate',
                        candidate: event.candidate,
                        to_user_id: this.state.partnerUser.id,
                        call_id: this.state.callId
                    });
                }
            };
            
            // Monitor connection state
            this.state.peerConnection.onconnectionstatechange = () => {
                const state = this.state.peerConnection.connectionState;
                
                switch(state) {
                    case 'connected':
                        this.updateStatus('Call connected!', '🎉');
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
                call_id: this.state.callId
            });
            
            console.log('✅ Offer created and sent');
            
        } catch (error) {
            console.error('❌ Error creating offer:', error);
            this.showError('Failed to start call. Please try again.', false);
        }
    },
    
    // Handle WebRTC signals
    async handleWebRTCSignal(signal) {
        try {
            if (!this.state.peerConnection) return;
            
            switch(signal.type) {
                case 'offer':
                    await this.state.peerConnection.setRemoteDescription(
                        new RTCSessionDescription(signal.offer)
                    );
                    
                    const answer = await this.state.peerConnection.createAnswer();
                    await this.state.peerConnection.setLocalDescription(answer);
                    
                    this.sendWebRTCSignal({
                        type: 'answer',
                        answer: answer,
                        to_user_id: signal.from,
                        call_id: signal.call_id
                    });
                    break;
                    
                case 'answer':
                    await this.state.peerConnection.setRemoteDescription(
                        new RTCSessionDescription(signal.answer)
                    );
                    break;
                    
                case 'ice-candidate':
                    try {
                        await this.state.peerConnection.addIceCandidate(
                            new RTCIceCandidate(signal.candidate)
                        );
                    } catch (e) {
                        console.warn('⚠️ Failed to add ICE candidate:', e);
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
    
    // Send WebRTC signal
    sendWebRTCSignal(signal) {
        if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
            this.state.ws.send(JSON.stringify({
                type: 'webrtc-signal',
                signal: signal
            }));
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
                call_id: this.state.callId
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
        
        // Save call data
        if (this.state.callStartTime) {
            const duration = Math.floor((Date.now() - this.state.callStartTime) / 1000);
            await this.saveCallData(duration);
        }
        
        return this.state.callId;
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
        
        this.state.callTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.state.callStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            
            const timerElement = document.getElementById('callTimer');
            if (timerElement) {
                timerElement.textContent = `${minutes}:${seconds}`;
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
    
    // Attempt reconnect
    attemptReconnect() {
        if (this.state.reconnectAttempts < this.state.maxReconnectAttempts) {
            this.state.reconnectAttempts++;
            
            setTimeout(() => {
                if (this.state.peerConnection && this.state.peerConnection.connectionState === 'failed') {
                    this.initializeWebRTC().catch(console.error);
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