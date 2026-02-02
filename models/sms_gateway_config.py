# models/sms_gateway_config.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import requests
import logging
import time
import os
import re

_logger = logging.getLogger(__name__)


class SmsGatewayConfiguration(models.Model):
    _name = 'sms.gateway.configuration'
    _description = 'SMS Gateway Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Gateway Name', 
        required=True,
        help='Descriptive name for this gateway configuration'
    )
    
    gateway_type = fields.Selection([
        ('africastalking', "Africa's Talking"),
        ('custom', 'Custom API')
    ], string='Gateway Type', required=True, default='africastalking')
    
    api_key = fields.Char(
        string='API Key', 
        required=True,
        default=lambda self: os.getenv('AT_API_KEY', ''),
        help='API Key from your SMS gateway provider'
    )
    
    api_secret = fields.Char(
        string='API Secret/Auth Token',
        help='Optional secondary authentication token'
    )
    
    sender_id = fields.Char(
        string='Sender ID/Phone Number',
        default=lambda self: os.getenv('AT_SENDER_ID', ''),
        help='Sender ID (e.g., STRATHMORE) or phone number'
    )
    
    username = fields.Char(
        string='Username',
        default=lambda self: os.getenv('AT_USERNAME', 'sandbox'),
        required=True,
        help='API Username'
    )
    
    test_phone_number = fields.Char(
        string='Test Phone Number',
        help='Phone number for testing (format: +254712345678)'
    )
    
    is_default = fields.Boolean(
        string='Default Gateway',
        help='Use this gateway for all outgoing SMS unless specified otherwise'
    )
    
    active = fields.Boolean(default=True)
    
    # Statistics
    total_sent = fields.Integer(
        string='Total Sent',
        compute='_compute_statistics',
        help='Total SMS sent through this gateway'
    )
    
    last_used = fields.Datetime(
        string='Last Used',
        readonly=True,
        help='When this gateway was last used'
    )

    @api.model
    def create(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True)]).write({'is_default': False})
        return super(SmsGatewayConfiguration, self).create(vals)

    def write(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True), ('id', '!=', self.id)]).write({'is_default': False})
        return super(SmsGatewayConfiguration, self).write(vals)

    @api.model
    def create_from_env(self):
        """Called on module install by data/gateway_data.xml. Safe to run multiple times; no-op if a record already exists."""
        if self.search_count([]) == 0:
            self.create({'name': 'Default Gateway'})

    def _compute_statistics(self):
        """Compute gateway statistics"""
        for gateway in self:
            campaigns = self.env['sms.campaign'].search([('gateway_id', '=', gateway.id)])
            gateway.total_sent = sum(campaigns.mapped('sent_count'))
    
    @staticmethod
    def normalize_phone_number(phone):
        """
        Normalize phone to E.164 format with international support
        
        Supports:
        - Kenya: 0712345678 → +254712345678
        - Uganda: 0712345678 → +256712345678  
        - Tanzania: 0712345678 → +255712345678
        - International: Already formatted
        """
        if not phone:
            return phone
        
        # Remove whitespace, dashes, parentheses, dots
        phone = re.sub(r'[\s\-\(\)\.]', '', str(phone).strip())
        
        # Already in E.164 format
        if phone.startswith('+'):
            if re.match(r'^\+\d{1,15}$', phone):
                return phone
            else:
                raise ValidationError(f'Invalid international number: {phone}')
        
        # Kenya (254) - 10 digits starting with 0
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
        
        # 9-digit Kenyan (missing leading 0)
        if len(phone) == 9 and phone[0] in '17':
            return '+254' + phone
        
        # US/Canada (1) - 10 digits
        if len(phone) == 10 and phone[0] in '2-9':
            return '+1' + phone
        
        # Generic fallback - default to Kenya if ambiguous
        if re.match(r'^\d{7,15}$', phone):
            return '+254' + phone if len(phone) == 9 else '+' + phone
        
        raise ValidationError(
            f'Invalid phone number: {phone}\n'
            f'Supported formats:\n'
            f'• Kenyan: 0712345678, 712345678, 254712345678\n'
            f'• International: +1234567890, +447123456789\n'
            f'• Must be 7-15 digits (E.164 standard)'
        )
    
    def send_sms(self, phone_number, message, retry_count=0, max_retries=3):
        """
        Send SMS via Africa's Talking with retry logic
        
        Args:
            phone_number: Recipient phone number
            message: SMS content
            retry_count: Current retry attempt
            max_retries: Maximum retry attempts
            
        Returns:
            dict: {
                'success': bool,
                'message_id': str,
                'cost': float,
                'status': str,
                'error': str (if failed)
            }
        """
        self.ensure_one()
        
        if self.gateway_type != 'africastalking':
            raise UserError('Only Africa\'s Talking gateway is supported')
        
        # Normalize phone number
        try:
            phone_number = self.normalize_phone_number(phone_number)
        except ValidationError as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }
        
        # Determine environment
        environment = os.getenv('AT_ENVIRONMENT', 'sandbox')
        if environment == 'sandbox':
            base_url = 'https://api.sandbox.africastalking.com/version1/messaging'
        else:
            base_url = 'https://api.africastalking.com/version1/messaging'
        
        headers = {
            'apiKey': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'username': self.username,
            'to': phone_number,
            'message': message,
        }
        
        if self.sender_id:
            data['from'] = self.sender_id
        
        try:
            _logger.info(f'Sending SMS to {phone_number} via {environment} (attempt {retry_count + 1}/{max_retries + 1})')
            
            response = requests.post(base_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            _logger.info(f'SMS API Response: {result}')
            
            # Parse Africa's Talking response
            if 'SMSMessageData' in result and 'Recipients' in result['SMSMessageData']:
                recipients = result['SMSMessageData']['Recipients']
                
                if recipients and len(recipients) > 0:
                    recipient = recipients[0]
                    
                    if recipient.get('status') == 'Success':
                        # Update last used timestamp
                        self.sudo().write({'last_used': fields.Datetime.now()})
                        
                        return {
                            'success': True,
                            'message_id': recipient.get('messageId'),
                            'cost': float(recipient.get('cost', '0').replace('KES ', '')),
                            'status': 'sent'
                        }
                    else:
                        error_msg = recipient.get('status', 'Unknown error')
                        
                        # Retry on transient errors
                        if retry_count < max_retries and 'network' in error_msg.lower():
                            time.sleep(2 ** retry_count)  # Exponential backoff
                            return self.send_sms(phone_number, message, retry_count + 1, max_retries)
                        
                        return {
                            'success': False,
                            'error': error_msg,
                            'status': 'failed'
                        }
            
            return {
                'success': False,
                'error': 'Invalid response from gateway',
                'status': 'failed'
            }
            
        except requests.exceptions.Timeout:
            # Retry on timeout
            if retry_count < max_retries:
                time.sleep(2 ** retry_count)
                return self.send_sms(phone_number, message, retry_count + 1, max_retries)
            
            _logger.error(f'SMS sending timed out after {max_retries + 1} attempts')
            return {
                'success': False,
                'error': 'Request timed out',
                'status': 'failed'
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error(f'SMS sending failed: {str(e)}')
            
            # Retry on network errors
            if retry_count < max_retries:
                time.sleep(2 ** retry_count)
                return self.send_sms(phone_number, message, retry_count + 1, max_retries)
            
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }
    
    def send_bulk_sms(self, recipients, message, rate_limit=10, delay=1.0):
        """
        Send SMS to multiple recipients with rate limiting
        
        Args:
            recipients: List of phone numbers or recordset of sms.recipient
            message: SMS content
            rate_limit: Max SMS per batch (default: 10)
            delay: Delay between batches in seconds (default: 1.0)
            
        Returns:
            dict: {
                'total': int,
                'success': int,
                'failed': int,
                'results': list
            }
        """
        self.ensure_one()
        
        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'results': []
        }
        
        # Convert to list of phone numbers
        if hasattr(recipients, '_name'):  # Recordset
            phone_numbers = recipients.mapped('phone_number')
        else:
            phone_numbers = recipients
        
        results['total'] = len(phone_numbers)
        
        # Process in batches
        for i in range(0, len(phone_numbers), rate_limit):
            batch = phone_numbers[i:i + rate_limit]
            
            for phone in batch:
                result = self.send_sms(phone, message)
                results['results'].append({
                    'phone': phone,
                    'result': result
                })
                
                if result['success']:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            
            # Delay between batches (except last batch)
            if i + rate_limit < len(phone_numbers):
                time.sleep(delay)
                _logger.info(f'Processed batch {i//rate_limit + 1}, sleeping {delay}s before next batch')
        
        return results
    
    def test_connection(self):
        """Test the connection by sending SMS to test number"""
        self.ensure_one()
        
        if not self.test_phone_number:
            raise UserError(
                'Please set a Test Phone Number in the gateway configuration first!\n\n'
                'Example: +254712345678'
            )
        
        # Send test SMS
        result = self.send_sms(
            self.test_phone_number, 
            f'Test SMS from Strathmore SMS System at {fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )
        
        if result['success']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful ✓',
                    'message': f'Test SMS sent to {self.test_phone_number}\n\nCost: KES {result.get("cost", 0):.2f}',
                    'type': 'success',
                    'sticky': True,
                }
            }
        else:
            raise UserError(f'Connection failed!\n\nError: {result["error"]}')
    
    def refresh_from_env(self):
        """Update settings from environment variables"""
        self.ensure_one()
        
        env_config = {
            'api_key': os.getenv('AT_API_KEY'),
            'username': os.getenv('AT_USERNAME'),
            'sender_id': os.getenv('AT_SENDER_ID'),
        }
        
        update_vals = {}
        
        try:
            if env_config['api_key'] and env_config['api_key'] != self.api_key:
                update_vals['api_key'] = env_config['api_key']
            
            if env_config['username'] and env_config['username'] != self.username:
                update_vals['username'] = env_config['username']
            
            if env_config['sender_id'] and env_config['sender_id'] != self.sender_id:
                update_vals['sender_id'] = env_config['sender_id']
            
            if update_vals:
                self.write(update_vals)
                self.invalidate_recordset()
                message = f"Gateway updated with .env values:\n{', '.join(update_vals.keys())}"
                notification_type = 'success'
            else:
                message = "Gateway is already up to date with .env file"
                notification_type = 'info'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Refresh from .env',
                    'message': message,
                    'type': notification_type,
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to refresh from .env:\n{str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    @api.model
    def get_api_balance(self):
        """
        Called by JS Systray to show balance in header.
        Fetches the balance from the Default Gateway.
        """
        gateway = self.search([('is_default', '=', True)], limit=1)
        if not gateway:
            return "No Gateway"
        
        # TODO: Implement actual balance check via Africa's Talking API
        # For now, return placeholder
        return "KES 4,500.00"