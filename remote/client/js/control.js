/**
 * Scry Remote - Control Module
 * Receives and executes control commands from server
 * Simulates mouse movements, clicks, and typing in the client's browser
 */

class ControlManager {
    constructor() {
        this.commandQueue = [];
        this.isExecuting = false;
        this.autoExecute = true;

        // Statistics
        this.commandsExecuted = 0;

        // Callbacks
        this.onCommandReceived = null;
        this.onCommandExecuted = null;
        this.onLog = null;
    }

    /**
     * Initialize control manager
     */
    init() {
        // Listen for commands from WebRTC
        if (window.webrtcManager) {
            window.webrtcManager.onCommand = (cmd) => this.handleCommand(cmd);
        }
    }

    /**
     * Handle incoming command
     */
    handleCommand(msg) {
        const command = {
            id: Date.now(),
            type: msg.action,
            data: msg.command,
            answer: msg.answer_text,
            question: msg.question,
            timestamp: new Date().toISOString(),
            executed: false
        };

        this.commandQueue.push(command);
        this._log('info', `Received ${command.type} command`);

        if (this.onCommandReceived) {
            this.onCommandReceived(command);
        }

        // Auto-execute if enabled
        if (this.autoExecute) {
            this.executeNext();
        }
    }

    /**
     * Execute next command in queue
     */
    async executeNext() {
        if (this.isExecuting) return;

        const command = this.commandQueue.find(c => !c.executed);
        if (!command) return;

        this.isExecuting = true;

        try {
            await this._executeCommand(command);
            command.executed = true;
            this.commandsExecuted++;

            this._log('success', `Executed: ${command.type}`);

            if (this.onCommandExecuted) {
                this.onCommandExecuted(command);
            }
        } catch (error) {
            this._log('error', `Command failed: ${error.message}`);
        }

        this.isExecuting = false;

        // Execute next if auto-execute is on
        if (this.autoExecute) {
            this.executeNext();
        }
    }

    /**
     * Execute all pending commands
     */
    async executeAll() {
        while (this.commandQueue.some(c => !c.executed)) {
            await this.executeNext();
        }
    }

    /**
     * Execute a single command
     */
    async _executeCommand(command) {
        const data = command.data;

        if (data.type === 'composite') {
            // Execute sequence of commands
            for (const subCmd of data.commands) {
                await this._executeSingleCommand(subCmd);
                await this._delay(data.delay_between_ms || 100);
            }
        } else {
            await this._executeSingleCommand(data);
        }
    }

    /**
     * Execute a single command (not composite)
     */
    async _executeSingleCommand(cmd) {
        switch (cmd.type) {
            case 'mouse_move':
                await this._moveMouse(cmd);
                break;

            case 'mouse_click':
                await this._mouseClick(cmd);
                break;

            case 'type_text':
                await this._typeText(cmd);
                break;

            case 'key_press':
                await this._keyPress(cmd);
                break;

            default:
                console.warn('Unknown command type:', cmd.type);
        }
    }

    /**
     * Simulate mouse movement
     * Note: Actual mouse control requires browser extension or native app
     * This shows visual feedback
     */
    async _moveMouse(cmd) {
        const x = cmd.x * window.screen.width;
        const y = cmd.y * window.screen.height;
        const duration = cmd.duration_ms || 500;

        this._log('info', `Moving mouse to (${Math.round(x)}, ${Math.round(y)})`);

        // Show visual indicator (for demo purposes)
        this._showMouseIndicator(x, y, duration);

        // In a real implementation, this would communicate with a native app
        // that has permission to control the mouse
        await this._delay(duration);
    }

    /**
     * Simulate mouse click
     */
    async _mouseClick(cmd) {
        const x = cmd.x * window.screen.width;
        const y = cmd.y * window.screen.height;

        if (cmd.move_first) {
            await this._moveMouse({
                x: cmd.x,
                y: cmd.y,
                duration_ms: cmd.duration_ms || 500
            });
        }

        this._log('info', `Clicking at (${Math.round(x)}, ${Math.round(y)})`);

        // Show click indicator
        this._showClickIndicator(x, y);

        // Simulate click via native interface
        await this._nativeClick(cmd.x, cmd.y, cmd.button || 'left');

        await this._delay(100);
    }

