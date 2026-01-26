/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TextField } from "@web/views/fields/text/text_field";
import { useRef, useState, onMounted } from "@odoo/owl";

export class SMSLiveWidget extends TextField {
    setup() {
        super.setup();
        this.textareaRef = useRef("textarea");
        
        this.state = useState({
            charCount: 0,
            smsParts: 1
        });
        
        onMounted(() => {
            this.updateCounter();
        });
    }

    updateCounter() {
        const value = this.props.record.data[this.props.name] || "";
        const len = value.length;
        
        this.state.charCount = len;
        this.state.smsParts = len <= 160 ? 1 : Math.ceil(len / 153);
    }

    onChange(ev) {
        super.onChange(ev);
        this.updateCounter();
    }
}

SMSLiveWidget.template = "su_sms.SMSLiveWidget";
SMSLiveWidget.supportedTypes = ["text"];

registry.category("fields").add("sms_live_counter", SMSLiveWidget);