from odoo import models, fields, api

class SMSType(models.Model):
    _name = 'sms.type'
    _description = 'SMS Type Classification'
    _order = 'sequence, name'
    
    name = fields.Char(string='Type Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'SMS Type code must be unique!')
    ]