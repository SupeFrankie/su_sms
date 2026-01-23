/** @odoo-module **/
// static/src/js/sms_sidebar.js - Sidebar JavaScript


// Global functions for template
window.toggleSMSSidebar = function() {
    const sidebar = document.getElementById('smsSidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
};

window.refreshCreditBalance = function() {
    loadCreditBalance(true);
};

// Load credit balance from backend
async function loadCreditBalance(forceRefresh = false) {
    const balanceEl = document.getElementById('smsCreditBalance');
    const badgeEl = document.getElementById('smsCreditBadge');
    
    if (!balanceEl) return;
    
    try {
        const response = await odoo.rpc('/sms/api/credit_balance', {
            force_refresh: forceRefresh
        });
        
        if (response.success) {
            const balance = response.balance;
            const formatted = `KES ${balance.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}`;
            
            balanceEl.textContent = formatted;
            
            // Add low balance indicator
            if (response.low_balance) {
                balanceEl.classList.add('low-balance');
                if (badgeEl) {
                    badgeEl.textContent = '!';
                    badgeEl.style.display = 'inline-block';
                }
            } else {
                balanceEl.classList.remove('low-balance');
                if (badgeEl) {
                    badgeEl.style.display = 'none';
                }
            }
        } else {
            balanceEl.textContent = 'Error loading balance';
        }
    } catch (error) {
        console.error('Failed to load SMS credit balance:', error);
        balanceEl.textContent = 'Error';
    }
}

// Load user profile data
async function loadUserProfile() {
    const nameEl = document.getElementById('smsUserName');
    const roleEl = document.getElementById('smsUserRole');
    const deptEl = document.getElementById('smsUserDept');
    
    if (!nameEl) return;
    
    try {
        const response = await odoo.rpc('/sms/api/user_profile', {});
        
        if (response.success) {
            nameEl.textContent = response.name;
            roleEl.textContent = response.role;
            deptEl.textContent = response.department;
            
            // Set body class for role-based visibility
            document.body.classList.add(`sms-user-${response.role_code}`);
        }
    } catch (error) {
        console.error('Failed to load user profile:', error);
    }
}

// Initialize sidebar on page load
document.addEventListener('DOMContentLoaded', function() {
    loadUserProfile();
    loadCreditBalance();
    
    // Refresh credit balance every 5 minutes (like PHP system on page load)
    setInterval(() => loadCreditBalance(false), 5 * 60 * 1000);
});