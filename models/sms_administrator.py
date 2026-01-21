# models/sms_administrator.py (accounts for who can send sms from where to where)
from odoo import models, fields, api

class SMSAdministrator(models.Model):
    _name = 'sms.administrator'
    _description = 'SMS Administrator'
    _inherits = {'res.users': 'user_id'}
    
    user_id = fields.Many2one('res.users', string='User', required=True, 
                              ondelete='cascade', index=True)
    department_id = fields.Many2one('sms.department', string='Finance Department', 
                                    required=True, ondelete='restrict')
    phone = fields.Char(string='Phone Number', 
                        help='Administrator phone (receives copy of sent SMS)')
    active = fields.Boolean(default=True)
    
    message_ids = fields.One2many('sms.message', 'administrator_id', string='Sent Messages')
    total_messages = fields.Integer(string='Total Messages', compute='_compute_totals')
    total_spent = fields.Float(string='Total Spent', compute='_compute_totals')
    
    name = fields.Char(related='user_id.name', string='Name', store=True, readonly=True)
    email = fields.Char(related='user_id.email', string='Email', readonly=True)
    
    _sql_constraints = [
        ('user_unique', 'unique(user_id)', 'A user can only have one SMS administrator record!')
    ]
    
    @api.depends('message_ids')
    def _compute_totals(self):
        for admin in self:
            admin.total_messages = len(admin.message_ids)
            admin.total_spent = sum(admin.message_ids.mapped('total_cost'))
    
    def action_view_messages(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'SMS Messages',
            'res_model': 'sms.message',
            'view_mode': 'tree,form',
            'domain': [('administrator_id', '=', self.id)],
            'context': {'default_administrator_id': self.id}
        }