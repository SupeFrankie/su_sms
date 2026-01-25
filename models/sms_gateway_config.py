# models/sms_gateway_config.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import requests
import logging
import time
import os

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
        ('africastalking', 'Africa\'s Talking'),
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
        help='Africa\'s Talking username (use "sandbox" for testing)'
    )
    
    api_url = fields.Char(
        string='API URL',
        help='Full URL endpoint for custom SMS API'
    )
    
    request_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST')
    ], string='Request Method', default='POST')
    
    active = fields.Boolean(
        string='Active', 
        default=True,
        help='Only active gateways can send SMS'
    )
    
    is_default = fields.Boolean(
        string='Default Gateway',
        default=False,
        help='This gateway will be used by default for all campaigns'
    )
    
    total_sent = fields.Integer(
        string='Total SMS Sent',
        compute='_compute_statistics',
        store=False
    )
    
    last_used = fields.Datetime(
        string='Last Used',
        readonly=True,
        help='When this gateway was last used to send SMS'
    )
    
    def _compute_statistics(self):
        """Compute usage statistics"""
        for gateway in self:
            campaigns = self.env['sms.campaign'].search([
                ('gateway_id', '=', gateway.id)
            ])
            gateway.total_sent = sum(campaigns.mapped('sent_count'))
    
    @api.constrains('is_default')
    def _check_default_gateway(self):
        """Ensure only one default gateway exists"""
        for record in self:
            if record.is_default:
                other_defaults = self.search([
                    ('is_default', '=', True),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if other_defaults:
                    other_defaults.write({'is_default': False})
    
    @api.constrains('gateway_type', 'username', 'api_url')
    def _check_required_fields(self):
        """Validate required fields based on gateway type"""
        for record in self:
            if record.gateway_type == 'africastalking':
                if not record.username:
                    raise ValidationError(
                        'Username is required for Africa\'s Talking gateway'
                    )
            elif record.gateway_type == 'custom':
                if not record.api_url:
                    raise ValidationError(
                        'API URL is required for Custom API gateway'
                    )
    
    @api.model
    def get_env_config(self):
        """Get SMS gateway configuration from environment variables"""
        config = {
            'username': os.getenv('AT_USERNAME', 'sandbox'),
            'api_key': os.getenv('AT_API_KEY', ''),
            'sender_id': os.getenv('AT_SENDER_ID', ''),
            'environment': os.getenv('AT_ENVIRONMENT', 'sandbox'),
        }
        return config
    
    @api.model
    def validate_env_config(self):
        """Validate that required environment variables are set"""
        required_vars = {
            'AT_USERNAME': 'Africa\'s Talking username',
            'AT_API_KEY': 'Africa\'s Talking API key',
        }
        
        missing = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing.append(f'{var} ({description})')
        
        if missing:
            raise ValidationError(
                f"Missing required environment variables in .env file:\n\n"
                f"{chr(10).join(f'  • {var}' for var in missing)}\n\n"
                f"Please create/update .env file in Odoo root directory with:\n\n"
                f"AT_USERNAME=sandbox\n"
                f"AT_API_KEY=your_api_key_here\n"
                f"AT_SENDER_ID=STRATHMORE\n"
                f"AT_ENVIRONMENT=sandbox"
            )
        
        return True
    
    @api.model
    def create_from_env(self):
        """Create default SMS gateway configuration from environment variables"""
        try:
            self.validate_env_config()
        except ValidationError:
            return self.browse()
        
        env_config = self.get_env_config()
        
        existing = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if existing:
            update_vals = {}
            if existing.api_key != env_config['api_key'] and env_config['api_key']:
                update_vals['api_key'] = env_config['api_key']
            if existing.username != env_config['username'] and env_config['username']:
                update_vals['username'] = env_config['username']
            if existing.sender_id != env_config['sender_id'] and env_config['sender_id']:
                update_vals['sender_id'] = env_config['sender_id']
            
            if update_vals:
                existing.write(update_vals)
            
            return existing
        
        gateway_name = f"Africa's Talking ({env_config['environment'].title()})"
        
        gateway = self.create({
            'name': gateway_name,
            'gateway_type': 'africastalking',
            'username': env_config['username'],
            'api_key': env_config['api_key'],
            'sender_id': env_config['sender_id'],
            'is_default': True,
            'active': True,
        })
        
        return gateway
    
    @api.model
    def get_default_gateway(self):
        """Get the default active gateway, create from .env if none exists"""
        gateway = self.search([
            ('is_default', '=', True),
            ('active', '=', True)
        ], limit=1)
        
        if gateway:
            return gateway
        
        gateway = self.search([('active', '=', True)], limit=1)
        
        if gateway:
            return gateway
        
        try:
            gateway = self.create_from_env()
            if gateway:
                return gateway
        except Exception:
            pass
        
        raise UserError(
            'No SMS gateway configured!\n\n'
            'Please either:\n'
            '1. Configure gateway via SMS System → Configuration → Gateway Configuration\n'
            '2. Set up .env file with AT_API_KEY and AT_USERNAME\n'
            '3. Contact system administrator'
        )
    
    def send_sms(self, phone_number, message):
        """Send SMS through configured gateway with retry logic"""
        self.ensure_one()
        
        if not self.active:
            return False, 'Gateway is not active'
        
        max_retries = 3
        retry_delay_base = 2
        
        for attempt in range(max_retries):
            try:
                if self.gateway_type == 'africastalking':
                    success, result = self._send_africastalking(phone_number, message)
                elif self.gateway_type == 'custom':
                    success, result = self._send_custom(phone_number, message)
                else:
                    return False, f"Unsupported gateway type: {self.gateway_type}"
                
                if success:
                    self.write({'last_used': fields.Datetime.now()})
                
                return success, result

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    sleep_time = retry_delay_base ** attempt
                    time.sleep(sleep_time)
                    continue
                else:
                    return False, f"Network failed after {max_retries} attempts: {str(e)}"
            
            except Exception as e:
                return False, str(e)
        
        return False, 'Unknown error occurred'
    
    def _send_africastalking(self, phone_number, message):
        """Send SMS via Africa's Talking API"""
        try:
            if not self.username:
                return False, "Username is not configured"
            
            if not self.api_key:
                return False, "API Key is not configured"
            
            is_sandbox = self.username and self.username.strip().lower() == 'sandbox'
            
            if is_sandbox:
                url = 'https://api.sandbox.africastalking.com/version1/messaging'
            else:
                url = 'https://api.africastalking.com/version1/messaging'
            
            phone = self._normalize_phone_number(phone_number)
            
            data = {
                'username': self.username,
                'to': phone,
                'message': message,
            }
            
            if self.sender_id and not is_sandbox:
                data['from'] = self.sender_id
            
            headers = {
                'apiKey': self.api_key,
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(
                url, 
                headers=headers, 
                data=data, 
                timeout=30,
                verify=False
            )
            
            if response.status_code == 401:
                return False, (
                    "Authentication Failed: Username/Key mismatch. "
                    "Please verify credentials in Africa's Talking dashboard."
                )
            
            response.raise_for_status()
            result = response.json()
            
            sms_data = result.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            
            if recipients and len(recipients) > 0:
                recipient_data = recipients[0]
                status = recipient_data.get('status', '').lower()
                
                if 'success' in status or 'sent' in status:
                    return True, result
                else:
                    error_msg = recipient_data.get('status', 'Unknown error')
                    return False, error_msg
            else:
                error_msg = sms_data.get('Message', 'No recipients in response')
                
                if 'InvalidCredentials' in error_msg or 'credentials' in error_msg.lower():
                    return False, (
                        "Invalid Credentials: Username and API Key don't match.\n"
                        f"Current username: {self.username}\n"
                        "Please verify in Africa's Talking dashboard."
                    )
                
                return False, error_msg

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            return False, error_msg
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            return False, error_msg
    
    def _send_custom(self, phone_number, message):
        """Send SMS via Custom API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'phone': phone_number,
                'message': message,
                'sender': self.sender_id or 'SMS'
            }
            
            if self.request_method == 'POST':
                response = requests.post(
                    self.api_url, 
                    headers=headers, 
                    json=data, 
                    timeout=30
                )
            else:
                response = requests.get(
                    self.api_url, 
                    headers=headers, 
                    params=data, 
                    timeout=30
                )
            
            response.raise_for_status()
            return True, response.text
            
        except Exception as e:
            error_msg = f"Custom API error: {str(e)}"
            return False, error_msg
    
    def _normalize_phone_number(self, phone_number):
        """Normalize phone number to E.164 format for Kenya"""
        if not phone_number:
            return phone_number
        
        phone = phone_number.strip().replace(' ', '').replace('-', '')
        
        if phone.startswith('+254'):
            return phone
        
        if phone.startswith('+'):
            return phone
        
        if phone.startswith('0'):
            return '+254' + phone[1:]
        
        if phone.startswith(('7', '1')):
            return '+254' + phone
        
        return phone
    
    def test_connection(self):
        """Test gateway connection by sending SMS to test number"""
        self.ensure_one()
        
        # Get test number from user profile or use configured number
        user = self.env.user
        test_number = None
        
        # Try to get phone from user's partner
        if user.partner_id:
            for field_name in ['mobile', 'phone', 'mobile_phone']:
                try:
                    test_number = getattr(user.partner_id, field_name, None)
                    if test_number:
                        break
                except AttributeError:
                    continue
        
        # Fallback to asking user
        if not test_number:
            # Return a wizard to ask for phone number
            return {
                'type': 'ir.actions.act_window',
                'name': 'Test Gateway',
                'res_model': 'sms.gateway.test.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_gateway_id': self.id}
            }
        
        # Send test SMS
        test_message = (
            f"Gateway test successful!\n"
            f"Gateway: {self.name}\n"
            f"Sent from Odoo SMS Module"
        )
        
        success, result = self.send_sms(test_number, test_message)
        
        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Successful',
                    'message': f'Test SMS sent to {test_number}\n\nCheck your phone!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Failed',
                    'message': f'Failed to send test SMS:\n\n{result}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_refresh_from_env(self):
        """Action to refresh gateway configuration from .env file"""
        self.ensure_one()
        
        try:
            env_config = self.get_env_config()
            
            update_vals = {}
            
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