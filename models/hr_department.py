# models/hr_department.py 

from odoo import models, fields, api

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    
    short_name = fields.Char(string='Short Name')
    chart_code = fields.Char(string='Chart Code', default='SU')
    account_number = fields.Char(string='Account Number')
    object_code = fields.Char(string='Object Code')
    
    administrator_id = fields.Many2one(
        'res.users', 
        string='Department Administrator'
    )
    
    is_school = fields.Boolean(
        string='Is School/Faculty',
        default=False
    )
    
    sms_credit_balance = fields.Float(
        string='SMS Credit Balance (KES)',
        compute='_compute_sms_credit_balance'
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
        for dept in self:
            # Placeholder for Kuali integration
            dept.sms_credit_balance = 0.0
    
    def _compute_sms_statistics(self):
        today = fields.Date.today()
        current_month = str(today.month).zfill(2)
        current_year = str(today.year)
        
        for dept in self:
            expenditures = self.env['sms.department.expenditure'].search([
                ('department_id', '=', dept.id),
                ('month_sent', '=', current_month),
                ('year_sent', '=', current_year)
            ])
            
            dept.sms_sent_this_month = len(expenditures)
            dept.sms_cost_this_month = sum(expenditures.mapped('total_cost')) if expenditures else 0.0