from odoo import models, api, _
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
        
        total_campaigns = Campaign.search_count([])
        campaigns_this_month = Campaign.search_count([
            ('create_date', '>=', f'{current_year}-{current_month:02d}-01')
        ])
        
        Recipient = self.env['sms.recipient']
        
        total_sent = Recipient.search_count([('status', '=', 'sent')])
        total_failed = Recipient.search_count([('status', '=', 'failed')])
        total_pending = Recipient.search_count([('status', '=', 'pending')])
        total_recipients = Recipient.search_count([])
        
        success_rate = (total_sent / total_recipients * 100) if total_recipients > 0 else 0
        
        all_campaigns = Campaign.search([])
        total_cost_all_time = sum(all_campaigns.mapped('total_cost'))
        
        campaigns_year = Campaign.search([
            ('create_date', '>=', f'{current_year}-01-01')
        ])
        cost_year = sum(campaigns_year.mapped('total_cost'))
        
        campaigns_month = Campaign.search([
            ('create_date', '>=', f'{current_year}-{current_month:02d}-01')
        ])
        cost_month = sum(campaigns_month.mapped('total_cost'))
        
        Contact = self.env['sms.contact']
        
        total_contacts = Contact.search_count([('active', '=', True)])
        opted_in = Contact.search_count([('opt_in', '=', True)])
        blacklisted = Contact.search_count([('blacklisted', '=', True)])
        
        students = Contact.search_count([('contact_type', '=', 'student')])
        staff = Contact.search_count([('contact_type', '=', 'staff')])
        external = Contact.search_count([('contact_type', '=', 'external')])
        
        Gateway = self.env['sms.gateway.configuration']
        
        active_gateways = Gateway.search_count([('active', '=', True)])
        default_gateway = Gateway.search([('is_default', '=', True)], limit=1)
        
        credit_balance = 0.0
        if default_gateway:
            try:
                credit_balance = default_gateway.get_current_balance()
            except Exception:
                credit_balance = 0.0
        
        recent_campaigns = Campaign.search([], order='create_date desc', limit=5)
        
        recent_activity = [{
            'id': c.id,
            'name': c.name,
            'type': c.sms_type_id.name,
            'date': c.create_date.strftime('%Y-%m-%d %H:%M'),
            'recipients': c.total_recipients,
            'sent': c.sent_count,
            'status': c.status,
        } for c in recent_campaigns]
        
        return {
            'total_campaigns': total_campaigns,
            'campaigns_this_month': campaigns_this_month,
            'total_sent': total_sent,
            'total_failed': total_failed,
            'total_pending': total_pending,
            'success_rate': round(success_rate, 2),
            'total_cost_all_time': round(total_cost_all_time, 2),
            'cost_year': round(cost_year, 2),
            'cost_month': round(cost_month, 2),
            'total_contacts': total_contacts,
            'opted_in': opted_in,
            'blacklisted': blacklisted,
            'students': students,
            'staff': staff,
            'external': external,
            'active_gateways': active_gateways,
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
                ('create_date', '>=', week_start.replace(hour=0, minute=0, second=0))
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
            sms_type = campaign.sms_type_id.name
            if sms_type not in chart_data:
                chart_data[sms_type] = {
                    'count': 0,
                    'sent': 0,
                    'cost': 0.0
                }
            
            chart_data[sms_type]['count'] += 1
            chart_data[sms_type]['sent'] += campaign.sent_count
            chart_data[sms_type]['cost'] += campaign.total_cost
        
        return chart_data