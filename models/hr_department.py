# models/hr_department.py 

from odoo import models, fields, api

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    
    short_name = fields.Char(
        string='Short Name',
        help='Department abbreviation (e.g., ICTD)'
    )
    
    chart_code = fields.Char(
        string='Chart Code',
        default='SU',
        help='Financial chart code (Kuali)'
    )
    
    account_number = fields.Char(
        string='Account Number',
        help='Kuali account number for billing'
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
        help='Check if this department is a school/faculty'
    )
    
    # SMS-related fields
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
    
    @api.depends('account_number', 'object_code')
    def _compute_sms_credit_balance(self):
        """Compute SMS credit balance - would integrate with Kuali"""
        for dept in self:
            # Placeholder - would query Kuali system
            dept.sms_credit_balance = 0.0
    
    def _compute_sms_statistics(self):
        """Compute SMS statistics for current month"""
        for dept in self:
            # Query department expenditure view
            expenditure = self.env['sms.department.expenditure'].search([
                ('department_id', '=', dept.id),
                ('month_sent', '=', fields.Date.today().strftime('%m')),
                ('year_sent', '=', str(fields.Date.today().year))
            ])
            
            dept.sms_sent_this_month = len(expenditure)
            dept.sms_cost_this_month = sum(expenditure.mapped('credit_spent'))