# models/res_users.py

from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help='Department this user belongs to for SMS filtering'
    )
    
    def get_sms_role(self):
        """
        Get SMS role for current user (not stored, computed on-demand)
        Returns string representing the user's SMS role
        """
        self.ensure_one()
        # Defensive: by convention, numeric logins represent student identities.
        # Students must never have SMS access, even if misconfigured into SMS groups.
        if self.login and str(self.login).isnumeric():
            return False
        
        # Check groups in priority order (highest to lowest)
        if self.has_group('su_sms.group_sms_system_admin'):
            return 'system_admin'
        elif self.has_group('su_sms.group_sms_administrator'):
            return 'administrator'
        elif self.has_group('su_sms.group_sms_faculty_admin'):
            return 'faculty_admin'
        elif self.has_group('su_sms.group_sms_department_admin'):
            return 'department_admin'
        elif self.has_group('su_sms.group_sms_basic_user'):
            return 'basic'
        else:
            return False
    
    def get_sms_role_display(self):
        """Get human-readable SMS role name"""
        self.ensure_one()
        role = self.get_sms_role()
        
        role_names = {
            'system_admin': 'SMS System Administrator',
            'administrator': 'SMS Administrator',
            'faculty_admin': 'SMS Faculty Administrator',
            'department_admin': 'SMS Department Administrator',
            'basic': 'SMS Basic User',
            False: 'No SMS Access'
        }
        
        return role_names.get(role, 'Unknown')
    
    def get_allowed_departments(self):
        """Get departments this user can send SMS to"""
        self.ensure_one()
        # Students (numeric logins) must never have SMS sending scope, regardless of groups.
        if self.login and str(self.login).isnumeric():
            return self.env['hr.department'].browse([])
        
        if self.has_group('su_sms.group_sms_system_admin') or \
           self.has_group('su_sms.group_sms_administrator'):
            # System Admin and Administrator can access all departments
            return self.env['hr.department'].search([])
        
        elif self.has_group('su_sms.group_sms_faculty_admin'):
            # Faculty Admin can access their faculty and sub-departments
            if self.department_id and self.department_id.is_school:
                return self.env['hr.department'].search([
                    '|',
                    ('id', '=', self.department_id.id),
                    ('parent_id', '=', self.department_id.id)
                ])
            return self.department_id
        
        elif self.has_group('su_sms.group_sms_department_admin'):
            # Department Admin can only access their department
            return self.department_id
        
        else:
            # Basic users have no department restrictions for ad hoc/manual
            return self.env['hr.department']
    
    def can_send_to_all_students(self):
        """Check if user can send to all students"""
        self.ensure_one()
        # Students must never have SMS permissions, even if misconfigured into SMS groups.
        if self.login and str(self.login).isnumeric():
            return False
        return self.has_group('su_sms.group_sms_faculty_admin') or \
               self.has_group('su_sms.group_sms_administrator') or \
               self.has_group('su_sms.group_sms_system_admin')
    
    def can_send_to_all_staff(self):
        """Check if user can send to all staff"""
        self.ensure_one()
        # Students must never have SMS permissions, even if misconfigured into SMS groups.
        if self.login and str(self.login).isnumeric():
            return False
        return self.has_group('su_sms.group_sms_department_admin') or \
               self.has_group('su_sms.group_sms_administrator') or \
               self.has_group('su_sms.group_sms_system_admin')
    
    def can_manage_configuration(self):
        """Check if user can manage system configuration"""
        self.ensure_one()
        # Students must never manage SMS configuration, regardless of group misconfiguration.
        if self.login and str(self.login).isnumeric():
            return False
        return self.has_group('su_sms.group_sms_system_admin')