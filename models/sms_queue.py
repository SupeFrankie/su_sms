# models/sms_queue.py 

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SMSQueue(models.Model):
    """
    Queue model for SMS sending jobs
    PHP equivalent: Laravel's jobs table
    """
    _name = 'sms.queue'
    _description = 'SMS Queue Jobs'
    _order = 'priority, create_date'
    
    campaign_id = fields.Many2one('sms.campaign', string='Campaign', required=True, ondelete='cascade')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending', required=True, index=True)
    
    priority = fields.Integer(default=10, help='Lower number = higher priority')
    attempts = fields.Integer(default=0)
    max_attempts = fields.Integer(default=3)
    
    scheduled_date = fields.Datetime(string='Scheduled For', index=True)
    started_date = fields.Datetime(string='Started At')
    completed_date = fields.Datetime(string='Completed At')
    
    error_message = fields.Text(string='Error Message')
    
    @api.model
    def process_queue(self):
        """
        Process pending queue jobs
        Called by scheduled action (ir.cron)
        
        PHP equivalent: Laravel queue worker
        """
        now = fields.Datetime.now()
        
        # Get pending jobs that are due
        jobs = self.search([
            ('state', '=', 'pending'),
            '|',
            ('scheduled_date', '=', False),
            ('scheduled_date', '<=', now)
        ], limit=10, order='priority, create_date')
        
        for job in jobs:
            try:
                job.state = 'processing'
                job.started_date = now
                
                # Execute the job
                job.campaign_id._send_batch()
                
                job.state = 'completed'
                job.completed_date = fields.Datetime.now()
                
            except Exception as e:
                job.attempts += 1
                job.error_message = str(e)
                
                if job.attempts >= job.max_attempts:
                    job.state = 'failed'
                    _logger.error(f'Queue job {job.id} failed after {job.attempts} attempts: {str(e)}')
                else:
                    job.state = 'pending'
                    _logger.warning(f'Queue job {job.id} failed, retrying ({job.attempts}/{job.max_attempts}): {str(e)}')


class SMSCampaign(models.Model):
    _inherit = 'sms.campaign'
    
    queue_id = fields.Many2one('sms.queue', string='Queue Job', readonly=True)
    
    def action_send(self):
        """Override to use queue system"""
        self.ensure_one()
        
        # Check credit
        if not self.can_send:
            raise exceptions.UserError(self.credit_block_reason)
        
        if not self.recipient_ids:
            raise exceptions.UserError(_("No recipients! Please prepare recipients first."))
        
        if not self.gateway_id:
            raise exceptions.UserError(_("No SMS gateway configured!"))
        
        self.status = 'in_progress'
        
        # Create queue job
        queue_job = self.env['sms.queue'].create({
            'campaign_id': self.id,
            'state': 'pending',
            'priority': 10,
        })
        
        self.queue_id = queue_job.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Campaign queued for sending! Processing will begin shortly.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_schedule(self):
        """Override to use queue system with scheduled date"""
        self.ensure_one()
        
        if not self.schedule_date:
            raise exceptions.UserError(_("Please set a schedule date first!"))
        
        if not self.recipient_ids:
            raise exceptions.UserError(_("No recipients! Please prepare recipients first."))
        
        self.status = 'scheduled'
        
        # Create scheduled queue job
        queue_job = self.env['sms.queue'].create({
            'campaign_id': self.id,
            'state': 'pending',
            'scheduled_date': self.schedule_date,
            'priority': 5,
        })
        
        self.queue_id = queue_job.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Campaign scheduled for %s') % self.schedule_date,
                'type': 'success',
            }
        }