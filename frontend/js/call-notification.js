// call-notification.js - Global call notification handler
// Include this on ALL authenticated pages to receive call invites anywhere
(function() {
    'use strict';

    // Skip on login/register/call pages (they have their own handling)
    // Also skip on pages that already have full call notification handling
    var path = window.location.pathname;
    if (path.includes('login.html') || path.includes('register.html') || path.includes('call.html')) {
        return;
    }

    let _ws = null;
    let _heartbeat = null;
    let _pollInterval = null;
    let _userId = null;

    function init() {
        const token = localStorage.getItem('token');
        const userStr = localStorage.getItem('user');
        if (!token || !userStr) return;

        try {
            const user = JSON.parse(userStr);
            _userId = user.id;
            if (!_userId) return;
        } catch (e) {
            return;
        }

        // Start polling for pending call invites (cross-instance fallback)
        pollPendingInvites();
        _pollInterval = setInterval(pollPendingInvites, 1500);

        // Connect WebSocket for real-time notifications
        connectWS();
    }

    function connectWS() {
        if (!_userId) return;
        // Don't create duplicate connections if page already has WS (e.g. dashboard.js, users.js)
        if (window._globalCallWS) return;

        try {
            const wsUrl = (typeof WS_BASE_URL !== 'undefined' ? WS_BASE_URL : '') + '/api/ws/' + _userId;
            _ws = new WebSocket(wsUrl);
            window._globalCallWS = _ws;

            _ws.onopen = function() {
                console.log('[CallNotify] WS connected');
                if (_heartbeat) clearInterval(_heartbeat);
                _heartbeat = setInterval(function() {
                    if (_ws && _ws.readyState === WebSocket.OPEN) {
                        _ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 15000);
                _ws.send(JSON.stringify({ type: 'ping' }));
            };

            _ws.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);
                    if (data.type === 'call_invite' || data.type === 'call_invitation') {
                        showCallNotification(data.caller_name || 'Someone', data.call_id, data.from_user_id);
                    }
                } catch (e) { /* ignore */ }
            };

            _ws.onclose = function() {
                window._globalCallWS = null;
                if (_heartbeat) { clearInterval(_heartbeat); _heartbeat = null; }
                // Reconnect after 2s
                setTimeout(connectWS, 2000);
            };

            _ws.onerror = function() {
                // Will trigger onclose
            };
        } catch (e) {
            console.warn('[CallNotify] WS error:', e);
        }
    }

    function pollPendingInvites() {
        var token = localStorage.getItem('token');
        if (!token) return;
        // Don't poll if notification is already showing
        if (document.getElementById('incoming-call-notification')) return;

        fetch((typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : '') + '/api/calls/pending-invites', {
            headers: { 'Authorization': 'Bearer ' + token }
        })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (data && data.invites && data.invites.length > 0) {
                var invite = data.invites[0];
                if (!document.getElementById('incoming-call-notification')) {
                    showCallNotification(invite.caller_name, invite.call_id, invite.caller_id);
                    // Mark as seen
                    fetch((typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : '') + '/api/calls/mark-invite-seen?call_id=' + invite.call_id, {
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer ' + token }
                    }).catch(function() {});
                }
            }
        })
        .catch(function() {});
    }

    function showCallNotification(callerName, callId, fromUserId) {
        // Remove existing
        var existing = document.getElementById('incoming-call-notification');
        if (existing) existing.remove();

        var overlay = document.createElement('div');
        overlay.id = 'incoming-call-notification';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:99999;';

        overlay.innerHTML =
            '<div style="background:white;padding:40px;border-radius:20px;text-align:center;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,0.5);">' +
                '<div style="font-size:60px;margin-bottom:15px;">&#128222;</div>' +
                '<h2 style="margin:0 0 10px;color:#667eea;">Incoming Call</h2>' +
                '<p style="font-size:20px;margin:15px 0;font-weight:600;">' + callerName + '</p>' +
                '<p style="color:#666;margin-bottom:25px;">wants to practice English with you</p>' +
                '<div style="display:flex;gap:15px;justify-content:center;">' +
                    '<button id="gcn-accept" style="background:linear-gradient(135deg,#11998e,#38ef7d);color:white;border:none;padding:15px 40px;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;">Accept</button>' +
                    '<button id="gcn-decline" style="background:linear-gradient(135deg,#f093fb,#f5576c);color:white;border:none;padding:15px 40px;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;">Decline</button>' +
                '</div>' +
            '</div>';

        document.body.appendChild(overlay);

        // Play a short beep
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            var osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.frequency.value = 440;
            osc.connect(ctx.destination);
            osc.start();
            setTimeout(function() { osc.stop(); ctx.close(); }, 300);
        } catch (e) { /* ignore audio errors */ }

        document.getElementById('gcn-accept').onclick = function() {
            overlay.remove();
            // Send accept via WS
            var wsConn = _ws || window._globalCallWS;
            if (wsConn && wsConn.readyState === WebSocket.OPEN) {
                wsConn.send(JSON.stringify({
                    type: 'accept_call',
                    call_id: callId,
                    from_user_id: fromUserId
                }));
            }
            // Call accept API
            var token = localStorage.getItem('token');
            fetch((typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : '') + '/api/calls/accept', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
                body: JSON.stringify({ call_id: callId })
            }).catch(function() {});
            // Redirect to call page
            window.location.href = '/frontend/templates/call.html?callId=' + callId + '&autoStart=true';
        };

        document.getElementById('gcn-decline').onclick = function() {
            overlay.remove();
            // Send reject via WS
            var wsConn = _ws || window._globalCallWS;
            if (wsConn && wsConn.readyState === WebSocket.OPEN) {
                wsConn.send(JSON.stringify({
                    type: 'reject_call_invitation',
                    call_id: callId,
                    from_user_id: fromUserId
                }));
            }
            // Call reject API
            var token = localStorage.getItem('token');
            fetch((typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : '') + '/api/calls/reject', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
                body: JSON.stringify({ call_id: callId })
            }).catch(function() {});
        };

        // Auto-dismiss after 30 seconds
        setTimeout(function() {
            var el = document.getElementById('incoming-call-notification');
            if (el) el.remove();
        }, 30000);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
