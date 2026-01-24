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
        ('mailing_list', 'Mailing List'),
        ('adhoc', 'Ad Hoc (CSV Upload)'),
        ('manual', 'Manual Numbers'),
    ], string='Target Audience', required=True)
    
    department_id = fields.Many2one(
        'hr.department',
        string='Billing Department',
        store=True,
        help='Department for billing purposes'
    )
    
    mailing_list_id = fields.Many2one('sms.mailing.list', 'Mailing List')
    
    import_file = fields.Binary(string='CSV File')
    import_filename = fields.Char(string='Filename')
    manual_numbers = fields.Text(string='Manual Numbers')
    
    recipient_ids = fields.One2many('sms.recipient', 'campaign_id', 'Recipients')
    total_recipients = fields.Integer('Total Recipients', compute='_compute_recipient_stats', store=True)
    pending_count = fields.Integer('Pending', compute='_compute_recipient_stats', store=True)
    
    send_immediately = fields.Boolean('Send Immediately', default=True)
    schedule_date = fields.Datetime('Scheduled Send Time')
    
    sent_count = fields.Integer('Sent', readonly=True, default=0)
    failed_count = fields.Integer('Failed', readonly=True, default=0)
    delivered_count = fields.Integer('Delivered', readonly=True, default=0)
    
    success_rate = fields.Float('Success Rate', compute='_compute_success_rate', store=True)
    
    gateway_id = fields.Many2one(
        'sms.gateway.configuration', 
        'SMS Gateway',
        default=lambda self: self.env['sms.gateway.configuration'].search([
            ('is_default', '=', True),
            ('active', '=', True)
        ], limit=1)
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
    
    @api.onchange('administrator_id')
    def _onchange_administrator_id(self):
        if self.administrator_id and self.administrator_id.department_id:
            self.department_id = self.administrator_id.department_id
    
    @api.depends('message')
    def _compute_message_length(self):
        for campaign in self:
            campaign.message_length = len(campaign.message) if campaign.message else 0
    
    @api.depends('recipient_ids', 'recipient_ids.status')
    def _compute_recipient_stats(self):
        for campaign in self:
            campaign.total_recipients = len(campaign.recipient_ids)
            campaign.pending_count = len(campaign.recipient_ids.filtered(lambda r: r.status == 'pending'))
    
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
    
    def action_prepare_recipients(self):
        self.ensure_one()
        
        if not self._check_user_permission():
            raise exceptions.UserError(_('You do not have permission to send to this audience.'))
        
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
            if self.target_type == 'department':
                user_dept = user.department_id if hasattr(user, 'department_id') else False
                if self.department_id == user_dept:
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
        recipients = []
        
        domain = [
            ('contact_type', '=', 'staff'),
            ('active', '=', True),
            ('opt_in', '=', True)
        ]
        
        if self.env.user.has_group('su_sms.group_sms_department_admin') and \
           not self.env.user.has_group('su_sms.group_sms_administrator'):
            if hasattr(self.env.user, 'department_id') and self.env.user.department_id:
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
        if not self.department_id:
            raise exceptions.UserError(_("Please select a department"))
        
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
    
    def _get_mailing_list_contacts(self):
        if not self.mailing_list_id:
            raise exceptions.UserError(_("Please select a mailing list"))
        
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
        if not self.import_file:
            raise exceptions.UserError(_("Please upload a CSV file"))
        
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
                raise exceptions.UserError(error_msg)
        
        except Exception as e:
            raise exceptions.UserError(_('Error processing CSV file: %s') % str(e))
        
        return recipients
    
    def _process_manual_numbers(self):
        if not self.manual_numbers:
            raise exceptions.UserError(_("Please enter phone numbers"))
        
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
        return not self.env['sms.blacklist'].is_blacklisted(phone)
    
    def action_send(self):
        self.ensure_one()
        
        if not self.recipient_ids:
            raise exceptions.UserError(_("No recipients! Please prepare recipients first."))
        
        if not self.gateway_id:
            raise exceptions.UserError(_("No SMS gateway configured!"))
        
        self.status = 'in_progress'
        
        pending_recipients = self.recipient_ids.filtered(lambda r: r.status == 'pending')
        
        batch_size = 100
        for i in range(0, len(pending_recipients), batch_size):
            batch = pending_recipients[i:i+batch_size]
            
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
                    success, result = self.gateway_id.send_sms(recipient.phone_number, message)
                    
                    if success:
                        recipient.write({
                            'status': 'sent',
                            'sent_date': fields.Datetime.now()
                        })
                        self.sent_count += 1
                    else:
                        recipient.write({
                            'status': 'failed',
                            'error_message': str(result)
                        })
                        self.failed_count += 1
                        
                except Exception as e:
                    _logger.error(f"Error sending SMS to {recipient.phone_number}: {str(e)}")
                    recipient.write({
                        'status': 'failed',
                        'error_message': str(e)
                    })
                    self.failed_count += 1
        
        self.status = 'completed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Campaign completed! %d sent, %d failed') % (self.sent_count, self.failed_count),
                'type': 'success',
                'sticky': True,
            }
        }
    
    def action_schedule(self):
        self.ensure_one()
        
        if not self.schedule_date:
            raise exceptions.UserError(_("Please set a schedule date first!"))
        
        if not self.recipient_ids:
            raise exceptions.UserError(_("No recipients! Please prepare recipients first."))
        
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
    
    def action_download_template(self):
        """Download CSV template for ad hoc SMS"""
        self.ensure_one()
        
        csv_content = "name,number\n"
        csv_content += "John Doe,+254712345678\n"
        csv_content += "Jane Smith,+254723456789\n"
        csv_content += "Bob Johnson,+254734567890\n"
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'data:text/csv;charset=utf-8,{csv_content}',
            'target': 'download',
        }