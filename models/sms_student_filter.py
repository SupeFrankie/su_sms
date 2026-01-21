# models/sms_student_filter.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SMSStudentFilter(models.TransientModel):
    _name = 'sms.student.filter'
    _description = 'Student SMS Filter Wizard'
    
    administrator_id = fields.Many2one(
        'res.users',
        string='Send As',
        default=lambda self: self.env.user
    )
    
    # School/Faculty
    school_id = fields.Many2one(
        'hr.department',
        string='School',
        domain=[('is_school', '=', True)]
    )
    
    # Program
    program_id = fields.Many2one(
        'student.program',
        string='Program',
        domain="[('school_id', '=', school_id)]"
    )
    
    # Course
    course_id = fields.Many2one(
        'student.course',
        string='Course',
        domain="[('program_id', '=', program_id)]"
    )
    
    # Academic Programs
    academic_year_id = fields.Many2one(
        'student.academic.year',
        string='Academic Year'
    )
    
    student_year = fields.Selection([
        ('all', 'All Student Years'),
        ('1', 'Year 1'),
        ('2', 'Year 2'),
        ('3', 'Year 3'),
        ('4', 'Year 4'),
        ('5', 'Year 5'),
        ('6', 'Year 6')
    ], string='Student Year', default='all')
    
    # Modular Programs
    enrolment_period_id = fields.Many2one(
        'student.enrolment.period',
        string='Enrolment Period'
    )
    
    module_id = fields.Many2one(
        'student.module',
        string='Module'
    )
    
    # Intake
    intake_id = fields.Many2one(
        'student.intake',
        string='Intake'
    )
    
    # Recipient Groups
    send_to_students = fields.Boolean(string='Students', default=True)
    send_to_fathers = fields.Boolean(string='Fathers')
    send_to_mothers = fields.Boolean(string='Mothers')
    
    # Message
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
    
    def action_view_recipients(self):
        """Preview recipients before sending"""
        self.ensure_one()
        
        # Build domain for student filtering
        # This would integrate with student information system
        # For now, show notification
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student SMS'),
                'message': _('Student information system integration required. This feature will filter students based on:\n- School: %s\n- Program: %s\n- Course: %s\n- Academic Year: %s\n- Student Year: %s\n- Intake: %s\n- Recipients: %s') % (
                    self.school_id.name if self.school_id else 'All',
                    self.program_id.name if self.program_id else 'All',
                    self.course_id.name if self.course_id else 'All',
                    self.academic_year_id.name if self.academic_year_id else 'All',
                    dict(self._fields['student_year'].selection).get(self.student_year, 'All'),
                    self.intake_id.name if self.intake_id else 'All',
                    ', '.join([x for x in ['Students' if self.send_to_students else '', 'Fathers' if self.send_to_fathers else '', 'Mothers' if self.send_to_mothers else ''] if x])
                ),
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_send_sms(self):
        """Send SMS to filtered students"""
        self.ensure_one()
        
        if not self.message:
            raise UserError(_('Message is required.'))
        
        # Create campaign
        campaign = self.env['sms.campaign'].create({
            'name': _('Student SMS - %s') % fields.Datetime.now(),
            'sms_type_id': self.env.ref('su_sms.sms_type_student').id,
            'message': self.message,
            'target_type': 'all_students',
            'administrator_id': self.administrator_id.id,
        })
        
        # Prepare and send
        campaign.action_prepare_recipients()
        
        return campaign.action_send()


class StudentProgram(models.Model):
    _name = 'student.program'
    _description = 'Student Program'
    
    name = fields.Char(string='Program Name', required=True)
    code = fields.Char(string='Program Code')
    school_id = fields.Many2one('hr.department', string='School')
    active = fields.Boolean(default=True)


class StudentCourse(models.Model):
    _name = 'student.course'
    _description = 'Student Course'
    
    name = fields.Char(string='Course Name', required=True)
    short_name = fields.Char(string='Short Name')
    program_id = fields.Many2one('student.program', string='Program')
    active = fields.Boolean(default=True)


class StudentAcademicYear(models.Model):
    _name = 'student.academic.year'
    _description = 'Academic Year'
    
    name = fields.Char(string='Academic Year', required=True)
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    active = fields.Boolean(default=True)


class StudentEnrolmentPeriod(models.Model):
    _name = 'student.enrolment.period'
    _description = 'Enrolment Period'
    
    name = fields.Char(string='Enrolment Period', required=True)
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    active = fields.Boolean(default=True)


class StudentModule(models.Model):
    _name = 'student.module'
    _description = 'Student Module'
    
    name = fields.Char(string='Module Name', required=True)
    code = fields.Char(string='Module Code')
    active = fields.Boolean(default=True)


class StudentIntake(models.Model):
    _name = 'student.intake'
    _description = 'Student Intake'
    
    name = fields.Char(string='Intake Name', required=True)
    year = fields.Integer(string='Year')
    active = fields.Boolean(default=True)