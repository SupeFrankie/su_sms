# models/sms_recipient.py

import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SmsRecipient(models.Model):
    _name = 'sms.recipient'
    _description = 'SMS Recipient'
    _order = 'create_date desc'

    campaign_id = fields.Many2one('sms.campaign', string='Campaign', required=True, ondelete='cascade', index=True)
    
    name = fields.Char(required=True)
    phone_number = fields.Char(string='Phone Number', required=True, index=True)
    email = fields.Char()
    
    # Student/Staff identifiers
    admission_number = fields.Char(index=True)
    staff_id = fields.Char(index=True)
    
    # Demographics
    gender = fields.Selection([
        ('all', 'All'),
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender', index=True)
    
    department = fields.Char(help='Department name', index=True)
    
    recipient_type = fields.Selection([
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('parent', 'Parent'),
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
    
    cost = fields.Monetary(currency_field='currency_id', help='SMS cost from gateway')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    
    year_of_study = fields.Char()

    @api.constrains('phone_number', 'campaign_id')
    def _check_unique_phone_campaign(self):
        """Ensure phone number is unique per campaign"""
        for record in self:
            if record.phone_number and record.campaign_id:
                existing = self.search([
                    ('phone_number', '=', record.phone_number),
                    ('campaign_id', '=', record.campaign_id.id),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(f'Phone number {record.phone_number} already exists in this campaign.')

    @api.model
    def normalize_phone(self, phone):
        """
        Normalize phone numbers to E.164 format with international support.
        
        Handles:
        - Kenyan: 0712345678 → +254712345678
        - Uganda: 0712345678 → +256712345678
        - Tanzania: 0712345678 → +255712345678
        - International: Already formatted numbers
        
        Args:
            phone (str): Raw phone number input
            
        Returns:
            str: E.164 formatted phone number
            
        Raises:
            ValidationError: If phone format is invalid
        """
        if not phone:
            return phone
        
        # Remove all whitespace, dashes, parentheses, dots
        phone = re.sub(r'[\s\-\(\)\.]', '', str(phone).strip())
        
        # Already in international format
        if phone.startswith('+'):
            # Validate E.164: + followed by 1-15 digits
            if re.match(r'^\+\d{1,15}$', phone):
                return phone
            else:
                raise ValidationError(f'Invalid international number format: {phone}')
        
        # Handle country-specific formatting
        
        # Kenya (254) - 10 digits after 0
        if phone.startswith('0') and len(phone) == 10:
            if phone[1] in '17':  # Kenyan mobile prefixes
                return '+254' + phone[1:]
        
        # Already has country code but missing +
        if phone.startswith('254') and len(phone) == 12:
            return '+' + phone
        if phone.startswith('256') and len(phone) == 12:  # Uganda
            return '+' + phone
        if phone.startswith('255') and len(phone) == 12:  # Tanzania
            return '+' + phone
        
        # 9-digit Kenyan numbers (missing leading 0)
        if len(phone) == 9 and phone[0] in '17':
            return '+254' + phone
        
        # US/Canada (1) - 10 digits
        if len(phone) == 10 and phone[0] in '2-9':
            return '+1' + phone
        
        # Generic international fallback - assume valid if 7-15 digits
        if re.match(r'^\d{7,15}$', phone):
            # Default to Kenya if ambiguous
            return '+254' + phone if len(phone) == 9 else '+' + phone
        
        raise ValidationError(
            f'Invalid phone number: {phone}\n'
            f'Supported formats:\n'
            f'• Kenyan: 0712345678, 712345678, 254712345678\n'
            f'• International: +1234567890, +447123456789\n'
            f'• Must be 7-15 digits (E.164 standard)'
        )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('phone_number'):
                vals['phone_number'] = self.normalize_phone(vals['phone_number'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('phone_number'):
            vals['phone_number'] = self.normalize_phone(vals['phone_number'])
        return super().write(vals)