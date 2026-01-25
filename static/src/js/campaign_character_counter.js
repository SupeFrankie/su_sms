/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TextField } from "@web/views/fields/text/text_field";

export class SmsCampaignCharCounter extends TextField {
    setup() {
        super.setup();
        this.state = useState({
            count: this.props.record.data[this.props.name] ? this.props.record.data[this.props.name].length : 0,
            parts: 1,
            cost: 0.00
        });
    }

    get charCount() {
        const value = this.props.record.data[this.props.name] || '';
        return value.length;
    }

    get smsParts() {
        const length = this.charCount;
        if (length === 0) return 0;
        if (length <= 160) return 1;
        return Math.ceil(length / 153);
    }

    get estimatedCost() {
        const costPerSms = 0.80; // KES
        return (this.smsParts * costPerSms).toFixed(2);
    }

    _onInput(ev) {
        super._onInput(ev);
        
        // Update stats after parent processes input
        const length = ev.target.value.length;
        this.state.count = length;
        
        if (length === 0) {
            this.state.parts = 0;
        } else if (length <= 160) {
            this.state.parts = 1;
        } else {
            this.state.parts = Math.ceil(length / 153);
        }

        this.state.cost = (this.state.parts * 0.80).toFixed(2);
    }
}

SmsCampaignCharCounter.template = "su_sms.SmsCampaignCharCounter";

// Register the widget
registry.category("fields").add("sms_counter", SmsCampaignCharCounter);