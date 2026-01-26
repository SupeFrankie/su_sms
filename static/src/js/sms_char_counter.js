/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { TextField } from "@web/views/fields/text/text_field";
import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class SMSCharCounter extends TextField {
    setup() {
        super.setup();
        this.state = useState({ 
            count: this.props.record.data[this.props.name] ? this.props.record.data[this.props.name].length : 0,
            parts: 1
        });
    }

    onInput(ev) {
        const val = ev.target.value;
        const length = val.length;
        const parts = length <= 160 ? 1 : Math.ceil(length / 153);
        
        this.state.count = length;
        this.state.parts = parts;
        
        // Call standard Odoo onInput to ensure value is saved eventually
        super.onInput(ev); 
    }
}

SMSCharCounter.template = "su_sms.SMSCharCounter";

registry.category("fields").add("sms_counter", SMSCharCounter);