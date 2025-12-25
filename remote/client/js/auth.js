/**
 * Scry Remote - Authentication Module
 * Handles SSO authentication state and session management
 */

class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
    }

    /**
     * Initialize authentication state
     */
    async init() {
        try {
            const response = await fetch('/auth/check', {
                credentials: 'include'
            });
            const data = await response.json();

            this.isAuthenticated = data.authenticated;
            this.user = data.user;

            if (this.isAuthenticated && this.user) {
                this.updateUI();
            }

            return this.isAuthenticated;
        } catch (error) {
            console.error('Auth check failed:', error);
            return false;
        }
    }

    /**
     * Update UI with user information
     */
    updateUI() {
        if (!this.user) return;

        const avatar = document.getElementById('userAvatar');
        const name = document.getElementById('userName');

        if (avatar && this.user.picture) {
            avatar.src = this.user.picture;
            avatar.alt = this.user.name || 'User';
        }

        if (name) {
            name.textContent = this.user.name || this.user.email;
        }
    }

    /**
     * Redirect to login
     */
    login() {
        window.location.href = '/auth/login';
    }

    /**
     * Logout and redirect
     */
    async logout() {
        try {
            await fetch('/auth/logout', {
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        window.location.href = '/auth/login';
    }

    /**
     * Get current user
     */
    getUser() {
        return this.user;
    }
}

// Export singleton instance
window.authManager = new AuthManager();
