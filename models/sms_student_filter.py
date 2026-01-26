# models/sms_student_filter.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SMSStudentFilter(models.TransientModel):
    _name = 'sms.student.filter'
    _description = 'Student SMS Filter Wizard'
    
    administrator_id = fields.Many2one('res.users', string='Send As', default=lambda self: self.env.user)
    school_id = fields.Many2one('hr.department', string='School', domain=[('is_school', '=', True)])
    program_id = fields.Many2one('student.program', string='Program')
    course_id = fields.Many2one('student.course', string='Course')
    academic_year_id = fields.Many2one('student.academic.year', string='Academic Year')
    student_year = fields.Selection([
        ('all', 'All Student Years'),
        ('1', 'Year 1'), ('2', 'Year 2'), ('3', 'Year 3'),
        ('4', 'Year 4'), ('5', 'Year 5'), ('6', 'Year 6')
    ], string='Student Year', default='all')
    enrolment_period_id = fields.Many2one('student.enrolment.period', string='Enrolment Period')
    module_id = fields.Many2one('student.module', string='Module')
    intake_id = fields.Many2one('student.intake', string='Intake')
    send_to_students = fields.Boolean(string='Students', default=True)
    send_to_fathers = fields.Boolean(string='Fathers')
    send_to_mothers = fields.Boolean(string='Mothers')
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
        
        WebService = self.env['sms.webservice.adapter']
        students_list = WebService._get_students(
            school_id=self.school_id.id if self.school_id else None,
            student_year=self.student_year if self.student_year != 'all' else '9999',
        )
        
        if not students_list:
            raise UserError(_('No students found matching your criteria.'))
        
        campaign = self.env['sms.campaign'].create({
            'name': _('Student SMS - %s') % fields.Datetime.now().strftime('%Y-%m-%d %H:%M'),
            'sms_type_id': self.env.ref('su_sms.sms_type_student').id,
            'message': self.message,
            'target_type': 'all_students',
            'administrator_id': self.administrator_id.id,
            'status': 'draft',
        })
        
        Gateway = self.env['sms.gateway.configuration']
        for student in students_list:
            if self.send_to_students and student.get('mobileNo'):
                try:
                    phone = Gateway.normalize_phone_number(student['mobileNo'])
                    self.env['sms.recipient'].create({
                        'campaign_id': campaign.id,
                        'name': student['studentNames'],
                        'phone_number': phone,
                        'email': student.get('email'),
                        'admission_number': student.get('studentNo'),
                        'recipient_type': 'student',
                        'year_of_study': student.get('studentYear'),
                        'status': 'pending',
                    })
                except:
                    continue
            
            if self.send_to_fathers and student.get('fatherMobileNo'):
                try:
                    phone = Gateway.normalize_phone_number(student['fatherMobileNo'])
                    self.env['sms.recipient'].create({
                        'campaign_id': campaign.id,
                        'name': f"Father of {student['studentNames']}",
                        'phone_number': phone,
                        'recipient_type': 'parent',
                        'status': 'pending',
                    })
                except:
                    continue
            
            if self.send_to_mothers and student.get('motherMobileNo'):
                try:
                    phone = Gateway.normalize_phone_number(student['motherMobileNo'])
                    self.env['sms.recipient'].create({
                        'campaign_id': campaign.id,
                        'name': f"Mother of {student['studentNames']}",
                        'phone_number': phone,
                        'recipient_type': 'parent',
                        'status': 'pending',
                    })
                except:
                    continue
        
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