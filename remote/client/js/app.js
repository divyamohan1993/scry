/**
 * Scry Remote - Main Application
 * Coordinates all modules and handles UI interactions
 */

class ScryRemoteApp {
    constructor() {
        // Managers
        this.auth = window.authManager;
        this.webrtc = window.webrtcManager;
        this.control = window.controlManager;

        // Statistics
        this.stats = {
            framesProcessed: 0,
            commandsSent: 0,
            latency: '--'
        };

        // Keepalive interval
        this.keepaliveInterval = null;
        this.statsInterval = null;
    }

    /**
     * Initialize the application
     */
    async init() {
        // Check authentication
        const isAuth = await this.auth.init();
        if (!isAuth) {
            // Will be redirected by server
            return;
        }

        // Setup control manager
        this.control.init();

        // Bind UI events
        this._bindEvents();

        // Setup callbacks
        this._setupCallbacks();

        // Log ready
        this._log('info', 'Scry Remote ready');
    }

    /**
     * Bind UI event listeners
     */
    _bindEvents() {
        // Start button
        const startBtn = document.getElementById('startBtn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startSession());
        }

        // Stop button
        const stopBtn = document.getElementById('stopBtn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopSession());
        }

        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.auth.logout());
        }

        // Clear log button
        const clearLogBtn = document.getElementById('clearLogBtn');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => this._clearLog());
        }

        // Auto-execute checkbox
        const autoExecute = document.getElementById('autoExecute');
        if (autoExecute) {
            autoExecute.addEventListener('change', (e) => {
                this.control.setAutoExecute(e.target.checked);
            });
        }

        // Execute all button
        const executeAllBtn = document.getElementById('executeAllBtn');
        if (executeAllBtn) {
            executeAllBtn.addEventListener('click', () => this.control.executeAll());
        }
    }

    /**
     * Setup manager callbacks
     */
    _setupCallbacks() {
        // WebRTC status changes
        this.webrtc.onStatusChange = (status) => {
            this._updateStatus(status);
        };

        // WebRTC errors
        this.webrtc.onError = (message) => {
            this._log('error', message);
        };

        // Control manager logs
        this.control.onLog = (level, message) => {
            this._log(level, message);
        };

        // Command received
        this.control.onCommandReceived = (cmd) => {
            this._addCommandToQueue(cmd);
        };

        // Command executed
        this.control.onCommandExecuted = (cmd) => {
            this._markCommandExecuted(cmd.id);
            this._updateStats();
        };
    }

    /**
     * Start screen sharing session
     */
    async startSession() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');

        startBtn.disabled = true;
        this._updateStatus('connecting');
        this._log('info', 'Starting screen share...');

        const success = await this.webrtc.startScreenShare();

        if (success) {
            startBtn.disabled = true;
            stopBtn.disabled = false;

            // Show preview
            this._showPreview(this.webrtc.getLocalStream());

            // Start keepalive
            this._startKeepalive();

            // Start stats polling
            this._startStatsPolling();

            this._log('success', 'Screen sharing active');
        } else {
            startBtn.disabled = false;
            this._log('error', 'Failed to start screen share');
        }
    }

    /**
     * Stop screen sharing session
     */
    async stopSession() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');

        await this.webrtc.stop();

        startBtn.disabled = false;
        stopBtn.disabled = true;

        this._hidePreview();
        this._stopKeepalive();
        this._stopStatsPolling();

        this._log('info', 'Screen sharing stopped');
    }

    /**
     * Update connection status UI
     */
    _updateStatus(status) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const statusDot = indicator?.querySelector('.status-dot');

        if (!indicator || !statusText || !statusDot) return;

        // Remove all status classes
        statusDot.classList.remove('disconnected', 'connecting', 'connected');

        switch (status) {
            case 'connected':
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
                break;
            case 'connecting':
                statusDot.classList.add('connecting');
                statusText.textContent = 'Connecting...';
                break;
            case 'disconnected':
            default:
                statusDot.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                break;
        }
    }

    /**
     * Show video preview
     */
    _showPreview(stream) {
        const video = document.getElementById('previewVideo');
        const overlay = document.getElementById('previewOverlay');

        if (video && stream) {
            video.srcObject = stream;
        }

        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    /**
     * Hide video preview
     */
    _hidePreview() {
        const video = document.getElementById('previewVideo');
        const overlay = document.getElementById('previewOverlay');

        if (video) {
            video.srcObject = null;
        }

        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    /**
     * Add log entry
     */
    _log(level, message) {
        const log = document.getElementById('activityLog');
        if (!log) return;

        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry log-${level}`;
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-message">${message}</span>
        `;

        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;

        // Limit log entries
        while (log.children.length > 100) {
            log.removeChild(log.firstChild);
        }
    }

    /**
     * Clear activity log
     */
    _clearLog() {
        const log = document.getElementById('activityLog');
        if (log) {
            log.innerHTML = '';
            this._log('info', 'Log cleared');
        }
    }

    /**
     * Add command to UI queue
     */
    _addCommandToQueue(cmd) {
        const queue = document.getElementById('commandQueue');
        if (!queue) return;

        // Remove empty state
        const emptyState = queue.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const item = document.createElement('div');
        item.className = 'command-item';
        item.id = `cmd-${cmd.id}`;
        item.innerHTML = `
            <div>
                <span class="command-type">${cmd.type.toUpperCase()}</span>
                <span class="command-detail">${cmd.answer?.substring(0, 30) || '...'}</span>
            </div>
            <span class="command-status">Pending</span>
        `;

        queue.appendChild(item);

        // Enable execute all button
        document.getElementById('executeAllBtn').disabled = false;
    }

    /**
     * Mark command as executed in UI
     */
    _markCommandExecuted(cmdId) {
        const item = document.getElementById(`cmd-${cmdId}`);
        if (item) {
            item.style.opacity = '0.5';
            const status = item.querySelector('.command-status');
            if (status) {
                status.textContent = 'Done';
                status.style.color = 'var(--color-success)';
            }

            // Remove after animation
            setTimeout(() => item.remove(), 2000);
        }

        // Disable execute all if no pending
        if (this.control.getPendingCount() === 0) {
            document.getElementById('executeAllBtn').disabled = true;

            // Show empty state
            const queue = document.getElementById('commandQueue');
            if (queue && !queue.querySelector('.empty-state')) {
                queue.innerHTML = '<div class="empty-state"><span>No pending commands</span></div>';
            }
        }
    }

    /**
     * Update statistics display
     */
    _updateStats() {
        const stats = this.control.getStats();

        document.getElementById('commandsSent').textContent = stats.executed;
    }

    /**
     * Start keepalive pings
     */
    _startKeepalive() {
        this.keepaliveInterval = setInterval(() => {
            this.webrtc.ping();
        }, 30000); // Every 30 seconds
    }

    /**
     * Stop keepalive
     */
    _stopKeepalive() {
        if (this.keepaliveInterval) {
            clearInterval(this.keepaliveInterval);
            this.keepaliveInterval = null;
        }
    }

    /**
     * Start polling server for stats
     */
    _startStatsPolling() {
        this.statsInterval = setInterval(async () => {
            try {
                const response = await fetch('/control/status', {
                    credentials: 'include'
                });
                const data = await response.json();

                if (data.connected) {
                    document.getElementById('framesProcessed').textContent =
                        data.frames_processed || 0;
                }
            } catch (e) {
                // Ignore errors
            }
        }, 2000); // Every 2 seconds
    }

    /**
     * Stop stats polling
     */
    _stopStatsPolling() {
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
            this.statsInterval = null;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ScryRemoteApp();
    window.app.init();
});
