# models/sms_recipient.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class SmsRecipient(models.Model):
    _name = 'sms.recipient'
    _description = 'SMS Recipient'
    _order = 'create_date desc'

    campaign_id = fields.Many2one('sms.campaign', required=True, ondelete='cascade', index=True)
    name = fields.Char(required=True)
    phone_number = fields.Char(required=True, index=True)
    email = fields.Char()
    admission_number = fields.Char(index=True)
    staff_id = fields.Char(index=True)
    recipient_type = fields.Selection([
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('other', 'Other'),
    ], default='student', index=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], default='pending', index=True)
    personalized_message = fields.Text()
    sent_date = fields.Datetime()
    delivered_date = fields.Datetime()
    error_message = fields.Text()
    gateway_message_id = fields.Char(index=True)
    retry_count = fields.Integer(default=0)
    cost = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    department = fields.Char()
    year_of_study = fields.Char()

    @api.constrains('phone_number', 'campaign_id')
    def _check_unique_phone_campaign(self):
        for record in self:
            if not record.phone_number or not record.campaign_id:
                continue
            
            existing = self.search([
                ('phone_number', '=', record.phone_number),
                ('campaign_id', '=', record.campaign_id.id),
                ('id', '!=', record.id)
            ], limit=1)
            
            if existing:
                raise ValidationError(
                    f'Phone number {record.phone_number} already exists in this campaign.'
                )

    @api.model
    def _normalize_phone(self, phone):
        if not phone:
            return phone

        phone = re.sub(r'\s+', '', phone)

        if phone.startswith('+254'):
            return phone
        if phone.startswith('+'):
            return phone
        if phone.startswith('0'):
            return '+254' + phone[1:]
        if phone.startswith(('7', '1')):
            return '+254' + phone

        raise ValidationError(f'Invalid phone number format: {phone}')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('phone_number'):
                vals['phone_number'] = self._normalize_phone(vals['phone_number'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('phone_number'):
            vals['phone_number'] = self._normalize_phone(vals['phone_number'])
        return super().write(vals)