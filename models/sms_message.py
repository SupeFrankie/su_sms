# models/sms_message.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SMSMessage(models.Model):
    _name = 'sms.message'
    _description = 'SMS Message'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Reference', required=True, copy=False, 
                       readonly=True, default='New')
    message = fields.Text(string='Message Content', required=True, tracking=True)
    
    sms_type = fields.Selection([
        ('adhoc', 'Ad Hoc SMS'),
        ('student', 'Student SMS'),
        ('staff', 'Staff SMS'),
        ('manual', 'Manual SMS'),
    ], string='SMS Type', required=True, tracking=True)
    
    administrator_id = fields.Many2one('sms.administrator', string='Sent By', 
                                       required=True, default=lambda self: self._get_current_admin(),
                                       tracking=True)
    department_id = fields.Many2one(related='administrator_id.department_id', 
                                    string='Department', store=True, readonly=True)
    
    detail_ids = fields.One2many('sms.detail', 'message_id', string='Recipient List')
    
    kfs5_processed = fields.Boolean(string='KFS5 Processed', default=False, tracking=True)
    kfs5_processed_date = fields.Datetime(string='KFS5 Process Date', readonly=True)
    
    total_cost = fields.Float(string='Total Cost', compute='_compute_totals', store=True)
    recipient_count = fields.Integer(string='Recipients', compute='_compute_totals', store=True)
    success_count = fields.Integer(string='Sent', compute='_compute_totals', store=True)
    failed_count = fields.Integer(string='Failed', compute='_compute_totals', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('partial', 'Partially Sent'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    gateway_id = fields.Many2one('sms.gateway.configuration', string='Gateway')
    
    
    @api.model
    def _get_current_admin(self):
        return self.env['sms.administrator'].search([
            ('user_id', '=', self.env.user.id)
        ], limit=1)
    
    @api.depends('detail_ids.cost', 'detail_ids.status')
    def _compute_totals(self):
        for msg in self:
            msg.recipient_count = len(msg.detail_ids)
            msg.total_cost = sum(msg.detail_ids.mapped('cost'))
            msg.success_count = len(msg.detail_ids.filtered(
                lambda d: d.status in ['sent', 'delivered']))
            msg.failed_count = len(msg.detail_ids.filtered(
                lambda d: d.status in ['failed', 'rejected']))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sms.message') or 'New'
        return super().create(vals_list)
    
    def action_send(self):
        for msg in self:
            if not msg.detail_ids:
                raise ValidationError('No recipients found. Please add recipients before sending.')
            msg.state = 'queued'
            msg._send_sms()
    
    def _send_sms(self):
        for msg in self:
            gateway = msg.gateway_id or self.env['sms.gateway.configuration'].search([], limit=1)
            if not gateway:
                raise ValidationError('No SMS gateway configured!')
            
            for detail in msg.detail_ids.filtered(lambda d: d.status == 'pending'):
                try:
                    result = gateway.send_sms(
                        phone_number=detail.recipient_number,
                        message=msg.message
                    )
                    detail.write({
                        'status': 'sent',
                        'gateway_message_id': result.get('message_id'),
                        'cost': result.get('cost', 0.0)
                    })
                except Exception as e:
                    detail.write({
                        'status': 'failed',
                        'failure_reason': str(e)
                    })
            
            msg._update_state()
    
    def _update_state(self):
        for msg in self:
            if all(d.status in ['sent', 'delivered'] for d in msg.detail_ids):
                msg.state = 'sent'
            elif all(d.status == 'failed' for d in msg.detail_ids):
                msg.state = 'failed'
            elif any(d.status in ['sent', 'delivered'] for d in msg.detail_ids):
                msg.state = 'partial'