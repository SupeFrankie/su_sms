# models/res_users.py

from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    sms_role = fields.Selection([
        ('basic', 'Basic User'),
        ('department_admin', 'Department Administrator'),
        ('faculty_admin', 'Faculty Administrator'),
        ('administrator', 'Administrator'),
        ('system_admin', 'System Administrator'),
    ], string='SMS Role', compute='_compute_sms_role', store=False)
    
    def _compute_sms_role(self):
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
        
        return self.env['hr.department']
    
    def can_send_to_all_students(self):
        self.ensure_one()
        return self.has_group('su_sms.group_sms_faculty_admin') or \
               self.has_group('su_sms.group_sms_administrator') or \
               self.has_group('su_sms.group_sms_system_admin')
    
    def can_send_to_all_staff(self):
        self.ensure_one()
        return self.has_group('su_sms.group_sms_administrator') or \
               self.has_group('su_sms.group_sms_system_admin')
    
    def can_manage_configuration(self):
        self.ensure_one()
        return self.has_group('su_sms.group_sms_system_admin')