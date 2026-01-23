# models/sms_contact.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class SMSContact(models.Model):
    
    _name = 'sms.contact'
    _description = 'SMS Contact'
    _order = 'name'
    _rec_name = 'name'
    
    name = fields.Char(string='Full Name', required=True, index=True)
    mobile = fields.Char(string='Mobile Number', required=True, index=True)
    email = fields.Char(string='Email')
    
    contact_type = fields.Selection([
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('external', 'External')
    ], string='Contact Type', required=True, default='student', index=True)
    
    # Demographics
    gender = fields.Selection([
        ('all', 'All'),
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender', index=True)
    
    student_id = fields.Char(string='Student/Staff ID', index=True)
    
    department_id = fields.Many2one('hr.department', string='Department', index=True)
    
    tag_ids = fields.Many2many('sms.tag', string='Tags')
    
    opt_in = fields.Boolean(string='Opt-in', default=True)
    opt_in_date = fields.Datetime(string='Opt-in Date', readonly=True)
    opt_out_date = fields.Datetime(string='Opt-out Date', readonly=True)
    
    blacklisted = fields.Boolean(string='Blacklisted', compute='_compute_blacklisted', store=True)
    
    mailing_list_ids = fields.Many2many('sms.mailing.list', string='Mailing Lists')
    
    messages_sent = fields.Integer(string='Messages Sent', compute='_compute_messages_sent', store=True)
    last_message_date = fields.Datetime(string='Last Message Date', readonly=True)
    
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
    
    partner_id = fields.Many2one('res.partner', string='Related Contact')
    
    @api.depends('mobile')
    def _compute_blacklisted(self):
        Blacklist = self.env['sms.blacklist']
        for contact in self:
            clean_mobile = self._clean_phone(contact.mobile)
            contact.blacklisted = bool(
                Blacklist.search([('phone_number', '=', clean_mobile), ('active', '=', True)], limit=1)
            )
    
    @api.depends('mailing_list_ids')
    def _compute_messages_sent(self):
        Message = self.env['sms.message']
        for contact in self:
            contact.messages_sent = Message.search_count([('contact_ids', 'in', contact.id)])
    
    @api.constrains('mobile')
    def _check_mobile(self):
        for contact in self:
            if not contact.mobile:
                raise ValidationError(_('Mobile number is required.'))
            
            clean_mobile = self._clean_phone(contact.mobile)
            
            duplicate = self.search([
                ('mobile', '=', clean_mobile),
                ('id', '!=', contact.id)
            ], limit=1)
            
            if duplicate:
                raise ValidationError(_(
                    'A contact with mobile number %s already exists: %s'
                ) % (clean_mobile, duplicate.name))
    
    @api.model
    def _clean_phone(self, phone):
        """Normalize phone number to E.164 format"""
        if not phone:
            return ''
        
        phone = re.sub(r'[\s\-\(\)\.]', '', str(phone).strip())
        
        if phone.startswith('+'):
            return phone
        
        if phone.startswith('0') and len(phone) == 10:
            return '+254' + phone[1:]
        elif phone.startswith('254') and len(phone) == 12:
            return '+' + phone
        elif len(phone) == 9:
            return '+254' + phone
        else:
            return '+' + phone
    
    def action_opt_in(self):
        self.ensure_one()
        self.write({'opt_in': True, 'opt_in_date': fields.Datetime.now()})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('%s has been opted in.') % self.name,
                'type': 'success',
            }
        }
    
    def action_opt_out(self):
        self.ensure_one()
        self.write({'opt_in': False, 'opt_out_date': fields.Datetime.now()})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('%s has been opted out.') % self.name,
                'type': 'info',
            }
        }
    
    def action_add_to_blacklist(self):
        self.ensure_one()
        Blacklist = self.env['sms.blacklist']
        
        if self.blacklisted:
            raise ValidationError(_('This contact is already blacklisted.'))
        
        Blacklist.create({
            'phone_number': self._clean_phone(self.mobile),
            'reason': 'manual',
            'notes': _('Added from contact: %s') % self.name,
        })
        
        self._compute_blacklisted()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('%s has been blacklisted.') % self.name,
                'type': 'warning',
            }
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('opt_in') and 'opt_in_date' not in vals:
                vals['opt_in_date'] = fields.Datetime.now()
            if not vals.get('opt_in') and 'opt_out_date' not in vals:
                vals['opt_out_date'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if 'mobile' in vals:
            vals['mobile'] = self._clean_phone(vals['mobile'])
        
        if 'opt_in' in vals:
            if vals['opt_in']:
                vals['opt_in_date'] = fields.Datetime.now()
            else:
                vals['opt_out_date'] = fields.Datetime.now()
        
        return super().write(vals)


class SMSTag(models.Model):
    _name = 'sms.tag'
    _description = 'SMS Tag'
    _order = 'name'
    
    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color', help='Color index for UI')
    active = fields.Boolean(default=True)