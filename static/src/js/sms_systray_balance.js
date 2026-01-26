/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class SMSBalanceSystray extends Component {
    static template = "su_sms.SMSBalanceSystray";
    
    setup() {
        this.orm = useService("orm");  // FIX: Changed from "rpc" to "orm"
        this.state = useState({ balance: "..." });

        onWillStart(async () => {
            await this.fetchBalance();
        });
    }

    async fetchBalance() {
        try {
            // FIX: Updated to Odoo 19 ORM syntax
            const result = await this.orm.call(
                "sms.gateway.configuration",
                "get_api_balance",
                []
            );
            this.state.balance = result || "0.00";
        } catch (e) {
            console.error("Failed to fetch SMS balance:", e);
            this.state.balance = "N/A";
        }
    }
}

export const systrayItem = {
    Component: SMSBalanceSystray,
};

registry.category("systray").add("sms_balance", systrayItem, { sequence: 100 });