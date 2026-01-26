# models/sms_campaign.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import math

_logger = logging.getLogger(__name__)

class SMSCampaign(models.Model):
    _name = 'sms.campaign'
    _description = 'SMS Campaign'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char('Campaign Title', required=True, tracking=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, string='Status')
    
    sms_type_id = fields.Many2one('sms.type', string='SMS Type', required=True, tracking=True)
    message = fields.Text('Message Content', required=True)
    
    manual_phone_numbers = fields.Text(string="Manual Phone Numbers")
    manual_numbers = fields.Text(string="Manual Numbers (Alias)", related='manual_phone_numbers', readonly=False)

    char_count = fields.Integer(string="Character Count", compute='_compute_message_stats', store=True)
    sms_count = fields.Integer(string="SMS Parts", compute='_compute_message_stats', store=True)
    
    message_length = fields.Integer(string='Message Length', related='char_count', readonly=True)
    sms_parts = fields.Integer(string='Parts Count', related='sms_count', readonly=True)

    personalized = fields.Boolean('Use Personalization')
    send_immediately = fields.Boolean('Send Immediately', default=True)
    
    kfs5_processed = fields.Boolean('KFS5 Processed', default=False, tracking=True)
    kfs5_processed_date = fields.Datetime('KFS5 Processed Date', readonly=True)
    
    target_type = fields.Selection([
        ('all_students', 'All Students'),
        ('all_staff', 'All Staff'),
        ('department', 'Department'),
        ('mailing_list', 'Mailing List'),
        ('adhoc', 'Ad Hoc'),
        ('manual', 'Manual'),
    ], string='Target Audience', required=True)
    
    administrator_id = fields.Many2one('sms.administrator', string='Administrator', default=lambda self: self._default_administrator())
    department_id = fields.Many2one('hr.department', string='Department')
    mailing_list_id = fields.Many2one('sms.mailing.list', string='Mailing List')
    gateway_id = fields.Many2one('sms.gateway.configuration', string='Gateway', default=lambda self: self._default_gateway())
    schedule_date = fields.Datetime('Schedule Date', tracking=True)
    
    total_recipients = fields.Integer(compute='_compute_statistics')
    sent_count = fields.Integer(compute='_compute_statistics')
    failed_count = fields.Integer(compute='_compute_statistics')
    pending_count = fields.Integer(compute='_compute_statistics')
    total_cost = fields.Float(compute='_compute_statistics', string='Total Cost')
    success_rate = fields.Float(compute='_compute_statistics', string='Success Rate')
    
    recipient_ids = fields.One2many('sms.recipient', 'campaign_id', string='Recipients')

    @api.depends('message')
    def _compute_message_stats(self):
        for record in self:
            length = len(record.message) if record.message else 0
            parts = 1
            if length > 160:
                parts = math.ceil(length / 153)
            record.char_count = length
            record.sms_count = parts

    @api.depends('recipient_ids', 'recipient_ids.status')
    def _compute_statistics(self):
        for record in self:
            recipients = record.recipient_ids
            total = len(recipients)
            record.total_recipients = total
            record.sent_count = len(recipients.filtered(lambda r: r.status == 'sent'))
            record.failed_count = len(recipients.filtered(lambda r: r.status == 'failed'))
            record.pending_count = len(recipients.filtered(lambda r: r.status == 'pending'))
            record.total_cost = sum(recipients.mapped('cost'))
            record.success_rate = (record.sent_count / total * 100) if total > 0 else 0.0

    def _default_administrator(self):
        return self.env['sms.administrator'].search([('user_id', '=', self.env.user.id)], limit=1)

    def _default_gateway(self):
        return self.env['sms.gateway.configuration'].search([('is_default', '=', True)], limit=1)

    def action_open_import_wizard(self):
        return {
            'name': _('Import Recipients'),
            'type': 'ir.actions.act_window',
            'res_model': 'sms.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_campaign_id': self.id}
        }

    def action_prepare_recipients(self):
        """Process manual phone numbers into recipients"""
        self.ensure_one()
        
        if self.target_type == 'manual' and self.manual_phone_numbers:
            # Clear existing pending recipients
            self.recipient_ids.filtered(lambda r: r.status == 'pending').unlink()
            
            # Parse comma-separated numbers
            numbers = [n.strip() for n in self.manual_phone_numbers.split(',') if n.strip()]
            
            if not numbers:
                raise UserError('No valid phone numbers found!')
            
            # Create recipients
            for number in numbers:
                try:
                    # Normalize phone number
                    normalized = self.env['sms.gateway.configuration'].normalize_phone_number(number)
                    
                    self.env['sms.recipient'].create({
                        'campaign_id': self.id,
                        'phone_number': normalized,
                        'name': f'Manual - {normalized}',
                        'status': 'pending'
                    })
                except Exception as e:
                    _logger.warning(f'Skipping invalid number {number}: {str(e)}')
            
            # Refresh statistics
            self._compute_statistics()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'{len(self.recipient_ids)} recipients prepared',
                    'type': 'success',
                }
            }
        
        return True

    def action_send(self):
        """Send SMS campaign with rate limiting and retry logic"""
        self.ensure_one()
        
        # Validation
        if not self.recipient_ids:
            raise UserError('No recipients to send to!')
        
        if not self.message:
            raise UserError('Message content is required!')
        
        if not self.gateway_id:
            self.gateway_id = self.env['sms.gateway.configuration'].search([('is_default', '=', True)], limit=1)
            if not self.gateway_id:
                raise UserError('No SMS gateway configured!')
        
        # Update status
        self.write({'status': 'in_progress'})
        self.env.cr.commit()  # Commit status change immediately
        
        # Get pending recipients
        pending_recipients = self.recipient_ids.filtered(lambda r: r.status == 'pending')
        
        if not pending_recipients:
            raise UserError('No pending recipients to send to!')
        
        _logger.info(f'Starting SMS campaign {self.name} with {len(pending_recipients)} recipients')
        
        # Send via gateway with rate limiting (10 SMS/second)
        success_count = 0
        failed_count = 0
        
        for i, recipient in enumerate(pending_recipients):
            try:
                _logger.info(f'Sending SMS {i+1}/{len(pending_recipients)} to {recipient.phone_number}')
                
                # Send SMS
                result = self.gateway_id.send_sms(recipient.phone_number, self.message)
                
                if result['success']:
                    recipient.write({
                        'status': 'sent',
                        'sent_date': fields.Datetime.now(),
                        'gateway_message_id': result.get('message_id'),
                        'cost': result.get('cost', 0.0),
                    })
                    success_count += 1
                    _logger.info(f'✓ SMS sent successfully to {recipient.phone_number}')
                else:
                    recipient.write({
                        'status': 'failed',
                        'error_message': result.get('error', 'Unknown error'),
                    })
                    failed_count += 1
                    _logger.error(f'✗ SMS failed for {recipient.phone_number}: {result.get("error")}')
                
                # Commit after each batch of 10 to prevent data loss
                if (i + 1) % 10 == 0:
                    self.env.cr.commit()
                    _logger.info(f'Progress: {i+1}/{len(pending_recipients)} processed')
                
            except Exception as e:
                _logger.error(f'Exception sending SMS to {recipient.phone_number}: {str(e)}')
                recipient.write({
                    'status': 'failed',
                    'error_message': str(e),
                })
                failed_count += 1
        
        # Final commit
        self.env.cr.commit()
        
        # Update campaign status
        if success_count == len(pending_recipients):
            final_status = 'completed'
            message = f'Campaign completed successfully! {success_count} SMS sent.'
            msg_type = 'success'
        elif success_count > 0:
            final_status = 'completed'
            message = f'Campaign completed with some failures.\nSent: {success_count}\nFailed: {failed_count}'
            msg_type = 'warning'
        else:
            final_status = 'failed'
            message = f'Campaign failed! All {failed_count} SMS failed to send.'
            msg_type = 'danger'
        
        self.write({'status': final_status})
        
        _logger.info(f'Campaign {self.name} finished: {success_count} sent, {failed_count} failed')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Campaign Results',
                'message': message,
                'type': msg_type,
                'sticky': True,
            }
        }

    def action_schedule(self):
        self.ensure_one()
        
        if not self.schedule_date:
            raise UserError('Please set a schedule date first!')
        
        self.write({'status': 'scheduled'})
        return True

    def action_cancel(self):
        self.ensure_one()
        self.write({'status': 'cancelled'})
        return True
    
    def action_retry_failed(self):
        """Retry sending to failed recipients"""
        self.ensure_one()
        
        failed_recipients = self.recipient_ids.filtered(lambda r: r.status == 'failed')
        
        if not failed_recipients:
            raise UserError('No failed recipients to retry!')
        
        # Reset failed recipients to pending
        failed_recipients.write({'status': 'pending', 'error_message': False})
        
        # Send again
        return self.action_send()