# models/sms_credit.py - Credit Balance Management

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SMSCreditManager(models.TransientModel):
    """
    Singleton model to manage SMS credit balance
    Mimics PHP system's credit checking on every page load
    """
    _name = 'sms.credit.manager'
    _description = 'SMS Credit Balance Manager'
    
    balance = fields.Float(string='Current Balance (KES)', readonly=True)
    last_check = fields.Datetime(string='Last Checked', readonly=True)
    
    @api.model
    def get_current_balance(self, force_refresh=False):
        """
        Get current SMS credit balance
        
        PHP equivalent: Controller.php __construct() - fetches balance on every page load
        
        Args:
            force_refresh: Force API call even if cache exists
            
        Returns:
            dict: {'balance': float, 'currency': str, 'low_balance': bool}
        """
        # Check cache first (valid for 5 minutes)
        cache_key = 'sms_credit_balance'
        cached = self.env['ir.config_parameter'].sudo().get_param(cache_key)
        cache_time_key = 'sms_credit_balance_time'
        cached_time = self.env['ir.config_parameter'].sudo().get_param(cache_time_key)
        
        if not force_refresh and cached and cached_time:
            from datetime import datetime, timedelta
            cache_dt = fields.Datetime.from_string(cached_time)
            if datetime.now() - cache_dt < timedelta(minutes=5):
                return {
                    'balance': float(cached),
                    'currency': 'KES',
                    'low_balance': float(cached) < self._get_minimum_balance(),
                    'threshold_block': float(cached) < self._get_icts_threshold()
                }
        
        # Fetch from gateway
        gateway = self.env['sms.gateway.configuration'].search([
            ('is_default', '=', True),
            ('active', '=', True)
        ], limit=1)
        
        if not gateway:
            gateway = self.env['sms.gateway.configuration'].search([
                ('active', '=', True)
            ], limit=1)
        
        if not gateway:
            _logger.warning('No SMS gateway configured')
            return {
                'balance': 0.0,
                'currency': 'KES',
                'low_balance': True,
                'threshold_block': True,
                'error': 'No gateway configured'
            }
        
        try:
            balance_data = gateway.get_balance()
            balance = balance_data.get('balance', 0.0)
            
            # Cache the result
            self.env['ir.config_parameter'].sudo().set_param(cache_key, str(balance))
            self.env['ir.config_parameter'].sudo().set_param(
                cache_time_key, 
                fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            return {
                'balance': balance,
                'currency': 'KES',
                'low_balance': balance < self._get_minimum_balance(),
                'threshold_block': balance < self._get_icts_threshold()
            }
            
        except Exception as e:
            _logger.error(f'Failed to fetch SMS balance: {str(e)}')
            return {
                'balance': 0.0,
                'currency': 'KES',
                'low_balance': True,
                'threshold_block': True,
                'error': str(e)
            }
    
    @api.model
    def _get_minimum_balance(self):
        """Get minimum balance threshold (triggers low credit warning)"""
        return float(
            self.env['ir.config_parameter'].sudo().get_param(
                'sms.minimum_credit_balance', 
                default='80.0'
            )
        )
    
    @api.model
    def _get_icts_threshold(self):
        """Get ICTS threshold (blocks non-system admins)"""
        return float(
            self.env['ir.config_parameter'].sudo().get_param(
                'sms.icts_credit_balance_threshold', 
                default='15000.0'
            )
        )
    
    @api.model
    def check_can_send(self):
        """
        Check if current user can send SMS based on credit balance
        
        PHP Logic:
        - Credit <= 0: Block everyone
        - Credit < ICTS_THRESHOLD: Block non-System Admins
        - Otherwise: Allow
        
        Returns:
            tuple: (bool, str) - (can_send, reason_if_blocked)
        """
        balance_data = self.get_current_balance()
        balance = balance_data['balance']
        user = self.env.user
        
        # Credit <= 0: Block everyone
        if balance <= 0:
            return False, _('Insufficient SMS credit balance. Current balance: KES 0.00')
        
        # Credit < ICTS_THRESHOLD: Block non-System Admins
        if balance < self._get_icts_threshold():
            if not user.has_group('su_sms.group_sms_system_admin'):
                return False, _(
                    'SMS credit balance is below the threshold (KES %.2f). '
                    'Only System Administrators can send SMS at this time. '
                    'Current balance: KES %.2f'
                ) % (self._get_icts_threshold(), balance)
        
        return True, ''
    
    @api.model
    def format_balance_display(self):
        """
        Format balance for display in UI
        
        Returns:
            str: Formatted balance string (e.g., "KES 12,450.50")
        """
        balance_data = self.get_current_balance()
        
        if 'error' in balance_data:
            return _('Balance: Error')
        
        balance = balance_data['balance']
        return f"KES {balance:,.2f}"


class SMSGatewayConfiguration(models.Model):
    """Extended to add balance fetching"""
    _inherit = 'sms.gateway.configuration'
    
    def get_balance(self):
        """
        Fetch balance from SMS gateway
        
        Returns:
            dict: {'balance': float, 'currency': str}
        """
        self.ensure_one()
        
        if self.gateway_type == 'africastalking':
            return self._get_balance_africastalking()
        elif self.gateway_type == 'custom':
            return self._get_balance_custom()
        else:
            raise UserError(_('Unsupported gateway type: %s') % self.gateway_type)
    
    def _get_balance_africastalking(self):
        """Fetch balance from Africa's Talking"""
        import requests
        
        try:
            is_sandbox = self.username and self.username.strip().lower() == 'sandbox'
            
            if is_sandbox:
                url = 'https://api.sandbox.africastalking.com/version1/user'
            else:
                url = 'https://api.africastalking.com/version1/user'
            
            params = {'username': self.username}
            headers = {
                'apiKey': self.api_key,
                'Accept': 'application/json'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            data = response.json()
            balance_str = data.get('UserData', {}).get('balance', 'KES 0.00')
            
            # Parse "KES 12345.67" format
            if balance_str.startswith('KES'):
                balance = float(balance_str.split()[1])
            else:
                balance = 0.0
            
            return {'balance': balance, 'currency': 'KES'}
            
        except Exception as e:
            _logger.error(f'Failed to fetch Africa\'s Talking balance: {str(e)}')
            raise UserError(_('Failed to fetch balance: %s') % str(e))
    
    def _get_balance_custom(self):
        """Fetch balance from custom API"""
        # Implement custom API balance fetching here
        return {'balance': 0.0, 'currency': 'KES'}