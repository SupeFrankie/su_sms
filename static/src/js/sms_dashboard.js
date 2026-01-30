/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SMSDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            stats: { campaigns: 0, sent: 0, cost: 0 }
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        // Simple search_count calls to populate stats
        const campaigns = await this.orm.searchCount("sms.campaign", []);
        const sent = await this.orm.searchCount("sms.recipient", [['status', '=', 'sent']]);
        
        // For cost, we need a search_read or a dedicated compute method
        // Keeping it simple/safe for now:
        this.state.stats = { campaigns, sent, cost: 0.0 }; 
    }

    openView(model, viewType) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: model,
            views: [[false, viewType], [false, 'form']],
            target: 'current',
        });
    }

    openAction(xmlId) {
        this.action.doAction(xmlId);
    }

    createCampaign() {
        this.openView('sms.campaign', 'form');
    }
    
    reload() {
        this.loadStats();
    }
}

SMSDashboard.template = "su_sms.dashboard_template";
registry.category("actions").add("sms_dashboard_client", SMSDashboard);