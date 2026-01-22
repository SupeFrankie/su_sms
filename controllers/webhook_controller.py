# controllers/webhook_controller.py

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SmsWebhookController(http.Controller):
    
    @http.route('/sms/webhook/delivery', type='http', auth='public', methods=['POST'], csrf=False)
    def sms_delivery_webhook(self, **kwargs):
        try:
            _logger.info(f'Delivery webhook received: {kwargs}')
            
            message_id = kwargs.get('id')
            status = kwargs.get('status')
            phone_number = kwargs.get('phoneNumber')
            
            if not message_id:
                return 'Missing message ID'
            
            recipient = request.env['sms.recipient'].sudo().search([
                ('gateway_message_id', '=', message_id)
            ], limit=1)
            
            if not recipient:
                _logger.warning(f'Recipient not found for message ID: {message_id}')
                return 'Recipient not found'
            
            status_map = {
                'Success': 'sent',
                'Sent': 'sent',
                'Delivered': 'delivered',
                'Failed': 'failed',
                'Rejected': 'failed'
            }
            
            new_status = status_map.get(status, 'failed')
            
            recipient.write({
                'status': new_status,
                'delivered_date': fields.Datetime.now() if new_status == 'delivered' else False,
                'error_message': kwargs.get('failureReason') if new_status == 'failed' else False
            })
            
            return 'OK'
            
        except Exception as e:
            _logger.error(f'Webhook error: {str(e)}')
            return f'Error: {str(e)}'
    
    @http.route('/sms/webhook/incoming', type='http', auth='public', methods=['POST'], csrf=False)
    def sms_incoming_webhook(self, **kwargs):
        try:
            _logger.info(f'Incoming SMS: {kwargs}')
            
            from_number = kwargs.get('from')
            message = kwargs.get('text')
            date = kwargs.get('date')
            
            if not from_number or not message:
                return 'Missing required fields'
            
            request.env['sms.incoming.message'].sudo().create({
                'phone_number': from_number,
                'message': message,
                'received_date': date or fields.Datetime.now()
            })
            
            return 'OK'
            
        except Exception as e:
            _logger.error(f'Incoming SMS error: {str(e)}')
            return f'Error: {str(e)}'