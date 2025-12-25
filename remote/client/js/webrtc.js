/**
 * Scry Remote - WebRTC Module
 * Handles screen capture and WebRTC streaming to server
 */

class WebRTCManager {
    constructor() {
        this.peerConnection = null;
        this.dataChannel = null;
        this.localStream = null;
        this.websocket = null;
        this.sessionId = null;

        this.isConnected = false;
        this.isStreaming = false;

        // Callbacks
        this.onStatusChange = null;
        this.onCommand = null;
        this.onError = null;

        // ICE configuration
        this.iceConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
            ]
        };
    }

    /**
     * Start screen sharing and connect to server
     */
    async startScreenShare() {
        try {
            // Request screen capture
            this.localStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: 'always',
                    displaySurface: 'monitor', // Prefer entire screen
                    frameRate: { ideal: 10, max: 15 }, // Lower framerate for efficiency
                },
                audio: false
            });

            // Handle stream ending (user clicks "Stop sharing")
            this.localStream.getVideoTracks()[0].addEventListener('ended', () => {
                this.stop();
            });

            // Connect via WebSocket for signaling
            await this.connectWebSocket();

            this._setStatus('connected');
            this.isStreaming = true;

            return true;

        } catch (error) {
            console.error('Screen share error:', error);
            this._handleError(error);
            return false;
        }
    }

    /**
     * Connect WebSocket for signaling
     */
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/rtc/ws`;

            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = async () => {
                console.log('WebSocket connected');

                // Authenticate
                const user = window.authManager?.getUser();
                this.websocket.send(JSON.stringify({
                    type: 'auth',
                    email: user?.email
                }));
            };

            this.websocket.onmessage = async (event) => {
                const msg = JSON.parse(event.data);
                await this._handleWebSocketMessage(msg, resolve, reject);
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.websocket.onclose = () => {
                console.log('WebSocket closed');
                this._setStatus('disconnected');
            };
        });
    }

    /**
     * Handle incoming WebSocket messages
     */
    async _handleWebSocketMessage(msg, resolve, reject) {
        switch (msg.type) {
            case 'auth_ok':
                this.sessionId = msg.session_id;
                console.log('Authenticated, session:', this.sessionId);

                // Now establish WebRTC connection
                await this._createPeerConnection();
                break;

            case 'answer':
                // Server's WebRTC answer
                await this.peerConnection.setRemoteDescription({
                    type: 'answer',
                    sdp: msg.sdp
                });
                console.log('Remote description set');
                this.isConnected = true;
                if (resolve) resolve();
                break;

            case 'ice':
                // ICE candidate from server
                if (msg.candidate) {
                    await this.peerConnection.addIceCandidate(msg.candidate);
                }
                break;

            case 'command':
                // Control command from server
                this._handleCommand(msg);
                break;

            case 'error':
                console.error('Server error:', msg.message);
                if (reject) reject(new Error(msg.message));
                break;

            case 'pong':
                // Keepalive response
                break;
        }
    }

    /**
     * Create WebRTC peer connection
     */
    async _createPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.iceConfig);

        // Add local stream tracks
        this.localStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.localStream);
        });

        // Create data channel for commands
        this.dataChannel = this.peerConnection.createDataChannel('commands', {
            ordered: true
        });

        this.dataChannel.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'command') {
                this._handleCommand(data);
            }
        };

        // ICE candidate handling
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate && this.websocket) {
                this.websocket.send(JSON.stringify({
                    type: 'ice',
                    candidate: event.candidate
                }));
            }
        };

        // Connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            console.log('Connection state:', this.peerConnection.connectionState);

            switch (this.peerConnection.connectionState) {
                case 'connected':
                    this._setStatus('connected');
                    break;
                case 'disconnected':
                case 'failed':
                case 'closed':
                    this._setStatus('disconnected');
                    break;
            }
        };

        // Create and send offer
        const offer = await this.peerConnection.createOffer();
        await this.peerConnection.setLocalDescription(offer);

        this.websocket.send(JSON.stringify({
            type: 'offer',
            sdp: offer.sdp
        }));

        console.log('Offer sent');
    }

    /**
     * Handle control command from server
     */
    _handleCommand(msg) {
        console.log('Received command:', msg);

        if (this.onCommand) {
            this.onCommand(msg);
        }
    }

    /**
     * Stop screen sharing and disconnect
     */
    async stop() {
        this.isStreaming = false;
        this.isConnected = false;

        // Stop local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        // Close data channel
        if (this.dataChannel) {
            this.dataChannel.close();
            this.dataChannel = null;
        }

        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        // Close WebSocket
        if (this.websocket) {
            // Notify server
            try {
                await fetch('/rtc/disconnect', {
                    method: 'POST',
                    credentials: 'include'
                });
            } catch (e) {
                // Ignore
            }

            this.websocket.close();
            this.websocket = null;
        }

        this._setStatus('disconnected');
    }

    /**
     * Get local video stream for preview
     */
    getLocalStream() {
        return this.localStream;
    }

    /**
     * Set status and trigger callback
     */
    _setStatus(status) {
        if (this.onStatusChange) {
            this.onStatusChange(status);
        }
    }

    /**
     * Handle errors
     */
    _handleError(error) {
        let message = 'Unknown error';

        if (error.name === 'NotAllowedError') {
            message = 'Screen sharing permission denied';
        } else if (error.name === 'NotFoundError') {
            message = 'No screen available for sharing';
        } else if (error.message) {
            message = error.message;
        }

        if (this.onError) {
            this.onError(message);
        }
    }

    /**
     * Send keepalive ping
     */
    ping() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({ type: 'ping' }));
        }
    }
}

// Export singleton instance
window.webrtcManager = new WebRTCManager();
