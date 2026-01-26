/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TextField } from "@web/views/fields/text/text_field";
import { Component, useState } from "@odoo/owl";

// Extends the standard Text Field to add a counter
export class SMSLiveWidget extends TextField {
    setup() {
        super.setup();
        this.state = useState({
            charCount: this.props.record.data[this.props.name] ? this.props.record.data[this.props.name].length : 0,
            smsParts: 1
        });
    }

    onInput(ev) {
        // 1. Update Standard Odoo Field (so it saves)
        super.onInput(ev);

        // 2. Update Live Counter
        const text = ev.target.value;
        const len = text.length;
        this.state.charCount = len;
        
        // GSM Standard: 160 chars = 1 SMS. >160 chars = 153 chars per part.
        if (len <= 160) {
            this.state.smsParts = 1;
        } else {
            this.state.smsParts = Math.ceil(len / 153);
        }
    }
}

SMSLiveWidget.template = "su_sms.SMSLiveWidget";
SMSLiveWidget.supportedTypes = ["text"];

// Register the widget so we can use widget="sms_counter" in XML
registry.category("fields").add("sms_counter", SMSLiveWidget);