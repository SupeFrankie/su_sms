# models/sms_department.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SMSDepartment(models.Model):
    _name = 'sms.department'
    _description = 'SMS Billing Department'
    _order = 'name'
    
    name = fields.Char(string='Department Name', required=True)
    short_name = fields.Char(string='Short Name', required=True)
    chart_code = fields.Char(string='Chart Code', default='SU', required=True)
    account_number = fields.Char(string='Account Number', required=True, 
                                  help='KFS5 Financial Account for billing')
    object_code = fields.Char(string='Object Code', required=True,
                              help='KFS5 Budget object code')
    active = fields.Boolean(default=True)
    administrator_ids = fields.One2many('sms.administrator', 'department_id', 
                                        string='Administrators')
    
    total_spent = fields.Float(string='Total Credit Spent', compute='_compute_total_spent', 
                               store=True)
    message_count = fields.Integer(string='Messages Sent', compute='_compute_message_count')
    
    @api.constrains('short_name')
    def _check_unique_short_name(self):
        for record in self:
            existing = self.search([
                ('short_name', '=', record.short_name),
                ('id', '!=', record.id)
            ], limit=1)
            if existing:
                raise ValidationError(f'Department short name "{record.short_name}" must be unique!')
    
    @api.depends('administrator_ids.message_ids.total_cost')
    def _compute_total_spent(self):
        for dept in self:
            messages = self.env['sms.message'].search([('department_id', '=', dept.id)])
            dept.total_spent = sum(messages.mapped('total_cost'))
    
    def _compute_message_count(self):
        for dept in self:
            dept.message_count = self.env['sms.message'].search_count([
                ('department_id', '=', dept.id)
            ])