# models/sms_compose_wizard.py 

"""
Basicaly allows selection types for (1)Adhoc sms(2)Staff sms(3)Manual sms(4)Student sms

Different from models/sms_composer.py 
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SMSComposeWizard(models.TransientModel):
    _name = 'sms.compose.wizard'
    _description = 'SMS Compose Wizard (5 Steps)'
    
    # Step 1: Select SMS Type
    sms_type = fields.Selection([
        ('adhoc', 'Ad Hoc SMS'),
        ('student', 'Student SMS'),
        ('staff', 'Staff SMS'),
        ('manual', 'Manual SMS'),
    ], string='SMS Type', required=True)
    
    # Step 2: Configure Recipients
    # For Ad Hoc
    import_file = fields.Binary(string='CSV File')
    import_filename = fields.Char()
    
    # For Manual
    manual_numbers = fields.Text(string='Phone Numbers')
    
    # For Students
    school_id = fields.Many2one('student.school', string='School')
    program_id = fields.Many2one('student.program', string='Program')
    course_id = fields.Many2one('student.course', string='Course')
    
    # For Staff
    department_id = fields.Many2one('hr.department', string='Department')
   
    # Step 3: Preview Recipients
    preview_recipient_ids = fields.Many2many('sms.recipient', string='Preview Recipients')
    recipient_count = fields.Integer(compute='_compute_recipient_count')
    
    # Step 4: Compose Message
    message = fields.Text(string='Message', required=True)
    message_length = fields.Integer(compute='_compute_message_length')
    sms_count = fields.Integer(compute='_compute_sms_count')
    template_id = fields.Many2one('sms.template', string='Use Template')
    
    # Step 5: Review & Send
    gateway_id = fields.Many2one('sms.gateway.configuration', string='Gateway')
    estimated_cost = fields.Float(compute='_compute_estimated_cost')
    
    # Wizard State
    current_step = fields.Selection([
        ('1', 'Select Type'),
        ('2', 'Configure Recipients'),
        ('3', 'Preview'),
        ('4', 'Compose'),
        ('5', 'Review'),
    ], default='1')
    
    @api.depends('preview_recipient_ids')
    def _compute_recipient_count(self):
        for wizard in self:
            wizard.recipient_count = len(wizard.preview_recipient_ids)
    
    @api.depends('message')
    def _compute_message_length(self):
        for wizard in self:
            wizard.message_length = len(wizard.message or '')
    
    @api.depends('message_length')
    def _compute_sms_count(self):
        for wizard in self:
            length = wizard.message_length
            if length == 0:
                wizard.sms_count = 0
            elif length <= 160:
                wizard.sms_count = 1
            else:
                wizard.sms_count = 1 + ((length - 160 + 152) // 153)
    
    @api.depends('recipient_count', 'sms_count')
    def _compute_estimated_cost(self):
        for wizard in self:
            wizard.estimated_cost = wizard.recipient_count * wizard.sms_count * 1.0
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.message = self.template_id.message
    
    def action_next_step(self):
        self.ensure_one()
        step_map = {'1': '2', '2': '3', '3': '4', '4': '5'}
        
        if self.current_step == '2':
            self._load_recipients()
        
        self.current_step = step_map.get(self.current_step, '5')
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sms.compose.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_previous_step(self):
        self.ensure_one()
        step_map = {'5': '4', '4': '3', '3': '2', '2': '1'}
        self.current_step = step_map.get(self.current_step, '1')
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sms.compose.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _load_recipients(self):
        self.ensure_one()
        recipients = []
        
        if self.sms_type == 'manual' and self.manual_numbers:
            numbers = [n.strip() for n in self.manual_numbers.split(',')]
            for number in numbers:
                if number:
                    recipients.append((0, 0, {
                        'phone_number': number,
                        'name': number,
                    }))
        
        elif self.sms_type == 'adhoc' and self.import_file:
            import csv
            import base64
            import io
            
            file_content = base64.b64decode(self.import_file)
            csv_reader = csv.DictReader(io.StringIO(file_content.decode('utf-8')))
            
            for row in csv_reader:
                recipients.append((0, 0, {
                    'phone_number': row.get('number', row.get('phone', '')),
                    'name': row.get('name', ''),
                }))
        
        self.preview_recipient_ids = recipients
    
    def action_send_sms(self):
        self.ensure_one()
        
        if not self.preview_recipient_ids:
            raise ValidationError('No recipients to send to!')
        
        campaign = self.env['sms.campaign'].create({
            'name': f"{self.sms_type.upper()} SMS - {fields.Datetime.now()}",
            'message': self.message,
            'sms_type_id': self.env['sms.type'].search([('code', '=', self.sms_type)], limit=1).id,
            'gateway_id': self.gateway_id.id,
            'recipient_ids': [(0, 0, {
                'name': r.name,
                'phone_number': r.phone_number,
            }) for r in self.preview_recipient_ids],
        })
        
        campaign.action_send()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sms.campaign',
            'res_id': campaign.id,
            'view_mode': 'form',
            'target': 'current',
        }