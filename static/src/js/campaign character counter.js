/** @odoo-module **/
// static/src/js/campaign_character_counter.js - Real-time Character Counter

import { Component, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MAX_CHARS = 200;
const COST_PER_SMS = 1.00; // KES

function calculateSMSParts(length) {
    if (length === 0) return 0;
    if (length <= 160) return 1;
    // After 160 chars, each SMS is 153 chars (7 for concatenation)
    return 1 + Math.ceil((length - 160) / 153);
}

// Hook into form view rendering
document.addEventListener('DOMContentLoaded', function() {
    setupCharacterCounter();
});

function setupCharacterCounter() {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            const messageField = document.querySelector('textarea[name="message"]');
            if (messageField && !messageField.dataset.counterAttached) {
                attachCounterToField(messageField);
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

function attachCounterToField(messageField) {
    messageField.dataset.counterAttached = 'true';
    
    const updateCounter = () => {
        const length = messageField.value.length;
        const parts = calculateSMSParts(length);
        
        // Get recipient count from form
        const recipientCountEl = document.querySelector('[name="total_recipients"] input');
        const recipientCount = recipientCountEl ? parseInt(recipientCountEl.value) || 0 : 0;
        
        const estimatedCost = parts * recipientCount * COST_PER_SMS;
        
        // Update character count
        const charCountEl = document.getElementById('char_count');
        if (charCountEl) {
            charCountEl.textContent = length;
            
            // Warning colors
            if (length > MAX_CHARS) {
                charCountEl.parentElement.classList.add('text-danger');
                charCountEl.parentElement.classList.remove('text-warning', 'text-success');
            } else if (length > 160) {
                charCountEl.parentElement.classList.add('text-warning');
                charCountEl.parentElement.classList.remove('text-danger', 'text-success');
            } else {
                charCountEl.parentElement.classList.add('text-success');
                charCountEl.parentElement.classList.remove('text-danger', 'text-warning');
            }
        }
        
        // Update SMS parts
        const partsEl = document.getElementById('sms_parts');
        if (partsEl) {
            partsEl.textContent = parts;
        }
        
        // Update estimated cost
        const costEl = document.getElementById('estimated_cost');
        if (costEl) {
            costEl.textContent = estimatedCost.toFixed(2);
        }
        
        // Enforce 200 character limit
        if (length > MAX_CHARS) {
            messageField.value = messageField.value.substring(0, MAX_CHARS);
            
            // Show warning
            showWarning('Maximum 200 characters allowed');
        }
    };
    
    // Attach event listeners
    messageField.addEventListener('input', updateCounter);
    messageField.addEventListener('keyup', updateCounter);
    messageField.addEventListener('paste', () => setTimeout(updateCounter, 10));
    
    // Initial update
    updateCounter();
}

function showWarning(message) {
    // Use Odoo's notification system
    if (window.odoo && window.odoo.notification) {
        window.odoo.notification.add(message, {
            type: 'warning',
            sticky: false
        });
    } else {
        // Fallback to alert
        console.warn(message);
    }
}
