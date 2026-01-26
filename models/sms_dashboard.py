# models/sms_dashboard.py
from odoo import models, fields, api, _
from datetime import datetime

class SMSDashboard(models.Model):
    _name = 'sms.dashboard'
    _description = 'SMS System Dashboard'
    _auto = False  # This is a reporting model, not a database table

    # This model acts as a backend for the "Landing Page" KPIs
    
    @api.model
    def get_dashboard_stats(self):
        """Called by the Javascript Dashboard to fetch numbers."""
        
        # 1. Total Sent
        total_sent = self.env['sms.recipient'].search_count([('status', '=', 'sent')])
        
        # 2. Gender Breakdown (Assuming contacts are linked to hr.employee or students)
        # Note: This requires joining sms.contact with hr.employee/student data. 
        # Simplified example assuming we have gender on contacts:
        male_count = 0 # Placeholder logic
        female_count = 0 # Placeholder logic
        
        # 3. Financials
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Calculate costs from Campaigns
        campaigns_year = self.env['sms.campaign'].search([('create_date', '>=', f'{current_year}-01-01')])
        cost_year = sum(campaigns_year.mapped('total_cost'))
        
        campaigns_month = self.env['sms.campaign'].search([
            ('create_date', '>=', f'{current_year}-{current_month:02d}-01')
        ])
        cost_month = sum(campaigns_month.mapped('total_cost'))

        return {
            'total_sent': total_sent,
            'gender_data': {'male': male_count, 'female': female_count},
            'cost_year': cost_year,
            'cost_month': cost_month,
        }