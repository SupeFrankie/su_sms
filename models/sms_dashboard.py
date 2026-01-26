from odoo import models, api
from datetime import datetime, timedelta

class SMSDashboard(models.AbstractModel):
    _name = 'sms.dashboard'
    _description = 'SMS System Dashboard'

    @api.model
    def get_dashboard_stats(self):
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        Campaign = self.env['sms.campaign']
        Recipient = self.env['sms.recipient']
        
        total_sent = Recipient.search_count([('status', '=', 'sent')])
        total_failed = Recipient.search_count([('status', '=', 'failed')])
        total_pending = Recipient.search_count([('status', '=', 'pending')])
        total_recipients = Recipient.search_count([])
        
        total_campaigns = Campaign.search_count([])
        campaigns_this_month = Campaign.search_count([
            ('create_date', '>=', f'{current_year}-{current_month:02d}-01')
        ])
        
        success_rate = (total_sent / total_recipients * 100) if total_recipients > 0 else 0
        
        all_campaigns = Campaign.search([])
        total_cost_all_time = sum(all_campaigns.mapped('total_cost'))
        
        campaigns_year = Campaign.search([
            ('create_date', '>=', f'{current_year}-01-01')
        ])
        cost_year = sum(campaigns_year.mapped('total_cost'))
        
        recent_campaigns = Campaign.search([], limit=5, order='create_date desc')
        recent_activity = [{
            'id': c.id,
            'name': c.name,
            'status': c.status,
            'date': c.create_date.strftime('%Y-%m-%d %H:%M'),
            'cost': c.total_cost
        } for c in recent_campaigns]

        credit_balance = 0.0
        try:
            gateway = self.env['sms.gateway.configuration'].search([('is_default', '=', True)], limit=1)
        except Exception:
            pass

        return {
            'total_sent': total_sent,
            'total_failed': total_failed,
            'total_pending': total_pending,
            'success_rate': round(success_rate, 1),
            'total_campaigns': total_campaigns,
            'campaigns_month': campaigns_this_month,
            'total_cost': round(total_cost_all_time, 2),
            'cost_year': round(cost_year, 2),
            'credit_balance': round(credit_balance, 2),
            'recent_activity': recent_activity,
        }
    
    @api.model
    def get_campaign_chart_data(self, period='month'):
        Campaign = self.env['sms.campaign']
        now = datetime.now()
        
        if period == 'day':
            campaigns = Campaign.search([
                ('create_date', '>=', now.replace(hour=0, minute=0, second=0))
            ])
        elif period == 'week':
            week_start = now - timedelta(days=now.weekday())
            campaigns = Campaign.search([
                ('create_date', '>=', week_start)
            ])
        elif period == 'month':
            campaigns = Campaign.search([
                ('create_date', '>=', f'{now.year}-{now.month:02d}-01')
            ])
        else:
            campaigns = Campaign.search([
                ('create_date', '>=', f'{now.year}-01-01')
            ])
        
        chart_data = {}
        for campaign in campaigns:
            sms_type = campaign.sms_type_id.name or 'Unknown'
            if sms_type not in chart_data:
                chart_data[sms_type] = {'count': 0, 'sent': 0, 'cost': 0.0}
            
            chart_data[sms_type]['count'] += 1
            chart_data[sms_type]['sent'] += campaign.sent_count
            chart_data[sms_type]['cost'] += campaign.total_cost
            
        return chart_data