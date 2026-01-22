# models/sms_gateway_config.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging
import time
import os

_logger = logging.getLogger(__name__)


class SmsGatewayConfiguration(models.Model):
    _name = 'sms.gateway.configuration'
    _description = 'SMS Gateway Configuration'

    name = fields.Char(required=True, default="Africa's Talking Gateway")
    gateway_type = fields.Selection([
        ('africastalking', 'Africa\'s Talking'),
        ('custom', 'Custom API')
    ], default='africastalking', required=True)
    
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(default=False)
    
    request_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST')
    ], default='POST')
    
    @api.constrains('is_default')
    def _check_default_gateway(self):
        for record in self:
            if record.is_default:
                other_defaults = self.search([
                    ('is_default', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_defaults:
                    other_defaults.write({'is_default': False})
    
    def _get_env_config(self):
        return {
            'username': os.getenv('AT_USERNAME', 'sandbox'),
            'api_key': os.getenv('AT_API_KEY'),
            'sender_id': os.getenv('AT_SENDER_ID', 'STRATHU'),
            'environment': os.getenv('AT_ENVIRONMENT', 'production')
        }
    
    def send_sms(self, phone_number, message):
        self.ensure_one()
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if self.gateway_type == 'africastalking':
                    return self._send_africastalking(phone_number, message)
                else:
                    return False, "Custom gateway not implemented"

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                _logger.warning(f"Network error (Attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return False, f"Network failed after {max_retries} attempts: {str(e)}"
            
            except Exception as e:
                return False, str(e)
    
    def _send_africastalking(self, phone_number, message):
        try:
            config = self._get_env_config()
            
            if not config['api_key']:
                raise ValidationError(
                    'AT_API_KEY not found in environment variables. '
                    'Please configure .env file.'
                )
            
            is_sandbox = config['environment'] == 'sandbox'
            url = 'https://api.sandbox.africastalking.com/version1/messaging' if is_sandbox else \
                  'https://api.africastalking.com/version1/messaging'

            phone = phone_number.strip()
            if not phone.startswith('+'):
                if phone.startswith('0'):
                    phone = '+254' + phone[1:]
                else:
                    phone = '+254' + phone

            data = {
                'username': config['username'],
                'to': phone,
                'message': message,
            }

            if config['sender_id'] and not is_sandbox:
                data['from'] = config['sender_id']

            headers = {
                'apiKey': config['api_key'],
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            _logger.info(f"Sending SMS to {phone} via {url}")

            response = requests.post(url, headers=headers, data=data, timeout=30, verify=True)
            response.raise_for_status()
            result = response.json()

            sms_data = result.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            
            if recipients:
                return True, result
            else:
                error_msg = sms_data.get('Message', 'Unknown error')
                return False, error_msg

        except requests.exceptions.HTTPError as e:
            _logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            return False, f"HTTP {e.response.status_code}: {e.response.text}"
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return False, str(e)
    
    def test_connection(self):
        self.ensure_one()
        
        test_number = self.env.user.partner_id.mobile or self.env.user.partner_id.phone
        
        if not test_number:
            raise ValidationError(
                "Current user has no mobile/phone number in profile. "
                "Please add one to test."
            )

        test_message = f"Test SMS from {self.name}. Sent by {self.env.user.name}."
        
        success, result = self.send_sms(test_number, test_message)
        
        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Test SMS sent to {test_number}!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed: {result}',
                    'type': 'danger',
                    'sticky': True,
                }
            }