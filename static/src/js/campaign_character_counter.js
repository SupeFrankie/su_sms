/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { CharField } from "@web/views/fields/char/char_field";

export class SmsCampaignCharCounter extends Component {
    setup() {
        this.state = useState({
            count: this.props.record.data[this.props.name] ? this.props.record.data[this.props.name].length : 0,
            parts: 1,
            cost: 0.00
        });
    }

    get maxLength() {
        return 1600; // Hard limit if you want one, otherwise ignore
    }

    onInput(ev) {
        // Update the field value in Odoo
        this.props.record.update({ [this.props.name]: ev.target.value });
        
        // Update local stats
        const length = ev.target.value.length;
        this.state.count = length;
        
        // Calculate parts (160 chars = 1 part, >160 = 153 chars per part)
        if (length === 0) {
            this.state.parts = 0;
        } else if (length <= 160) {
            this.state.parts = 1;
        } else {
            this.state.parts = Math.ceil(length / 153);
        }

        const costPerSms = 0.80; // KES
        this.state.cost = (this.state.parts * costPerSms).toFixed(2);
    }
}

SmsCampaignCharCounter.template = "su_sms.SmsCampaignCharCounter";
SmsCampaignCharCounter.props = {
    ...standardFieldProps,
};

// Register the widget as "sms_counter"
registry.category("fields").add("sms_counter", SmsCampaignCharCounter);