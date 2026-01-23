# models/mock_webservice.py
"""
Mock Web Service Adapter
=========================

Replaces external web service calls with mock data for testing.
When real web service is available, swap with real API calls.
"""

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class MockWebService:
    """Simulates the external student/staff web service"""
    
    @staticmethod
    def get_all_students():
        """Mock: /student/getAllCurrentStudents"""
        return [
            {
                'studentNo': '123456',
                'studentNames': 'Alice Wanjiru Kamau',
                'mobileNo': '+254712345001',
                'email': 'awanjiru@strathmore.edu',
                'fatherMobileNo': '+254722111001',
                'motherMobileNo': '+254733111001',
                'programName': 'Bachelor of Science in Computer Science',
                'courseShortName': 'CS',
                'intakeName': 'September 2024',
                'academicYear': '2024/2025',
                'studentYear': '1'
            },
            {
                'studentNo': '123457',
                'studentNames': 'Bob Ochieng Otieno',
                'mobileNo': '+254723456002',
                'email': 'bochieng@strathmore.edu',
                'fatherMobileNo': '+254722222002',
                'motherMobileNo': '+254733222002',
                'programName': 'Bachelor of Business Administration',
                'courseShortName': 'BBA',
                'intakeName': 'January 2024',
                'academicYear': '2024/2025',
                'studentYear': '2'
            },
            {
                'studentNo': '123458',
                'studentNames': 'Carol Akinyi Omondi',
                'mobileNo': '+254734567003',
                'email': 'cakinyi@strathmore.edu',
                'fatherMobileNo': '+254722333003',
                'motherMobileNo': '+254733333003',
                'programName': 'Bachelor of Science in Computer Science',
                'courseShortName': 'CS',
                'intakeName': 'September 2023',
                'academicYear': '2024/2025',
                'studentYear': '2'
            },
            {
                'studentNo': '123459',
                'studentNames': 'David Mwangi Njoroge',
                'mobileNo': '+254745678004',
                'email': 'dmwangi@strathmore.edu',
                'fatherMobileNo': '+254722444004',
                'motherMobileNo': '+254733444004',
                'programName': 'Bachelor of Commerce',
                'courseShortName': 'BCOM',
                'intakeName': 'May 2024',
                'academicYear': '2024/2025',
                'studentYear': '1'
            },
            {
                'studentNo': '123460',
                'studentNames': 'Eve Wambui Kariuki',
                'mobileNo': '+254756789005',
                'email': 'ewambui@strathmore.edu',
                'fatherMobileNo': '+254722555005',
                'motherMobileNo': '+254733555005',
                'programName': 'Bachelor of Science in Computer Science',
                'courseShortName': 'CS',
                'intakeName': 'September 2021',
                'academicYear': '2024/2025',
                'studentYear': '4'
            }
        ]
    
    @staticmethod
    def get_students_academic(school_id=None, program_id=None, course_id=None, 
                              academic_year=None, student_year=None, intake_id=None):
        """Mock: /student/getStudentsAcademic with filters"""
        students = MockWebService.get_all_students()
        
        # Filter by student year if provided
        if student_year and student_year != '9999':
            students = [s for s in students if s.get('studentYear') == str(student_year)]
        
        # Filter by academic year if provided
        if academic_year and academic_year != '9999':
            students = [s for s in students if s.get('academicYear') == academic_year]
        
        return students
    
    @staticmethod
    def get_all_staff():
        """Mock: /staff/getAllStaff"""
        return [
            {
                'firstName': 'Jane',
                'lastName': 'Kamau',
                'mobileNo': '+254711111001',
                'email': 'jkamau@strathmore.edu',
                'staffId': 'EMP001',
                'departmentName': 'ICT Department',
                'genderId': '2',  # Female
                'categoryId': '1',  # Academic
                'jobStatusType': 'ft'  # Full Time
            },
            {
                'firstName': 'John',
                'lastName': 'Mwangi',
                'mobileNo': '+254722222002',
                'email': 'jmwangi@strathmore.edu',
                'staffId': 'EMP002',
                'departmentName': 'ICT Department',
                'genderId': '1',  # Male
                'categoryId': '2',  # Administrative
                'jobStatusType': 'ft'
            },
            {
                'firstName': 'Grace',
                'lastName': 'Otieno',
                'mobileNo': '+254733333003',
                'email': 'gotieno@strathmore.edu',
                'staffId': 'EMP003',
                'departmentName': 'Business School',
                'genderId': '2',
                'categoryId': '1',
                'jobStatusType': 'pt'  # Part Time
            },
            {
                'firstName': 'Peter',
                'lastName': 'Omondi',
                'mobileNo': '+254744444004',
                'email': 'pomomondi@strathmore.edu',
                'staffId': 'EMP004',
                'departmentName': 'Finance',
                'genderId': '1',
                'categoryId': '2',
                'jobStatusType': 'ft'
            },
            {
                'firstName': 'Mary',
                'lastName': 'Njoroge',
                'mobileNo': '+254755555005',
                'email': 'mnjoroge@strathmore.edu',
                'staffId': 'EMP005',
                'departmentName': 'ICT Department',
                'genderId': '2',
                'categoryId': '1',
                'jobStatusType': 'in'  # Intern
            }
        ]
    
    @staticmethod
    def get_staff_by(department_id=None, gender_id=None, category_id=None, job_status_type=None):
        """Mock: /staff/getStaffBy with filters"""
        staff = MockWebService.get_all_staff()
        
        # Filter by gender
        if gender_id and gender_id != '9999':
            staff = [s for s in staff if s.get('genderId') == str(gender_id)]
        
        # Filter by category
        if category_id and category_id != '9999':
            staff = [s for s in staff if s.get('categoryId') == str(category_id)]
        
        # Filter by job status type
        if job_status_type and job_status_type != '9999':
            staff = [s for s in staff if s.get('jobStatusType') == job_status_type]
        
        return staff
    
    @staticmethod
    def get_all_schools():
        """Mock: /school/getAllSchools"""
        return [
            {'id': '1', 'name': 'School of Computing & Engineering Sciences', 'shortName': 'SCES'},
            {'id': '2', 'name': 'Strathmore Business School', 'shortName': 'SBS'},
            {'id': '3', 'name': 'School of Governance', 'shortName': 'SGov'},
        ]
    
    @staticmethod
    def get_all_departments():
        """Mock: /department/getAllDepartments"""
        return [
            {'id': '1', 'name': 'ICT Department', 'shortName': 'ICTD'},
            {'id': '2', 'name': 'Business School', 'shortName': 'SBS'},
            {'id': '3', 'name': 'Finance', 'shortName': 'FIN'},
            {'id': '4', 'name': 'Human Resources', 'shortName': 'HR'},
        ]
    
    @staticmethod
    def get_all_programs_by_school(school_id):
        """Mock: /program/getAllProgramsBySchool/{id}"""
        programs_map = {
            '1': [
                {'id': '1', 'name': 'Bachelor of Science in Computer Science', 'shortName': 'BSc CS', 'modularInd': '0'},
                {'id': '2', 'name': 'Bachelor of Science in Information Technology', 'shortName': 'BSc IT', 'modularInd': '0'},
            ],
            '2': [
                {'id': '3', 'name': 'Bachelor of Business Administration', 'shortName': 'BBA', 'modularInd': '0'},
                {'id': '4', 'name': 'Bachelor of Commerce', 'shortName': 'BCOM', 'modularInd': '0'},
            ]
        }
        return programs_map.get(str(school_id), [])
    
    @staticmethod
    def get_all_courses_by_program(program_id):
        """Mock: /course/getAllCoursesByProgram/{id}"""
        courses_map = {
            '1': [
                {'id': '1', 'name': 'Computer Science General', 'shortName': 'CS'},
            ],
            '3': [
                {'id': '2', 'name': 'Business Administration General', 'shortName': 'BBA'},
            ]
        }
        return courses_map.get(str(program_id), [])
    
    @staticmethod
    def get_all_academic_years():
        """Mock: /academicYear/getAllAcademicYears"""
        return [
            {'id': '1', 'name': '2024/2025'},
            {'id': '2', 'name': '2023/2024'},
            {'id': '3', 'name': '2022/2023'},
        ]
    
    @staticmethod
    def get_all_intakes():
        """Mock: /intake/getAllIntakes"""
        return [
            {'id': '1', 'name': 'September 2024', 'year': '2024'},
            {'id': '2', 'name': 'January 2024', 'year': '2024'},
            {'id': '3', 'name': 'May 2024', 'year': '2024'},
            {'id': '4', 'name': 'September 2023', 'year': '2023'},
        ]