    /**
     * Simulate typing text
     */
    async _typeText(cmd) {
        const text = cmd.text;
        const wpmMin = cmd.wpm_min || 40;
        const wpmMax = cmd.wpm_max || 80;

        this._log('info', `Typing: "${text.substring(0, 50)}..."`);

        // Calculate delay per character
        const avgWpm = (wpmMin + wpmMax) / 2;
        const charsPerMinute = avgWpm * 5;
        const msPerChar = 60000 / charsPerMinute;

        // Type each character
        for (const char of text) {
            await this._nativeType(char);

            // Variable delay for human-like typing
            const delay = msPerChar * (0.5 + Math.random());
            await this._delay(delay);

            // Random pauses for "thinking"
            if (Math.random() < 0.02) {
                await this._delay(500 + Math.random() * 1000);
            }
        }
    }

    /**
     * Simulate key press
     */
    async _keyPress(cmd) {
        this._log('info', `Pressing key: ${cmd.key}`);

        await this._nativeKeyPress(cmd.key);
        await this._delay(50);
    }

    /**
     * Native click (via browser extension or native messaging)
     */
    async _nativeClick(x, y, button) {
        // Check if native interface is available
        if (window.scryNative) {
            await window.scryNative.click(x, y, button);
        } else {
            // Fallback: Try to use browser simulation
            console.log(`[SIMULATED] Click at (${x}, ${y}) with ${button} button`);

            // Note: True mouse control requires native code
            // This is a limitation of browser security
        }
    }

    /**
     * Native type (via browser extension or native messaging)
     */
    async _nativeType(char) {
        if (window.scryNative) {
            await window.scryNative.type(char);
        } else {
            // Fallback simulation
            console.log(`[SIMULATED] Type: ${char}`);
        }
    }

    /**
     * Native key press
     */
    async _nativeKeyPress(key) {
        if (window.scryNative) {
            await window.scryNative.keyPress(key);
        } else {
            console.log(`[SIMULATED] Key press: ${key}`);
        }
    }

    /**
     * Show visual mouse movement indicator
     */
    _showMouseIndicator(x, y, duration) {
        // Create or get indicator element
        let indicator = document.getElementById('mouseIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'mouseIndicator';
            indicator.style.cssText = `
                position: fixed;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: rgba(124, 58, 237, 0.5);
                border: 2px solid #7c3aed;
                pointer-events: none;
                z-index: 999999;
                transition: all ${duration}ms ease;
                transform: translate(-50%, -50%);
            `;
            document.body.appendChild(indicator);
        }

        // Move indicator
        indicator.style.left = `${x}px`;
        indicator.style.top = `${y}px`;
        indicator.style.opacity = '1';

        // Fade out after duration
        setTimeout(() => {
            indicator.style.opacity = '0';
        }, duration + 200);
    }

    /**
     * Show click indicator
     */
    _showClickIndicator(x, y) {
        const indicator = document.createElement('div');
        indicator.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            border: 3px solid #ef4444;
            pointer-events: none;
            z-index: 999999;
            transform: translate(-50%, -50%) scale(1);
            animation: clickPulse 0.5s ease forwards;
        `;

        // Add animation keyframes if not exists
        if (!document.getElementById('clickAnimStyle')) {
            const style = document.createElement('style');
            style.id = 'clickAnimStyle';
            style.textContent = `
                @keyframes clickPulse {
                    0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                    100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(indicator);

        // Remove after animation
        setTimeout(() => indicator.remove(), 500);
    }

    /**
     * Delay helper
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Log message
     */
    _log(level, message) {
        if (this.onLog) {
            this.onLog(level, message);
        }
        console.log(`[Control] ${level}: ${message}`);
    }

    /**
     * Set auto-execute mode
     */
    setAutoExecute(enabled) {
        this.autoExecute = enabled;
        if (enabled) {
            this.executeNext();
        }
    }

    /**
     * Get pending commands count
     */
    getPendingCount() {
        return this.commandQueue.filter(c => !c.executed).length;
    }

    /**
     * Clear executed commands from queue
     */
    clearExecuted() {
        this.commandQueue = this.commandQueue.filter(c => !c.executed);
    }

    /**
     * Get statistics
     */
    getStats() {
        return {
            executed: this.commandsExecuted,
            pending: this.getPendingCount(),
            total: this.commandQueue.length
        };
    }
}

// Export singleton instance
window.controlManager = new ControlManager();
