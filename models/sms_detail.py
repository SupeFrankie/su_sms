# models/sms_detail.py 

from odoo import models, fields, api

class SMSDetail(models.Model):
    _name = 'sms.detail'
    _description = 'SMS Recipient Detail'
    _order = 'create_date desc'
    
    message_id = fields.Many2one('sms.message', string='SMS Message', 
                                  required=True, ondelete='cascade', index=True)
    gateway_message_id = fields.Char(string='Gateway Message ID', 
                                      help='Message ID from SMS gateway')
    
    recipient_name = fields.Char(string='Recipient Name')
    recipient_number = fields.Char(string='Phone Number', required=True, index=True)
    
    cost = fields.Float(string='Cost', digits=(10, 2))
    
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', required=True, index=True)
    
    failure_reason = fields.Char(string='Failure Reason')
    sent_date = fields.Datetime(string='Sent Date')
    delivered_date = fields.Datetime(string='Delivered Date')
    
    sms_type = fields.Selection(related='message_id.sms_type', string='Type', store=True)
    department_id = fields.Many2one(related='message_id.department_id', 
                                     string='Department', store=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            number = vals.get('recipient_number', '')
            if number and not number.startswith('+'):
                if number.startswith('0'):
                    vals['recipient_number'] = '+254' + number[1:]
                elif number.startswith('254'):
                    vals['recipient_number'] = '+' + number
        return super().create(vals_list)
    
    def action_retry_send(self):
        for detail in self.filtered(lambda d: d.status in ['failed', 'rejected']):
            detail.status = 'pending'
        self.mapped('message_id')._send_sms()