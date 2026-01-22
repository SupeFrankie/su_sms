# models/sms_campaign.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
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
        help='Classification of SMS campaign'
    )
    
    message = fields.Text('Message Content', required=True)
    message_length = fields.Integer('Message Length', compute='_compute_message_length')
    
    personalized = fields.Boolean(
        'Use Personalization', 
        help="Replace {name}, {admission_number}, {staff_id} with actual values"
    )
    
    target_type = fields.Selection([
        ('all_students', 'All Students'),
        ('all_staff', 'All Staff'),
        ('department', 'Department'),
        ('all_departments', 'All Departments'),
        ('club', 'Club'),
        ('mailing_list', 'Mailing List'),
        ('adhoc', 'Ad Hoc (CSV Upload)'),
        ('manual', 'Manual Numbers'),
    ], string='Target Audience', required=True)
    
    department_id = fields.Many2one('hr.department', 'Department')
    club_id = fields.Many2one('sms.club', 'Club')
    mailing_list_id = fields.Many2one('sms.mailing.list', 'Mailing List')
    
    import_file = fields.Binary(string='CSV File')
    import_filename = fields.Char(string='Filename')
    manual_numbers = fields.Text(string='Manual Numbers')
    
    recipient_ids = fields.One2many('sms.recipient', 'campaign_id', 'Recipients')
    total_recipients = fields.Integer('Total Recipients', compute='_compute_recipient_count')
    
    send_immediately = fields.Boolean('Send Immediately', default=True)
    schedule_date = fields.Datetime('Scheduled Send Time')
    
    sent_count = fields.Integer('Sent', readonly=True, default=0)
    failed_count = fields.Integer('Failed', readonly=True, default=0)
    delivered_count = fields.Integer('Delivered', readonly=True, default=0)
    pending_count = fields.Integer('Pending', compute='_compute_recipient_count')
    
    success_rate = fields.Float('Success Rate', compute='_compute_success_rate', store=True)
    
    gateway_id = fields.Many2one(
        'sms.gateway.configuration', 
        'SMS Gateway',
        help='Gateway to use for sending (leave empty for default)'
    )
    
    administrator_id = fields.Many2one(
        'res.users',
        string='Administrator',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    
    kfs5_processed = fields.Boolean(
        string='KFS5 Processed',
        default=False,
        help='Whether this SMS has been processed in KFS5 financial system'
    )
    
    kfs5_processed_date = fields.Datetime(
        string='KFS5 Process Date',
        readonly=True
    )
    
    total_cost = fields.Float(
        string='Total Cost (KES)',
        compute='_compute_total_cost',
        store=True
    )
    
    @api.depends('message')
    def _compute_message_length(self):
        for campaign in self:
            campaign.message_length = len(campaign.message) if campaign.message else 0
    
    @api.depends('recipient_ids')
    def _compute_recipient_count(self):
        for campaign in self:
            campaign.total_recipients = len(campaign.recipient_ids)
            campaign.pending_count = len(
                campaign.recipient_ids.filtered(lambda r: r.status == 'pending')
            )
    
    @api.depends('sent_count', 'total_recipients')
    def _compute_success_rate(self):
        for campaign in self:
            if campaign.total_recipients > 0:
                campaign.success_rate = (campaign.sent_count / campaign.total_recipients) * 100
            else:
                campaign.success_rate = 0.0
    
    @api.depends('recipient_ids.cost')
    def _compute_total_cost(self):
        for campaign in self:
            campaign.total_cost = sum(campaign.recipient_ids.mapped('cost'))
    
    def _get_gateway(self):
        """Get SMS gateway for this campaign with fallback logic"""
        self.ensure_one()
        
        if self.gateway_id and self.gateway_id.active:
            return self.gateway_id
        
        try:
            gateway = self.env['sms.gateway.configuration'].get_default_gateway()
            return gateway
        except UserError as e:
            raise
    
    def action_prepare_recipients(self):
        """Prepare recipients based on target type"""
        self.ensure_one()
        
        if not self._check_user_permission():
            raise UserError(
                _('You do not have permission to send to this audience.\n\n'
                  'Your role: %s\n'
                  'Target: %s') % (
                    self.env.user.sms_role or 'None',
                    dict(self._fields['target_type'].selection).get(self.target_type)
                )
            )
        
        self.recipient_ids.unlink()
        
        recipients_data = []
        
        if self.target_type == 'all_students':
            recipients_data = self._get_all_students()
        elif self.target_type == 'all_staff':
            recipients_data = self._get_all_staff()
        elif self.target_type == 'department':
            recipients_data = self._get_department_contacts()
        elif self.target_type == 'all_departments':
            recipients_data = self._get_all_departments_contacts()
        elif self.target_type == 'club':
            recipients_data = self._get_club_members()
        elif self.target_type == 'mailing_list':
            recipients_data = self._get_mailing_list_contacts()
        elif self.target_type == 'adhoc':
            recipients_data = self._process_adhoc_csv()
        elif self.target_type == 'manual':
            recipients_data = self._process_manual_numbers()
        
        if recipients_data:
            self.env['sms.recipient'].create(recipients_data)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('%d recipients prepared!') % len(recipients_data),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _check_user_permission(self):
        """Check if user has permission based on role"""
        user = self.env.user
        
        if user.has_group('su_sms.group_sms_system_admin'):
            return True
        
        if user.has_group('su_sms.group_sms_administrator'):
            if self.target_type in ['all_students', 'all_staff', 'all_departments']:
                return True
        
        if user.has_group('su_sms.group_sms_faculty_admin'):
            if self.target_type in ['all_students']:
                return True
        
        if user.has_group('su_sms.group_sms_department_admin'):
            if self.target_type == 'department' and self.department_id == user.department_id:
                return True
            if self.target_type == 'all_staff':
                return True
        
        if user.has_group('su_sms.group_sms_basic_user'):
            if self.target_type in ['adhoc', 'manual']:
                return True
        
        if self.target_type in ['adhoc', 'manual']:
            return True
        
        return False
    
    def _get_all_students(self):
        """Get all students from SMS contacts"""
        recipients = []
        contacts = self.env['sms.contact'].search([
            ('contact_type', '=', 'student'),
            ('active', '=', True),
            ('opt_in', '=', True)
        ])
        
        for contact in contacts:
            if self._check_not_blacklisted(contact.mobile):
                recipients.append({
                    'campaign_id': self.id,
                    'name': contact.name,
                    'phone_number': contact.mobile,
                    'admission_number': contact.student_id,
                    'recipient_type': 'student',
                })
        
        return recipients
    
    def _get_all_staff(self):
        """Get all staff from SMS contacts"""
        recipients = []
        
        domain = [
            ('contact_type', '=', 'staff'),
            ('active', '=', True),
            ('opt_in', '=', True)
        ]
        
        if self.env.user.has_group('su_sms.group_sms_department_admin') and \
           not self.env.user.has_group('su_sms.group_sms_administrator'):
            if self.env.user.department_id:
                domain.append(('department_id', '=', self.env.user.department_id.id))
        
        contacts = self.env['sms.contact'].search(domain)
        
        for contact in contacts:
            if self._check_not_blacklisted(contact.mobile):
                recipients.append({
                    'campaign_id': self.id,
                    'name': contact.name,
                    'phone_number': contact.mobile,
                    'staff_id': contact.student_id,
                    'recipient_type': 'staff',
                    'department': contact.department_id.name if contact.department_id else '',
                })
        
        return recipients
    
    def _get_department_contacts(self):
        """Get contacts from specific department"""
        if not self.department_id:
            raise UserError(_("Please select a department"))
        
        recipients = []
        contacts = self.env['sms.contact'].search([
            ('department_id', '=', self.department_id.id),
            ('active', '=', True),
            ('opt_in', '=', True)
        ])
        
        for contact in contacts:
            if self._check_not_blacklisted(contact.mobile):
                recipients.append({
                    'campaign_id': self.id,
                    'name': contact.name,
                    'phone_number': contact.mobile,
                    'department': self.department_id.name,
                    'recipient_type': contact.contact_type,
                })
        
        return recipients
    
    def _get_all_departments_contacts(self):
        """Get contacts from all departments"""
        recipients = []
        contacts = self.env['sms.contact'].search([
            ('department_id', '!=', False),
            ('active', '=', True),
            ('opt_in', '=', True)
        ])
        
        for contact in contacts:
            if self._check_not_blacklisted(contact.mobile):
                recipients.append({
                    'campaign_id': self.id,
                    'name': contact.name,
                    'phone_number': contact.mobile,
                    'department': contact.department_id.name if contact.department_id else '',
                    'recipient_type': contact.contact_type,
                })
        
        return recipients
    
    def _get_club_members(self):
        """Get club members"""
        if not self.club_id:
            raise UserError(_("Please select a club"))
        
        recipients = []
        for contact in self.club_id.member_ids:
            if contact.opt_in and self._check_not_blacklisted(contact.mobile):
                recipients.append({
                    'campaign_id': self.id,
                    'name': contact.name,
                    'phone_number': contact.mobile,
                    'club': self.club_id.name,
                    'recipient_type': 'student',
                })
        
        return recipients
    
    def _get_mailing_list_contacts(self):
        """Get mailing list contacts"""
        if not self.mailing_list_id:
            raise UserError(_("Please select a mailing list"))
        
        recipients = []
        for contact in self.mailing_list_id.contact_ids:
            if contact.opt_in and self._check_not_blacklisted(contact.mobile):
                recipients.append({
                    'campaign_id': self.id,
                    'name': contact.name,
                    'phone_number': contact.mobile,
                    'recipient_type': contact.contact_type,
                })
        
        return recipients
    
    def _process_adhoc_csv(self):
        """Process CSV file with name,number format"""
        if not self.import_file:
            raise UserError(_("Please upload a CSV file"))
        
        recipients = []
        errors = []
        
        try:
            file_content = base64.b64decode(self.import_file)
            csv_data = io.StringIO(file_content.decode('utf-8'))
            csv_reader = csv.DictReader(csv_data)
            
            row_num = 1
            for row in csv_reader:
                row_num += 1
                
                name = row.get('name', '').strip()
                number = row.get('number', '').strip()
                if not number:
                    errors.append(_('Row %d: Missing phone number') % row_num)
                    continue
                
                if not name:
                    name = number
                
                if self._check_not_blacklisted(number):
                    recipients.append({
                        'campaign_id': self.id,
                        'name': name,
                        'phone_number': number,
                        'recipient_type': 'other',
                    })
                else:
                    errors.append(_('Row %d: Phone number %s is blacklisted') % (row_num, number))
            
            if errors:
                error_msg = '\n'.join(errors[:10])
                if len(errors) > 10:
                    error_msg += _('\n... and %d more errors') % (len(errors) - 10)
                raise UserError(error_msg)
        
        except Exception as e:
            raise UserError(_('Error processing CSV file: %s') % str(e))
        
        return recipients
    
    def _process_manual_numbers(self):
        """Process comma-separated manual numbers"""
        if not self.manual_numbers:
            raise UserError(_("Please enter phone numbers"))
        
        recipients = []
        numbers = [n.strip() for n in self.manual_numbers.split(',')]
        
        for number in numbers:
            if number and self._check_not_blacklisted(number):
                recipients.append({
                    'campaign_id': self.id,
                    'name': number,
                    'phone_number': number,
                    'recipient_type': 'other',
                })
        
        return recipients
    
    def _check_not_blacklisted(self, phone):
        """Check if phone number is not blacklisted"""
        return not self.env['sms.blacklist'].is_blacklisted(phone)
    
    def action_send(self):
        """Send SMS campaign"""
        self.ensure_one()
        
        if not self.recipient_ids:
            raise UserError(_("No recipients! Please prepare recipients first."))
        
        try:
            gateway = self._get_gateway()
            
            if not gateway.username or not gateway.api_key:
                raise UserError(
                    _('Gateway "%s" is not fully configured!\n\n'
                      'Missing: %s\n\n'
                      'Please update gateway configuration.') % (
                        gateway.name,
                        ', '.join(filter(None, [
                            'Username' if not gateway.username else '',
                            'API Key' if not gateway.api_key else ''
                        ]))
                    )
                )
                
        except UserError as e:
            raise UserError(
                _('Cannot send SMS: %s\n\n'
                  'Please configure gateway:\n'
                  'SMS System → Configuration → Gateway Configuration') % str(e)
            )
        
        self.status = 'in_progress'
        
        pending_recipients = self.recipient_ids.filtered(lambda r: r.status == 'pending')
        
        if not pending_recipients:
            raise UserError(_("No pending recipients to send to!"))
        
        batch_size = 100
        total_batches = (len(pending_recipients) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(pending_recipients))
            batch = pending_recipients[start_idx:end_idx]
            
            for recipient in batch:
                message = self.message
                
                if self.personalized:
                    message = message.replace('{name}', recipient.name or '')
                    message = message.replace('{admission_number}', recipient.admission_number or '')
                    message = message.replace('{staff_id}', recipient.staff_id or '')
                    recipient.personalized_message = message
                else:
                    recipient.personalized_message = message
                
                try:
                    success, result = gateway.send_sms(recipient.phone_number, message)
                    
                    if success:
                        actual_cost = 1.0
                        if isinstance(result, dict):
                            sms_data = result.get('SMSMessageData', {})
                            recipients_list = sms_data.get('Recipients', [])
                            if recipients_list:
                                cost_str = recipients_list[0].get('cost', 'KES 1.0')
                                try:
                                    actual_cost = float(cost_str.replace('KES', '').strip())
                                except:
                                    actual_cost = 1.0
                        
                        recipient.write({
                            'status': 'sent',
                            'sent_date': fields.Datetime.now(),
                            'cost': actual_cost,
                        })
                        self.sent_count += 1
                    else:
                        recipient.write({
                            'status': 'failed',
                            'error_message': str(result)
                        })
                        self.failed_count += 1
                        
                except Exception as e:
                    recipient.write({
                        'status': 'failed',
                        'error_message': str(e)
                    })
                    self.failed_count += 1
        
        if self.sent_count == len(self.recipient_ids):
            self.status = 'completed'
        elif self.sent_count > 0:
            self.status = 'completed'
        else:
            self.status = 'failed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Campaign Completed'),
                'message': _('Campaign completed!\n\n'
                           'Sent: %d\n'
                           'Failed: %d\n'
                           'Success Rate: %.1f%%') % (
                    self.sent_count, 
                    self.failed_count,
                    self.success_rate
                ),
                'type': 'success' if self.status == 'completed' else 'warning',
                'sticky': True,
            }
        }
    
    def action_schedule(self):
        """Schedule campaign for later"""
        self.ensure_one()
        
        if not self.schedule_date:
            raise UserError(_("Please set a schedule date first!"))
        
        if not self.recipient_ids:
            raise UserError(_("No recipients! Please prepare recipients first."))
        
        try:
            self._get_gateway()
        except UserError as e:
            raise UserError(
                _('Cannot schedule: %s\n\n'
                  'Please configure gateway before scheduling.') % str(e)
            )
        
        self.status = 'scheduled'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Campaign scheduled for %s') % self.schedule_date,
                'type': 'success',
            }
        }
    
    def action_cancel(self):
        """Cancel campaign"""
        self.ensure_one()
        self.status = 'cancelled'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Campaign cancelled'),
                'type': 'info',
            }
        }
    
    @api.model
    def cron_send_scheduled(self):
        """Cron job to send scheduled campaigns"""
        now = fields.Datetime.now()
        
        scheduled_campaigns = self.search([
            ('status', '=', 'scheduled'),
            ('schedule_date', '<=', now)
        ])
        
        for campaign in scheduled_campaigns:
            try:
                campaign.action_send()
            except Exception as e:
                _logger.error('Failed to send scheduled campaign %s: %s', 
                            campaign.name, str(e))
                campaign.write({
                    'status': 'failed',
                })