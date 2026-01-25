from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help='Department this user belongs to for SMS purposes'
    )
    
    sms_role = fields.Selection([
        ('basic', 'Basic User'),
        ('department_admin', 'Department Administrator'),
        ('faculty_admin', 'Faculty Administrator'),
        ('administrator', 'Administrator'),
        ('system_admin', 'System Administrator'),
    ], string='SMS Role', default='basic')
    
    @api.depends('groups_id')
    def _compute_sms_role(self):
        """Compute SMS role based on security groups"""
        for user in self:
            if user.has_group('su_sms.group_sms_system_admin'):
                user.sms_role = 'system_admin'
            elif user.has_group('su_sms.group_sms_administrator'):
                user.sms_role = 'administrator'
            elif user.has_group('su_sms.group_sms_faculty_admin'):
                user.sms_role = 'faculty_admin'
            elif user.has_group('su_sms.group_sms_department_admin'):
                user.sms_role = 'department_admin'
            elif user.has_group('su_sms.group_sms_basic_user'):
                user.sms_role = 'basic'
            else:
                user.sms_role = False
    
    def get_allowed_departments(self):
        """Get departments this user can send SMS to"""
        self.ensure_one()
        
        if self.has_group('su_sms.group_sms_system_admin') or \
           self.has_group('su_sms.group_sms_administrator'):
            return self.env['hr.department'].search([])
        
        elif self.has_group('su_sms.group_sms_faculty_admin'):
            if self.department_id and self.department_id.is_school:
                return self.env['hr.department'].search([
                    '|',
                    ('id', '=', self.department_id.id),
                    ('parent_id', '=', self.department_id.id)
                ])
            return self.department_id
        
        elif self.has_group('su_sms.group_sms_department_admin'):
            return self.department_id
        
        else:
            return self.env['hr.department']
    
    def can_send_to_all_students(self):
        """Check if user can send to all students"""
        self.ensure_one()
        return self.has_group('su_sms.group_sms_faculty_admin') or \
               self.has_group('su_sms.group_sms_administrator') or \
               self.has_group('su_sms.group_sms_system_admin')
    
    def can_send_to_all_staff(self):
        """Check if user can send to all staff"""
        self.ensure_one()
        return self.has_group('su_sms.group_sms_administrator') or \
               self.has_group('su_sms.group_sms_system_admin')
    
    def can_manage_configuration(self):
        """Check if user can manage system configuration"""
        self.ensure_one()
        return self.has_group('su_sms.group_sms_system_admin')