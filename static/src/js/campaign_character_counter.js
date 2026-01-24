/** @odoo-module **/

const COST_PER_SMS = 1.00;

function calculateSMSParts(length) {
    if (length === 0) return 0;
    if (length <= 160) return 1;
    return 1 + Math.ceil((length - 160) / 153);
}

document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver((mutations) => {
        const messageField = document.querySelector('textarea[name="message"]');
        if (messageField && !messageField.dataset.counterAttached) {
            attachCounterToField(messageField);
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

function attachCounterToField(messageField) {
    messageField.dataset.counterAttached = 'true';

    const updateCounter = () => {
        const length = messageField.value.length;
        const parts = calculateSMSParts(length);

        const recipientField = document.querySelector('[name="total_recipients"] span, [name="total_recipients"] input');
        let recipientCount = 0;
        
        if (recipientField) {
            if (recipientField.tagName === 'INPUT') {
                recipientCount = parseInt(recipientField.value) || 0;
            } else {
                recipientCount = parseInt(recipientField.innerText) || 0;
            }
        }

        const estimatedCost = parts * recipientCount * COST_PER_SMS;

        const charCountEl = document.getElementById('char_count');
        const partsEl = document.getElementById('sms_parts');
        const costEl = document.getElementById('estimated_cost');

        if (charCountEl) {
            charCountEl.innerText = length;
            updateColors(charCountEl, length);
        }

        if (partsEl) partsEl.innerText = parts;
        if (costEl) costEl.innerText = estimatedCost.toFixed(2);
    };

    messageField.addEventListener('input', updateCounter);
    messageField.addEventListener('change', updateCounter);
    
    updateCounter();
}

function updateColors(element, length) {
    const parent = element.parentElement;
    if (!parent) return;
    
    parent.classList.remove('text-success', 'text-warning', 'text-danger');
    
    if (length > 160) {
        parent.classList.add('text-warning');
    } else {
        parent.classList.add('text-success');
    }
}