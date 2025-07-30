/**
 * Galaxy of Consequence - Datapad HUD JavaScript
 * Handles character profile display, updates, and interactive elements
 */

class DatapadHUD {
    constructor(apiBaseUrl = '') {
        this.apiBaseUrl = apiBaseUrl;
        this.currentUser = null;
        this.currentProfile = null;
        this.isLoading = false;
        this.updateInterval = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoUpdate();
    }
    
    setupEventListeners() {
        // Profile update buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('update-field-btn')) {
                this.handleFieldUpdate(e.target.dataset.field);
            }
            
            if (e.target.classList.contains('refresh-profile-btn')) {
                this.refreshProfile();
            }
            
            if (e.target.classList.contains('show-hud-btn')) {
                this.showDatapadHUD();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+H to show HUD
            if (e.ctrlKey && e.key === 'h') {
                e.preventDefault();
                this.showDatapadHUD();
            }
            
            // F5 to refresh profile
            if (e.key === 'F5' && e.target.closest('.datapad-container')) {
                e.preventDefault();
                this.refreshProfile();
            }
        });
        
        // Auto-save form inputs
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('auto-save')) {
                this.debounce(() => this.autoSaveField(e.target), 1000);
            }
        });
    }
    
    loadInitialData() {
        // Try to load user from URL params or localStorage
        const urlParams = new URLSearchParams(window.location.search);
        this.currentUser = urlParams.get('user') || localStorage.getItem('galaxy_user');
        
        if (this.currentUser) {
            this.loadUserProfile(this.currentUser);
        }
    }
    
    async loadUserProfile(username) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading('Loading character profile...');
        
        try {
            const response = await this.apiCall('GET', `/get_alignment?user=${encodeURIComponent(username)}`);
            
            if (response.user) {
                this.currentUser = username;
                this.currentProfile = response;
                localStorage.setItem('galaxy_user', username);
                
                // Also load additional profile data
                await this.loadAdditionalProfileData();
                
                this.renderDatapadHUD();
            } else {
                this.showError('Character profile not found');
            }
        } catch (error) {
            this.showError(`Failed to load profile: ${error.message}`);
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    async loadAdditionalProfileData() {
        try {
            // Load canvas data for additional character info
            const canvasResponse = await this.apiCall('GET', `/get_canvas?user=${encodeURIComponent(this.currentUser)}`);
            if (canvasResponse.data) {
                this.currentProfile.characterData = canvasResponse.data;
            }
            
            // Load faction relationships
            const sessionId = this.currentProfile.characterData?.session_id;
            if (sessionId) {
                const sessionResponse = await this.apiCall('GET', `/get_session_state?session_id=${encodeURIComponent(sessionId)}`);
                if (sessionResponse.galaxy_state) {
                    this.currentProfile.galaxyState = sessionResponse.galaxy_state;
                }
            }
        } catch (error) {
            console.warn('Failed to load additional profile data:', error);
        }
    }
    
    renderDatapadHUD() {
        if (!this.currentProfile) return;
        
        const container = this.getOrCreateDatapadContainer();
        const profile = this.currentProfile;
        const charData = profile.characterData || {};
        
        container.innerHTML = `
            <div class="datapad-header">
                <h2>[ PLAYER CHARACTER FILE ]</h2>
                <div class="profile-controls">
                    <button class="btn btn-sm refresh-profile-btn" title="Refresh Profile">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                </div>
            </div>
            
            <div class="datapad-section">
                <div class="datapad-field">
                    <span class="datapad-label">PC NAME</span>
                    <span class="datapad-value editable" data-field="name">
                        ${charData.name || '[Unknown]'}
                        <button class="update-field-btn" data-field="name">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">SPECIES</span>
                    <span class="datapad-value editable" data-field="species">
                        ${charData.species || '[Unknown]'}
                        <button class="update-field-btn" data-field="species">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">HOMEWORLD</span>
                    <span class="datapad-value editable" data-field="homeworld">
                        ${charData.homeworld || '[Unknown]'}
                        <button class="update-field-btn" data-field="homeworld">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">BACKGROUND</span>
                    <span class="datapad-value editable" data-field="background">
                        ${charData.background || '[Unknown]'}
                        <button class="update-field-btn" data-field="background">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">ALLEGIANCE</span>
                    <span class="datapad-value editable" data-field="allegiance">
                        ${charData.allegiance || '[Independent]'}
                        <button class="update-field-btn" data-field="allegiance">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">FORCE SENSITIVE</span>
                    <span class="datapad-value ${profile.force_sensitive ? 'force-light' : ''}">
                        ${profile.force_sensitive ? 'Yes' : 'No'}
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">FORCE ALIGNMENT</span>
                    <span class="datapad-value ${this.getAlignmentClass(profile.net_alignment)}">
                        ${profile.alignment_description}
                    </span>
                </div>
            </div>
            
            <div class="datapad-section">
                <h3>APPEARANCE</h3>
                <div class="datapad-field">
                    <span class="datapad-value editable" data-field="appearance">
                        ${charData.appearance || '[No description provided]'}
                        <button class="update-field-btn" data-field="appearance">✏️</button>
                    </span>
                </div>
            </div>
            
            <div class="datapad-section">
                <h3>EQUIPMENT LOADOUT</h3>
                <div class="datapad-field">
                    <span class="datapad-label">Primary Weapon</span>
                    <span class="datapad-value editable" data-field="primary_weapon">
                        ${charData.primary_weapon || '[None]'}
                        <button class="update-field-btn" data-field="primary_weapon">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">Secondary Weapon</span>
                    <span class="datapad-value editable" data-field="secondary_weapon">
                        ${charData.secondary_weapon || '[None]'}
                        <button class="update-field-btn" data-field="secondary_weapon">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">Armor / Clothing</span>
                    <span class="datapad-value editable" data-field="armor">
                        ${charData.armor || '[Basic clothing]'}
                        <button class="update-field-btn" data-field="armor">✏️</button>
                    </span>
                </div>
                
                <div class="datapad-field">
                    <span class="datapad-label">Special Items</span>
                    <span class="datapad-value editable" data-field="special_items">
                        ${charData.special_items || '[None]'}
                        <button class="update-field-btn" data-field="special_items">✏️</button>
                    </span>
                </div>
            </div>
            
            <div class="datapad-section">
                <h3>SKILLS & TRAITS</h3>
                <div class="datapad-field">
                    <span class="datapad-value editable" data-field="skills">
                        ${this.formatSkillsList(charData.skills)}
                        <button class="update-field-btn" data-field="skills">✏️</button>
                    </span>
                </div>
            </div>
            
            <div class="datapad-section">
                <h3>PERSONAL GOAL</h3>
                <div class="datapad-field">
                    <span class="datapad-value editable" data-field="goal">
                        ${charData.goal || '[No goal set]'}
                        <button class="update-field-btn" data-field="goal">✏️</button>
                    </span>
                </div>
            </div>
            
            <div class="datapad-section">
                <h3>FORCE ALIGNMENT METER</h3>
                <div class="force-meter">
                    <div class="force-meter-fill ${this.getAlignmentMeterClass(profile.net_alignment)}" 
                         style="width: ${this.getAlignmentMeterWidth(profile.net_alignment)}%">
                    </div>
                </div>
                <div class="datapad-field">
                    <span class="datapad-label">Light Side Points</span>
                    <span class="datapad-value force-light">${profile.light_side_points}</span>
                </div>
                <div class="datapad-field">
                    <span class="datapad-label">Dark Side Points</span>
                    <span class="datapad-value force-dark">${profile.dark_side_points}</span>
                </div>
                <div class="datapad-field">
                    <span class="datapad-label">Net Alignment</span>
                    <span class="datapad-value ${this.getAlignmentClass(profile.net_alignment)}">${profile.net_alignment}</span>
                </div>
                ${profile.corruption_level > 0 ? `
                    <div class="datapad-field">
                        <span class="datapad-label">Corruption Level</span>
                        <span class="datapad-value force-dark">${profile.corruption_level}%</span>
                    </div>
                ` : ''}
            </div>
            
            ${profile.force_powers && profile.force_powers.length > 0 ? `
                <div class="datapad-section">
                    <h3>FORCE POWERS</h3>
                    <div class="datapad-field">
                        <span class="datapad-value">
                            ${profile.force_powers.map(power => `<span class="force-power-tag">${power}</span>`).join(' ')}
                        </span>
                    </div>
                </div>
            ` : ''}
            
            ${this.renderFactionReputation()}
            
            <div class="datapad-section">
                <h3>CHARACTER IMAGE</h3>
                <div class="datapad-field">
                    <span class="datapad-value">
                        ${charData.character_image ? 
                            `<img src="${charData.character_image}" alt="Character Portrait" class="character-portrait">` :
                            '[No image uploaded]'
                        }
                        <button class="update-field-btn" data-field="character_image">🖼️</button>
                    </span>
                </div>
            </div>
            
            <div class="datapad-footer">
                <div class="profile-stats">
                    <span class="stat-item">Last Updated: ${new Date().toLocaleString()}</span>
                    ${profile.last_force_event ? `<span class="stat-item">Last Force Event: ${new Date(profile.last_force_event).toLocaleString()}</span>` : ''}
                </div>
            </div>
        `;
        
        this.addInteractiveElements(container);
    }
    
    renderFactionReputation() {
        if (!this.currentProfile.galaxyState) {
            return `
                <div class="datapad-section">
                    <h3>FACTION REPUTATION</h3>
                    <div class="datapad-field">
                        <span class="datapad-value">[Faction data unavailable]</span>
                    </div>
                </div>
            `;
        }
        
        const factions = [
            { name: 'Empire', key: 'empire', status: 'neutral' },
            { name: 'Rebel Alliance', key: 'rebellion', status: 'neutral' },
            { name: 'Hutt Cartel', key: 'hutts', status: 'neutral' },
            { name: 'CSA', key: 'csa', status: 'neutral' }
        ];
        
        return `
            <div class="datapad-section">
                <h3>FACTION REPUTATION</h3>
                ${factions.map(faction => `
                    <div class="datapad-field">
                        <span class="datapad-label">${faction.name}</span>
                        <span class="datapad-value">
                            <span class="faction-status ${faction.status}">${faction.status.toUpperCase()}</span>
                        </span>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    getOrCreateDatapadContainer() {
        let container = document.getElementById('datapad-hud');
        if (!container) {
            container = document.createElement('div');
            container.id = 'datapad-hud';
            container.className = 'datapad-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    getAlignmentClass(alignment) {
        if (alignment > 25) return 'force-light';
        if (alignment < -25) return 'force-dark';
        return 'force-balanced';
    }
    
    getAlignmentMeterClass(alignment) {
        if (alignment > 25) return 'light-side';
        if (alignment < -25) return 'dark-side';
        return 'balanced';
    }
    
    getAlignmentMeterWidth(alignment) {
        // Convert -100 to 100 scale to 0 to 100 percentage
        return Math.abs(alignment);
    }
    
    formatSkillsList(skills) {
        if (!skills) return '[No skills listed]';
        if (Array.isArray(skills)) {
            return skills.map(skill => `• ${skill}`).join('<br>');
        }
        return skills;
    }
    
    addInteractiveElements(container) {
        // Add CSS for force power tags
        const style = document.createElement('style');
        style.textContent = `
            .force-power-tag {
                display: inline-block;
                background: rgba(138, 43, 226, 0.3);
                border: 1px solid #8a2be2;
                border-radius: 12px;
                padding: 2px 8px;
                margin: 2px;
                font-size: 0.8rem;
                color: #8a2be2;
            }
            
            .character-portrait {
                max-width: 200px;
                max-height: 200px;
                border-radius: 10px;
                border: 2px solid var(--imperial-gold);
            }
            
            .profile-controls {
                position: absolute;
                top: 15px;
                right: 20px;
            }
            
            .update-field-btn {
                background: none;
                border: none;
                color: var(--rebel-blue);
                cursor: pointer;
                margin-left: 8px;
                opacity: 0.7;
                transition: opacity 0.3s ease;
            }
            
            .update-field-btn:hover {
                opacity: 1;
            }
            
            .editable:hover .update-field-btn {
                opacity: 1;
            }
            
            .profile-stats {
                display: flex;
                justify-content: space-between;
                flex-wrap: wrap;
                font-size: 0.8rem;
                color: #888;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid var(--carbon-freeze);
            }
            
            .stat-item {
                margin: 2px 0;
            }
        `;
        
        if (!document.getElementById('datapad-styles')) {
            style.id = 'datapad-styles';
            document.head.appendChild(style);
        }
    }
    
    async handleFieldUpdate(fieldName) {
        const currentValue = this.getCurrentFieldValue(fieldName);
        const newValue = prompt(`Enter new ${fieldName.replace('_', ' ')}:`, currentValue);
        
        if (newValue !== null && newValue !== currentValue) {
            await this.updateCharacterField(fieldName, newValue);
        }
    }
    
    getCurrentFieldValue(fieldName) {
        const charData = this.currentProfile.characterData || {};
        return charData[fieldName] || '';
    }
    
    async updateCharacterField(fieldName, newValue) {
        if (!this.currentUser) return;
        
        try {
            this.showLoading(`Updating ${fieldName}...`);
            
            // Update local data
            if (!this.currentProfile.characterData) {
                this.currentProfile.characterData = {};
            }
            this.currentProfile.characterData[fieldName] = newValue;
            
            // Save to canvas
            await this.saveCharacterData();
            
            // Re-render the updated field
            this.renderDatapadHUD();
            
            this.showSuccess(`${fieldName} updated successfully`);
        } catch (error) {
            this.showError(`Failed to update ${fieldName}: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }
    
    async saveCharacterData() {
        const payload = {
            user: this.currentUser,
            data: this.currentProfile.characterData || {},
            campaign: 'default',
            canvas: 'character_profile'
        };
        
        await this.apiCall('POST', '/save_canvas', payload);
    }
    
    async refreshProfile() {
        if (this.currentUser) {
            await this.loadUserProfile(this.currentUser);
            this.showSuccess('Profile refreshed');
        }
    }
    
    showDatapadHUD() {
        const container = document.getElementById('datapad-hud');
        if (container) {
            container.style.display = container.style.display === 'none' ? 'block' : 'none';
        } else if (this.currentUser) {
            this.loadUserProfile(this.currentUser);
        } else {
            const username = prompt('Enter character name to load profile:');
            if (username) {
                this.loadUserProfile(username);
            }
        }
    }
    
    startAutoUpdate() {
        // Auto-refresh profile every 5 minutes
        this.updateInterval = setInterval(() => {
            if (this.currentUser && !this.isLoading) {
                this.loadUserProfile(this.currentUser);
            }
        }, 5 * 60 * 1000);
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    // Utility Methods
    async apiCall(method, endpoint, data = null) {
        const url = this.apiBaseUrl + endpoint;
        const options = {
            method: method,
            headers: {
                'Authorization': 'Bearer Abracadabra',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    }
    
    showLoading(message = 'Loading...') {
        this.hideAllNotifications();
        const notification = this.createNotification('loading', message);
        document.body.appendChild(notification);
    }
    
    hideLoading() {
        const loading = document.getElementById('loading-notification');
        if (loading) {
            loading.remove();
        }
    }
    
    showSuccess(message) {
        this.hideAllNotifications();
        const notification = this.createNotification('success', message);
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }
    
    showError(message) {
        this.hideAllNotifications();
        const notification = this.createNotification('error', message);
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }
    
    createNotification(type, message) {
        const notification = document.createElement('div');
        notification.id = `${type}-notification`;
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            z-index: 10000;
            max-width: 400px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        `;
        
        switch (type) {
            case 'loading':
                notification.style.background = 'rgba(0, 102, 204, 0.9)';
                notification.innerHTML = `
                    <div style="display: flex; align-items: center;">
                        <div class="loading-spinner" style="margin-right: 10px;"></div>
                        ${message}
                    </div>
                `;
                break;
            case 'success':
                notification.style.background = 'rgba(0, 255, 0, 0.9)';
                notification.innerHTML = `✅ ${message}`;
                break;
            case 'error':
                notification.style.background = 'rgba(255, 68, 68, 0.9)';
                notification.innerHTML = `❌ ${message}`;
                break;
        }
        
        return notification;
    }
    
    hideAllNotifications() {
        const notifications = document.querySelectorAll('.notification');
        notifications.forEach(n => n.remove());
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    autoSaveField(input) {
        const fieldName = input.dataset.field;
        const newValue = input.value;
        
        if (fieldName && newValue !== this.getCurrentFieldValue(fieldName)) {
            this.updateCharacterField(fieldName, newValue);
        }
    }
}

// Initialize Datapad HUD when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.datapadHUD = new DatapadHUD();
    
    // Add global functions for easy access
    window.showHUD = () => window.datapadHUD.showDatapadHUD();
    window.refreshProfile = () => window.datapadHUD.refreshProfile();
    window.loadProfile = (username) => window.datapadHUD.loadUserProfile(username);
    
    // Add command prompt for testing
    console.log(`
🌌 Galaxy of Consequence Datapad HUD Loaded

Available commands:
- showHUD() - Show/hide character datapad
- refreshProfile() - Refresh current profile
- loadProfile(username) - Load specific character profile
- Ctrl+H - Toggle HUD display
- F5 (when HUD focused) - Refresh profile

May the Force be with you!
    `);
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatapadHUD;
}
