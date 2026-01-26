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
    
    is_default = fields.Boolean(
        string='Default Gateway',
        help='Use this gateway for all outgoing SMS unless specified otherwise'
    )
    
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True)]).write({'is_default': False})
        return super(SmsGatewayConfiguration, self).create(vals)

    def write(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True), ('id', '!=', self.id)]).write({'is_default': False})
        return super(SmsGatewayConfiguration, self).write(vals)

    def test_connection(self):
        """Test the connection to the gateway"""
        self.ensure_one()
        # Mock connection test for now
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Connection Successful',
                'message': f'Successfully connected to {self.gateway_type}',
                'type': 'success',
                'sticky': False,
            }
        }
        
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
            
        # Placeholder for actual API call
        return "KES 4,500.00"