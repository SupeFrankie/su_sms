# models/sms_campaign.py

from odoo import models, fields, api, exceptions, _
import logging
import base64
import csv
import io

_logger = logging.getLogger(__name__)

class SMSCampaign(models.Model):
    _name = 'sms.campaign'
    _description = 'SMS Campaign'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char('Campaign Name', required=True, tracking=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, string='Status')
    
    sms_type_id = fields.Many2one(
        'sms.type',
        string='SMS Type',
        required=True,
        tracking=True
    )
    
    message = fields.Text('Message Content', required=True)
    message_length = fields.Integer('Message Length', compute='_compute_message_length')
    
    personalized = fields.Boolean('Use Personalization')
    
    target_type = fields.Selection([
        ('all_students', 'All Students'),
        ('all_staff', 'All Staff'),
        ('department', 'Department'),
        ('mailing_list', 'Mailing List'),
        ('adhoc', 'Ad-hoc (CSV Import)'),
        ('manual', 'Manual Numbers'),
    ], string='Target Audience', required=True, default='manual')
    
    department_id = fields.Many2one('hr.department', string='Department')
    mailing_list_id = fields.Many2one('sms.mailing.list', string='Mailing List')
    
    # Import fields
    import_file = fields.Binary('Import File', attachment=True)
    import_filename = fields.Char('Filename')
    
    manual_numbers = fields.Text('Phone Numbers')
    
    schedule_date = fields.Datetime('Scheduled Date', tracking=True)
    send_immediately = fields.Boolean('Send Immediately', default=True)
    
    administrator_id = fields.Many2one(
        'res.users', 
        string='Administrator',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )
    
    recipient_ids = fields.One2many('sms.recipient', 'campaign_id', string='Recipients')
    
    # Statistics
    total_recipients = fields.Integer(compute='_compute_statistics', store=True)
    sent_count = fields.Integer(compute='_compute_statistics', store=True)
    failed_count = fields.Integer(compute='_compute_statistics', store=True)
    pending_count = fields.Integer(compute='_compute_statistics', store=True)
    success_rate = fields.Float(compute='_compute_success_rate', store=False)
    
    total_cost = fields.Float('Total Cost', compute='_compute_cost', store=True)
    gateway_id = fields.Many2one('sms.gateway.configuration', string='Gateway', required=True)
    
    kfs5_processed = fields.Boolean('Processed in KFS5', default=False)
    kfs5_processed_date = fields.Datetime('KFS5 Process Date')

    @api.depends('message')
    def _compute_message_length(self):
        for record in self:
            record.message_length = len(record.message) if record.message else 0

    @api.depends('recipient_ids', 'recipient_ids.status')
    def _compute_statistics(self):
        for record in self:
            recipients = record.recipient_ids
            record.total_recipients = len(recipients)
            record.sent_count = len(recipients.filtered(lambda r: r.status == 'sent'))
            record.failed_count = len(recipients.filtered(lambda r: r.status == 'failed'))
            record.pending_count = len(recipients.filtered(lambda r: r.status == 'pending'))

    @api.depends('total_recipients', 'sent_count')
    def _compute_success_rate(self):
        for record in self:
            if record.total_recipients > 0:
                record.success_rate = (record.sent_count / record.total_recipients) * 100
            else:
                record.success_rate = 0.0

    @api.depends('recipient_ids', 'recipient_ids.cost')
    def _compute_cost(self):
        for record in self:
            record.total_cost = sum(record.recipient_ids.mapped('cost'))

    def action_view_recipients(self):
        self.ensure_one()
        return {
            'name': _('Recipients'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'sms.recipient',
            'domain': [('campaign_id', '=', self.id)],
            'context': {'default_campaign_id': self.id},
        }

    def action_download_template(self):
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['name', 'phone_number'])
        writer.writerow(['John Doe', '+254712345678'])
        
        content = base64.b64encode(output.getvalue().encode('utf-8'))
        filename = 'sms_recipient_template.csv'
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': content,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_prepare_recipients(self):
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