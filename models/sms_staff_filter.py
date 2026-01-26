# models/sms_staff_filter.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SMSStaffFilter(models.TransientModel):
    _name = 'sms.staff.filter'
    _description = 'Staff SMS Filter Wizard'
    
    administrator_id = fields.Many2one('res.users', string='Send As', default=lambda self: self.env.user)
    department_id = fields.Many2one('hr.department', string='Department')
    gender = fields.Selection([('all', 'All Genders'), ('male', 'Male'), ('female', 'Female')], string='Gender', default='all')
    category = fields.Selection([('all', 'All Staff'), ('academic', 'Academic'), ('administrative', 'Administrative')], string='Category', default='all')
    job_status_type = fields.Selection([('all', 'All Staff'), ('ft', 'Full Time'), ('pt', 'Part Time'), ('in', 'Interns')], string='Job Type', default='all')
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
    
    def action_send_sms(self):
        self.ensure_one()
        
        if not self.message:
            raise UserError(_('Message is required.'))
        
        # Get staff from mock webservice
        WebService = self.env['sms.webservice.adapter']
        staff_list = WebService._get_staff(
            department_id=self.department_id.id if self.department_id else None,
            gender_id='1' if self.gender == 'male' else '2' if self.gender == 'female' else '9999',
            category_id='1' if self.category == 'academic' else '2' if self.category == 'administrative' else '9999',
            job_status_type=self.job_status_type if self.job_status_type != 'all' else '9999'
        )
        
        if not staff_list:
            raise UserError(_('No staff found matching your criteria.'))
        
        # Create campaign
        campaign = self.env['sms.campaign'].create({
            'name': _('Staff SMS - %s') % fields.Datetime.now().strftime('%Y-%m-%d %H:%M'),
            'sms_type_id': self.env.ref('su_sms.sms_type_staff').id,
            'message': self.message,
            'target_type': 'all_staff',
            'department_id': self.department_id.id if self.department_id else False,
            'administrator_id': self.administrator_id.id,
            'status': 'draft',
        })
        
        # Create recipients
        Gateway = self.env['sms.gateway.configuration']
        for staff in staff_list:
            try:
                phone = Gateway.normalize_phone_number(staff['mobileNo'])
                self.env['sms.recipient'].create({
                    'campaign_id': campaign.id,
                    'name': f"{staff['firstName']} {staff['lastName']}",
                    'phone_number': phone,
                    'email': staff.get('email'),
                    'staff_id': staff.get('staffId'),
                    'department': staff.get('departmentName'),
                    'recipient_type': 'staff',
                    'status': 'pending',
                })
            except Exception as e:
                continue
        
        # Send immediately
        return campaign.action_send()