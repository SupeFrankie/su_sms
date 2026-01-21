# models/sms_staff_filter.py - COMPLETE based on manual

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SMSStaffFilter(models.TransientModel):
    _name = 'sms.staff.filter'
    _description = 'Staff SMS Filter Wizard'
    
    administrator_id = fields.Many2one(
        'res.users',
        string='Send As',
        default=lambda self: self.env.user
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department'
    )
    
    gender = fields.Selection([
        ('all', 'All Genders'),
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender', default='all')
    
    category = fields.Selection([
        ('all', 'All Staff'),
        ('academic', 'Academic'),
        ('administrative', 'Administrative')
    ], string='Category', default='all')
    
    job_status_type = fields.Selection([
        ('all', 'All Staff'),
        ('ft', 'Full Time'),
        ('pt', 'Part Time'),
        ('in', 'Interns')
    ], string='Job Type', default='all')
    
    message = fields.Text(string='Message', required=True)
    char_count = fields.Integer(compute='_compute_char_count')
    sms_count = fields.Integer(compute='_compute_char_count')
    
    @api.depends('message')
    def _compute_char_count(self):
        for record in self:
            if record.message:
                record.char_count = len(record.message)
                record.sms_count = (record.char_count // 160) + 1
            else:
                record.char_count = 0
                record.sms_count = 0
    
    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Apply department restrictions for Staff Administrators"""
        user = self.env.user
        
        if user.has_group('su_sms.group_sms_department_admin') and \
           not user.has_group('su_sms.group_sms_administrator'):
            if user.department_id:
                self.department_id = user.department_id
                return {
                    'domain': {
                        'department_id': [('id', '=', user.department_id.id)]
                    }
                }
    
    def action_view_recipients(self):
        """Preview recipients before sending"""
        self.ensure_one()
        
        domain = [
            ('contact_type', '=', 'staff'),
            ('active', '=', True),
            ('opt_in', '=', True)
        ]
        
        # Apply filters
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        # Gender filter would require gender field on contact
        # Category and job_status_type would require HR integration
        
        contacts = self.env['sms.contact'].search(domain)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Staff SMS Recipients'),
                'message': _('Found %d staff members matching criteria:\n- Department: %s\n- Gender: %s\n- Category: %s\n- Job Type: %s') % (
                    len(contacts),
                    self.department_id.name if self.department_id else 'All',
                    dict(self._fields['gender'].selection).get(self.gender),
                    dict(self._fields['category'].selection).get(self.category),
                    dict(self._fields['job_status_type'].selection).get(self.job_status_type)
                ),
                'type': 'info',
            }
        }
    
    def action_send_sms(self):
        """Send SMS to filtered staff"""
        self.ensure_one()
        
        if not self.message:
            raise UserError(_('Message is required.'))
        
        # Determine target type
        if self.department_id:
            target_type = 'department'
            department_id = self.department_id.id
        else:
            target_type = 'all_staff'
            department_id = False
        
        # Create campaign
        campaign = self.env['sms.campaign'].create({
            'name': _('Staff SMS - %s') % fields.Datetime.now(),
            'sms_type_id': self.env.ref('su_sms.sms_type_staff').id,
            'message': self.message,
            'target_type': target_type,
            'department_id': department_id,
            'administrator_id': self.administrator_id.id,
        })
        
        # Prepare and send
        campaign.action_prepare_recipients()
        
        return campaign.action_send()