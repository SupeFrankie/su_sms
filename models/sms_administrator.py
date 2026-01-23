# models/sms_administrator.py 

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SMSAdministrator(models.Model):
    """
    SMS Administrator Model
    PHP equivalent: administrators table
    
    Separate from res.users - links user to department for billing
    """
    _name = 'sms.administrator'
    _description = 'SMS Administrator'
    _order = 'name'
    
    # Core fields (from PHP)
    user_id = fields.Many2one(
        'res.users', 
        string='User', 
        required=True, 
        ondelete='cascade', 
        index=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Finance Department',
        required=True,
        ondelete='restrict',
        help='Department for SMS billing (KFS5)'
    )
    
    phone = fields.Char(
        string='Admin Phone',
        help='Administrator phone (receives copy of sent SMS)'
    )
    
    active = fields.Boolean(default=True)
    
    # Related fields (from user)
    name = fields.Char(
        related='user_id.name',
        string='Name',
        store=True,
        readonly=True
    )
    
    email = fields.Char(
        related='user_id.email',
        string='Email',
        readonly=True
    )
    
    username = fields.Char(
        related='user_id.login',
        string='Username',
        store=True,
        readonly=True,
        index=True
    )
    
    # Role info
    role_id = fields.Many2one(
        'res.groups',
        string='SMS Role',
        compute='_compute_role',
        store=True
    )
    
    role_name = fields.Char(
        string='Role',
        compute='_compute_role',
        store=True
    )
    
    # Statistics
    message_ids = fields.One2many(
        'sms.campaign',
        'administrator_id',
        string='Sent Messages'
    )
    
    total_messages = fields.Integer(
        string='Total Messages',
        compute='_compute_totals'
    )
    
    total_spent = fields.Float(
        string='Total Spent',
        compute='_compute_totals'
    )
    
    @api.depends('user_id.groups_id')
    def _compute_role(self):
        """Compute SMS role from user groups"""
        for admin in self:
            user = admin.user_id
            if user.has_group('su_sms.group_sms_system_admin'):
                admin.role_name = 'System Administrator'
                admin.role_id = self.env.ref('su_sms.group_sms_system_admin')
            elif user.has_group('su_sms.group_sms_administrator'):
                admin.role_name = 'Administrator'
                admin.role_id = self.env.ref('su_sms.group_sms_administrator')
            elif user.has_group('su_sms.group_sms_faculty_admin'):
                admin.role_name = 'Faculty Administrator'
                admin.role_id = self.env.ref('su_sms.group_sms_faculty_admin')
            elif user.has_group('su_sms.group_sms_department_admin'):
                admin.role_name = 'Staff Administrator'
                admin.role_id = self.env.ref('su_sms.group_sms_department_admin')
            else:
                admin.role_name = 'Basic User'
                admin.role_id = self.env.ref('su_sms.group_sms_basic_user')
    
    @api.constrains('user_id', 'department_id')
    def _check_unique_user_department(self):
        """
        User can have multiple administrator records for different departments
        But only one per department (unlike PHP which enforces one total)
        """
        for admin in self:
            existing = self.search([
                ('user_id', '=', admin.user_id.id),
                ('department_id', '=', admin.department_id.id),
                ('id', '!=', admin.id)
            ], limit=1)
            if existing:
                raise ValidationError(_(
                    'User %s already has an administrator record for department %s!'
                ) % (admin.user_id.name, admin.department_id.name))
    
    @api.depends('message_ids')
    def _compute_totals(self):
        """Compute total messages and cost"""
        for admin in self:
            admin.total_messages = len(admin.message_ids)
            admin.total_spent = sum(admin.message_ids.mapped('total_cost'))
    
    def action_view_messages(self):
        """View all SMS messages sent by this administrator"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Messages - %s') % self.name,
            'res_model': 'sms.campaign',
            'view_mode': 'tree,form',
            'domain': [('administrator_id', '=', self.id)],
            'context': {'default_administrator_id': self.id}
        }
    
    @api.model
    def get_or_create_for_user(self, user_id=None, department_id=None):
        """
        Get or create administrator record for user
        PHP equivalent: AdministratorsController::store()
        
        Returns administrator record for current user or creates one
        """
        if not user_id:
            user_id = self.env.user.id
        
        if not department_id:
            user = self.env['res.users'].browse(user_id)
            department_id = user.department_id.id if user.department_id else False
        
        if not department_id:
            raise ValidationError(_('Cannot create administrator without department!'))
        
        admin = self.search([
            ('user_id', '=', user_id),
            ('department_id', '=', department_id)
        ], limit=1)
        
        if not admin:
            user = self.env['res.users'].browse(user_id)
            phone = user.partner_id.mobile or user.partner_id.phone
            
            admin = self.create({
                'user_id': user_id,
                'department_id': department_id,
                'phone': phone,
            })
        
        return admin
    
    @api.model
    def create(self, vals):
        """Auto-populate phone from user if not provided"""
        if 'phone' not in vals and vals.get('user_id'):
            user = self.env['res.users'].browse(vals['user_id'])
            vals['phone'] = user.partner_id.mobile or user.partner_id.phone
        
        return super().create(vals)