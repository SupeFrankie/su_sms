from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SMSType(models.Model):
    _name = 'sms.type'
    _description = 'SMS Type Classification'
    _order = 'sequence, name'
    
    name = fields.Char(string='Type Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    
    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            existing = self.search([
                ('code', '=', record.code),
                ('id', '!=', record.id)
            ], limit=1)
            if existing:
                raise ValidationError(f'SMS Type code "{record.code}" must be unique!')