class WebServiceAdapter(models.AbstractModel):
    """
    Adapter that provides web service data to the system.
    Uses mock data by default, can be swapped with real API later.
    """
    
    _name = 'sms.webservice.adapter'
    _description = 'Web Service Adapter'
    
    def _get_students(self, **filters):
        """Get students with optional filters"""
        _logger.info(f"Fetching students with filters: {filters}")
        return MockWebService.get_students_academic(**filters)
    
    def _get_all_students(self):
        """Get all current students"""
        _logger.info("Fetching all current students")
        return MockWebService.get_all_students()
    
    def _get_staff(self, **filters):
        """Get staff with optional filters"""
        _logger.info(f"Fetching staff with filters: {filters}")
        return MockWebService.get_staff_by(**filters)
    
    def _get_all_staff(self):
        """Get all staff"""
        _logger.info("Fetching all staff")
        return MockWebService.get_all_staff()
    
    def _get_schools(self):
        """Get all schools"""
        return MockWebService.get_all_schools()
    
    def _get_departments(self):
        """Get all departments"""
        return MockWebService.get_all_departments()
    
    def _get_programs_by_school(self, school_id):
        """Get programs for a school"""
        return MockWebService.get_all_programs_by_school(school_id)
    
    def _get_courses_by_program(self, program_id):
        """Get courses for a program"""
        return MockWebService.get_all_courses_by_program(program_id)
    
    def _get_academic_years(self):
        """Get all academic years"""
        return MockWebService.get_all_academic_years()
    
    def _get_intakes(self):
        """Get all intakes"""
        return MockWebService.get_all_intakes()