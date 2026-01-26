/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class SMSBalanceSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({ balance: "..." });

        onWillStart(async () => {
            await this.fetchBalance();
        });
    }

    async fetchBalance() {
        try {
            // Calls a python method to get balance from API
            const result = await this.rpc("/web/dataset/call_kw/sms.gateway.configuration/get_api_balance", {
                model: "sms.gateway.configuration",
                method: "get_api_balance",
                args: [],
                kwargs: {},
            });
            this.state.balance = result;
        } catch (e) {
            this.state.balance = "Err";
        }
    }
}

SMSBalanceSystray.template = "su_sms.SMSBalanceSystray";

export const systrayItem = {
    Component: SMSBalanceSystray,
};

registry.category("systray").add("sms_balance", systrayItem, { sequence: 100 });