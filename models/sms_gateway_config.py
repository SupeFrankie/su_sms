from odoo import models, fields, api
import os
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class SmsGatewayConfiguration(models.Model):
    _name = 'sms.gateway.configuration'
    _description = 'SMS Gateway Configuration'

    name = fields.Char(required=True)
    gateway_type = fields.Selection([
        ('africastalking', "Africa's Talking"),
        ('other', "Other")
    ], default='africastalking', required=True)
    
    is_default = fields.Boolean(string="Default Gateway")
    active = fields.Boolean(default=True)

    # Computed fields reading from .env
    api_key = fields.Char(string="API Key", compute="_compute_credentials", store=False)
    username = fields.Char(string="Username", compute="_compute_credentials", store=False)
    sender_id = fields.Char(string="Sender ID", compute="_compute_credentials", store=False)
    environment = fields.Char(string="Environment", compute="_compute_credentials", store=False)

    def _compute_credentials(self):
        for rec in self:
            if rec.gateway_type == 'africastalking':
                # .strip() removes accidental spaces from the .env file
                rec.api_key = (os.getenv('AT_API_KEY') or '').strip()
                rec.username = (os.getenv('AT_USERNAME') or '').strip()
                rec.sender_id = (os.getenv('AT_SENDER_ID') or '').strip()
                rec.environment = (os.getenv('AT_ENVIRONMENT') or 'sandbox').strip()
            else:
                rec.api_key = False
                rec.username = False
                rec.sender_id = False
                rec.environment = False
   
    @api.model
    def get_default_gateway(self):
        """Retrieve the default gateway configuration."""
        # Try to find one marked as default
        gateway = self.search([('is_default', '=', True)], limit=1)
        
        # If no default, just take the first active one
        if not gateway:
            gateway = self.search([], limit=1)
            
        if not gateway:
            raise models.ValidationError(
                "No SMS Gateway configured! Please go to Configuration -> Gateway Configuration and create one."
            )
        return gateway

    def send_sms(self, phone_number, message):
        """
        Main entry point called by sms.campaign
        """
        self.ensure_one()
        
        if self.gateway_type == 'africastalking':
            return self._send_africastalking(phone_number, message)
        else:
            return False, "Gateway type not supported yet."

    def _send_africastalking(self, phone, message):
        # --- DEBUG LOGGING (Check your terminal after clicking Send) ---
        masked_key = f"{self.api_key[:5]}...{self.api_key[-5:]}" if self.api_key else "MISSING"
        _logger.info(f" AUTH CHECK -> Username: '{self.username}' | Environment: '{self.environment}' | Key: {masked_key}")
        

        if not self.api_key:
            return False, "Configuration Error: API Key not found. Check .env file."

        # Select URL
        if self.environment == 'production':
            url = "https://api.africastalking.com/version1/messaging"
        else:
            url = "https://api.sandbox.africastalking.com/version1/messaging"

        headers = {
            'ApiKey': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        data = {
            'username': self.username, # <--- This MUST match the App Name
            'to': phone,
            'message': message
        }

        if self.sender_id and self.sender_id.lower() != 'none':
            data['from'] = self.sender_id

        try:
            _logger.info(f"Sending SMS via AT to {phone}...")
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 401:
                _logger.error(f" AUTH FAILED: The API rejected username '{self.username}' with the provided key.")
                return False, "Authentication Failed: Username/Key mismatch. Check Server Logs."

            if response.status_code not in [200, 201]:
                return False, f"HTTP Error {response.status_code}: {response.text}"

            return True, "Message Sent Successfully"

        except Exception as e:
            _logger.exception("Failed to send SMS")
            return False, str(e)

    def test_connection(self):
        self.ensure_one()
        if not self.api_key:
            raise models.ValidationError("API Key missing in .env file!")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Connection Test',
                'message': f'Credentials Loaded! Env: {self.environment}',
                'type': 'success',
                'sticky': False,
            }
        }