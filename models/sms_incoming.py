# models/sms_incoming.py

from odoo import models, fields

class SmsIncomingMessage(models.Model):
    _name = 'sms.incoming.message'
    _description = 'Incoming SMS Messages'
    _order = 'received_date desc'
    
    phone_number = fields.Char(required=True, index=True)
    message = fields.Text(required=True)
    received_date = fields.Datetime(default=fields.Datetime.now, index=True)
    processed = fields.Boolean(default=False)