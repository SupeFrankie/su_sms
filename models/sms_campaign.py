from odoo import models, fields, api, _
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
            record.total_cost = record.sent_count * record.sms_count
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
        self.ensure_one()
        if self.target_type == 'manual' and self.manual_phone_numbers:
            self.recipient_ids.filtered(lambda r: r.status == 'pending').unlink()
            numbers = [n.strip() for n in self.manual_phone_numbers.split(',') if n.strip()]
            for number in numbers:
                self.env['sms.recipient'].create({
                    'campaign_id': self.id,
                    'phone_number': number,
                    'name': 'Manual Number',
                    'status': 'pending'
                })
        return True

    def action_send(self):
        self.ensure_one()
        self.write({'status': 'in_progress'})
        return True

    def action_schedule(self):
        self.ensure_one()
        self.write({'status': 'scheduled'})
        return True

    def action_cancel(self):
        self.ensure_one()
        self.write({'status': 'cancelled'})
        return True