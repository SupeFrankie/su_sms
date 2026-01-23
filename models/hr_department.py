# models/hr_department.py 

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    
    # Basic SMS Fields
    short_name = fields.Char(
        string='Short Name',
        help='Department abbreviation (e.g., ICTD)',
        index=True
    )
    
    # KFS5 Billing Fields
    chart_code = fields.Char(
        string='Chart Code',
        default='SU',
        help='Financial chart code (Kuali)'
    )
    
    account_number = fields.Char(
        string='Account Number',
        help='Kuali account number for billing',
        index=True
    )
    
    object_code = fields.Char(
        string='Object Code',
        help='Kuali object code for SMS billing'
    )
    
    administrator_id = fields.Many2one(
        'res.users',
        string='Department Administrator',
        help='Primary administrator for this department'
    )
    
    is_school = fields.Boolean(
        string='Is School/Faculty',
        default=False,
        help='Check if this department is a school/faculty',
        index=True
    )
    
    # SMS Statistics (Computed)
    sms_credit_balance = fields.Float(
        string='SMS Credit Balance (KES)',
        compute='_compute_sms_credit_balance',
        help='Current SMS credit balance for this department'
    )
    
    sms_sent_this_month = fields.Integer(
        string='SMS Sent This Month',
        compute='_compute_sms_statistics'
    )
    
    sms_cost_this_month = fields.Float(
        string='SMS Cost This Month (KES)',
        compute='_compute_sms_statistics'
    )
    
    total_sms_sent = fields.Integer(
        string='Total SMS Sent',
        compute='_compute_total_sms'
    )
    
    total_sms_cost = fields.Float(
        string='Total SMS Cost (KES)',
        compute='_compute_total_sms'
    )
    
    @api.constrains('short_name')
    def _check_unique_short_name(self):
        for dept in self:
            if dept.short_name:
                existing = self.search([
                    ('short_name', '=', dept.short_name),
                    ('id', '!=', dept.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _('Department short name "%s" must be unique!') % dept.short_name
                    )
    
    @api.depends('account_number', 'object_code')
    def _compute_sms_credit_balance(self):
        """
        Compute SMS credit balance
        In production, this would query KFS5 system
        For now, return 0 as placeholder
        """
        for dept in self:
            dept.sms_credit_balance = 0.0
    
    def _compute_sms_statistics(self):
        """Compute SMS statistics for current month"""
        Campaign = self.env['sms.campaign']
        today = fields.Date.today()
        
        for dept in self:
            # Get campaigns from users in this department
            campaigns = Campaign.search([
                ('administrator_id.department_id', '=', dept.id),
                ('create_date', '>=', today.replace(day=1)),
                ('create_date', '<=', today)
            ])
            
            dept.sms_sent_this_month = sum(campaigns.mapped('sent_count'))
            dept.sms_cost_this_month = sum(campaigns.mapped('total_cost'))
    
    def _compute_total_sms(self):
        """Compute total SMS sent by department"""
        Campaign = self.env['sms.campaign']
        
        for dept in self:
            campaigns = Campaign.search([
                ('administrator_id.department_id', '=', dept.id)
            ])
            
            dept.total_sms_sent = sum(campaigns.mapped('sent_count'))
            dept.total_sms_cost = sum(campaigns.mapped('total_cost'))
    
    def action_view_sms_campaigns(self):
        """View all SMS campaigns from this department"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Campaigns - %s') % self.name,
            'res_model': 'sms.campaign',
            'view_mode': 'list,form',
            'domain': [('administrator_id.department_id', '=', self.id)],
            'context': {'default_administrator_id': self.env.user.id}
        }