# models/mock_webservice.py
"""
Strathmore University Dataservice Adapter
==========================================

Connects to Juba dataservices to fetch real student and staff data.
Falls back to mock data if webservice is unavailable.
"""

from odoo import models, api
import logging
import requests
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


class WebServiceAdapter(models.AbstractModel):
    """
    Adapter that provides student/staff data from Strathmore's dataservices.
    Automatically falls back to mock data if webservice is unavailable.
    """
    
    _name = 'sms.webservice.adapter'
    _description = 'Strathmore Dataservice Adapter'
    
    # ========================================
    # Configuration
    # ========================================
    
    @api.model
    def _get_student_base_url(self):
        """Get student dataservice URL from environment"""
        return os.getenv(
            'STUDENT_DATASERVICE_URL',
            'https://juba.strathmore.edu/dataservice/students/'
        )
    
    @api.model
    def _get_staff_base_url(self):
        """Get staff dataservice URL from environment"""
        return os.getenv(
            'STAFF_DATASERVICE_URL',
            'https://juba.strathmore.edu/dataservice/staff/'
        )
    
    @api.model
    def _get_timeout(self):
        """Request timeout in seconds"""
        return int(os.getenv('DATASERVICE_TIMEOUT', '10'))
    
    @api.model
    def _use_mock_data(self):
        """
        Check if we should use mock data
        Set DATASERVICE_USE_MOCK=true in .env to force mock data
        """
        return os.getenv('DATASERVICE_USE_MOCK', 'false').lower() == 'true'
    
    # ========================================
    # Student Dataservice Methods
    # ========================================
    
    @api.model
    def _get_students(self, **filters):
        """
        Get students with optional filters
        Falls back to mock data on error
        """
        if self._use_mock_data():
            _logger.info('Using MOCK student data (DATASERVICE_USE_MOCK=true)')
            return MockWebService.get_students_academic(**filters)
        
        try:
            base_url = self._get_student_base_url()
            
            # Build URL based on filters
            if filters:
                endpoint = 'getStudentsAcademic'
            else:
                endpoint = 'getAllCurrentStudents'
            
            url = f'{base_url}{endpoint}'
            
            _logger.info(f'Fetching students from: {url}')
            
            response = requests.get(
                url,
                params=filters,
                timeout=self._get_timeout(),
                verify=True  # Verify SSL certificates
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Validate response structure
            if isinstance(data, list):
                _logger.info(f'Successfully fetched {len(data)} students from dataservice')
                return data
            else:
                _logger.warning(f'Unexpected response format: {type(data)}')
                return []
            
        except requests.exceptions.Timeout:
            _logger.error(f'Student dataservice timeout. Falling back to mock data.')
            return MockWebService.get_students_academic(**filters)
        
        except requests.exceptions.RequestException as e:
            _logger.error(f'Student dataservice error: {str(e)}. Falling back to mock data.')
            return MockWebService.get_students_academic(**filters)
        
        except Exception as e:
            _logger.error(f'Unexpected error fetching students: {str(e)}. Falling back to mock data.')
            return MockWebService.get_students_academic(**filters)
    
    @api.model
    def _get_all_students(self):
        """Get all current students"""
        return self._get_students()
    
    # ========================================
    # Staff Dataservice Methods
    # ========================================
    
    @api.model
    def _get_staff(self, **filters):
        """
        Get staff with optional filters
        Falls back to mock data on error
        """
        if self._use_mock_data():
            _logger.info('Using MOCK staff data (DATASERVICE_USE_MOCK=true)')
            return MockWebService.get_staff_by(**filters)
        
        try:
            base_url = self._get_staff_base_url()
            
            # Build URL based on filters
            if filters:
                endpoint = 'getStaffBy'
            else:
                endpoint = 'getAllStaff'
            
            url = f'{base_url}{endpoint}'
            
            _logger.info(f'Fetching staff from: {url}')
            
            response = requests.get(
                url,
                params=filters,
                timeout=self._get_timeout(),
                verify=True
            )
            
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                _logger.info(f'Successfully fetched {len(data)} staff from dataservice')
                return data
            else:
                _logger.warning(f'Unexpected staff response format: {type(data)}')
                return []
            
        except requests.exceptions.Timeout:
            _logger.error(f'Staff dataservice timeout. Falling back to mock data.')
            return MockWebService.get_staff_by(**filters)
        
        except requests.exceptions.RequestException as e:
            _logger.error(f'Staff dataservice error: {str(e)}. Falling back to mock data.')
            return MockWebService.get_staff_by(**filters)
        
        except Exception as e:
            _logger.error(f'Unexpected error fetching staff: {str(e)}. Falling back to mock data.')
            return MockWebService.get_staff_by(**filters)
    
    @api.model
    def _get_all_staff(self):
        """Get all staff"""
        return self._get_staff()
    
    @api.model
    def _get_staff_by_username(self, username):
        """
        Get specific staff member by username
        Uses: /staff/getStaffByUsername/{username}
        """
        if self._use_mock_data():
            all_staff = MockWebService.get_all_staff()
            return next((s for s in all_staff if s.get('staffId') == username), None)
        
        try:
            base_url = self._get_staff_base_url()
            url = f'{base_url}getStaffByUsername/{username}'
            
            _logger.info(f'Fetching staff by username: {url}')
            
            response = requests.get(
                url,
                timeout=self._get_timeout(),
                verify=True
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data if data else None
            
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error fetching staff by username {username}: {str(e)}')
            all_staff = MockWebService.get_all_staff()
            return next((s for s in all_staff if s.get('staffId') == username), None)
    
    # ========================================
    # Reference Data Methods
    # ========================================
    
    @api.model
    def _get_schools(self):
        """Get all schools/faculties"""
        if self._use_mock_data():
            return MockWebService.get_all_schools()
        
        try:
            base_url = self._get_student_base_url()
            url = f'{base_url}getAllSchools'
            
            response = requests.get(url, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            _logger.error(f'Error fetching schools: {str(e)}')
            return MockWebService.get_all_schools()
    
    @api.model
    def _get_departments(self):
        """Get all departments"""
        if self._use_mock_data():
            return MockWebService.get_all_departments()
        
        try:
            base_url = self._get_staff_base_url()
            url = f'{base_url}getAllDepartments'
            
            response = requests.get(url, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            _logger.error(f'Error fetching departments: {str(e)}')
            return MockWebService.get_all_departments()
    
    @api.model
    def _get_programs_by_school(self, school_id):
        """Get programs for a specific school"""
        if self._use_mock_data():
            return MockWebService.get_all_programs_by_school(school_id)
        
        try:
            base_url = self._get_student_base_url()
            url = f'{base_url}getAllProgramsBySchool/{school_id}'
            
            response = requests.get(url, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            _logger.error(f'Error fetching programs for school {school_id}: {str(e)}')
            return MockWebService.get_all_programs_by_school(school_id)
    
    @api.model
    def _get_courses_by_program(self, program_id):
        """Get courses for a specific program"""
        if self._use_mock_data():
            return MockWebService.get_all_courses_by_program(program_id)
        
        try:
            base_url = self._get_student_base_url()
            url = f'{base_url}getAllCoursesByProgram/{program_id}'
            
            response = requests.get(url, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            _logger.error(f'Error fetching courses for program {program_id}: {str(e)}')
            return MockWebService.get_all_courses_by_program(program_id)
    
    @api.model
    def _get_academic_years(self):
        """Get all academic years"""
        if self._use_mock_data():
            return MockWebService.get_all_academic_years()
        
        try:
            base_url = self._get_student_base_url()
            url = f'{base_url}getAllAcademicYears'
            
            response = requests.get(url, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            _logger.error(f'Error fetching academic years: {str(e)}')
            return MockWebService.get_all_academic_years()
    
    @api.model
    def _get_intakes(self):
        """Get all intakes"""
        if self._use_mock_data():
            return MockWebService.get_all_intakes()
        
        try:
            base_url = self._get_student_base_url()
            url = f'{base_url}getAllIntakes'
            
            response = requests.get(url, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            _logger.error(f'Error fetching intakes: {str(e)}')
            return MockWebService.get_all_intakes()
    
    # ========================================
    # Health Check
    # ========================================
    
    @api.model
    def test_dataservice_connection(self):
        """
        Test connection to both student and staff dataservices
        Returns detailed status report
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'student_service': {'status': 'unknown', 'message': ''},
            'staff_service': {'status': 'unknown', 'message': ''},
        }
        
        # Test Student Service
        try:
            url = f"{self._get_student_base_url()}getAllSchools"
            response = requests.get(url, timeout=5, verify=True)
            
            if response.status_code == 200:
                results['student_service']['status'] = 'online'
                results['student_service']['message'] = f'Connected successfully ({response.elapsed.total_seconds():.2f}s)'
            else:
                results['student_service']['status'] = 'error'
                results['student_service']['message'] = f'HTTP {response.status_code}'
        except Exception as e:
            results['student_service']['status'] = 'offline'
            results['student_service']['message'] = str(e)
        
        # Test Staff Service
        try:
            url = f"{self._get_staff_base_url()}getAllDepartments"
            response = requests.get(url, timeout=5, verify=True)
            
            if response.status_code == 200:
                results['staff_service']['status'] = 'online'
                results['staff_service']['message'] = f'Connected successfully ({response.elapsed.total_seconds():.2f}s)'
            else:
                results['staff_service']['status'] = 'error'
                results['staff_service']['message'] = f'HTTP {response.status_code}'
        except Exception as e:
            results['staff_service']['status'] = 'offline'
            results['staff_service']['message'] = str(e)
        
        return results


# ========================================
# Mock Data (Fallback)
# ========================================

class MockWebService:
    """
    Mock data provider - used as fallback when dataservices are unavailable
    """
    
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
        ]
    
    @staticmethod
    def get_students_academic(**filters):
        """Mock: /student/getStudentsAcademic with filters"""
        students = MockWebService.get_all_students()
        
        # Apply filters
        student_year = filters.get('student_year')
        if student_year and student_year != '9999':
            students = [s for s in students if s.get('studentYear') == str(student_year)]
        
        academic_year = filters.get('academic_year')
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
                'genderId': '2',
                'categoryId': '1',
                'jobStatusType': 'ft'
            },
            {
                'firstName': 'John',
                'lastName': 'Mwangi',
                'mobileNo': '+254722222002',
                'email': 'jmwangi@strathmore.edu',
                'staffId': 'EMP002',
                'departmentName': 'ICT Department',
                'genderId': '1',
                'categoryId': '2',
                'jobStatusType': 'ft'
            },
        ]
    
    @staticmethod
    def get_staff_by(**filters):
        """Mock: /staff/getStaffBy with filters"""
        staff = MockWebService.get_all_staff()
        
        # Apply filters
        gender_id = filters.get('gender_id')
        if gender_id and gender_id != '9999':
            staff = [s for s in staff if s.get('genderId') == str(gender_id)]
        
        category_id = filters.get('category_id')
        if category_id and category_id != '9999':
            staff = [s for s in staff if s.get('categoryId') == str(category_id)]
        
        return staff
    
    @staticmethod
    def get_all_schools():
        """Mock: /school/getAllSchools"""
        return [
            {'id': '1', 'name': 'School of Computing & Engineering Sciences', 'shortName': 'SCES'},
            {'id': '2', 'name': 'Strathmore Business School', 'shortName': 'SBS'},
        ]
    
    @staticmethod
    def get_all_departments():
        """Mock: /department/getAllDepartments"""
        return [
            {'id': '1', 'name': 'ICT Department', 'shortName': 'ICTD'},
            {'id': '2', 'name': 'Business School', 'shortName': 'SBS'},
        ]
    
    @staticmethod
    def get_all_programs_by_school(school_id):
        """Mock: /program/getAllProgramsBySchool/{id}"""
        programs_map = {
            '1': [
                {'id': '1', 'name': 'Bachelor of Science in Computer Science', 'shortName': 'BSc CS'},
            ],
            '2': [
                {'id': '3', 'name': 'Bachelor of Business Administration', 'shortName': 'BBA'},
            ]
        }
        return programs_map.get(str(school_id), [])
    
    @staticmethod
    def get_all_courses_by_program(program_id):
        """Mock: /course/getAllCoursesByProgram/{id}"""
        courses_map = {
            '1': [{'id': '1', 'name': 'Computer Science General', 'shortName': 'CS'}],
            '3': [{'id': '2', 'name': 'Business Administration General', 'shortName': 'BBA'}],
        }
        return courses_map.get(str(program_id), [])
    
    @staticmethod
    def get_all_academic_years():
        """Mock: /academicYear/getAllAcademicYears"""
        return [
            {'id': '1', 'name': '2024/2025'},
            {'id': '2', 'name': '2023/2024'},
        ]
    
    @staticmethod
    def get_all_intakes():
        """Mock: /intake/getAllIntakes"""
        return [
            {'id': '1', 'name': 'September 2024', 'year': '2024'},
            {'id': '2', 'name': 'January 2024', 'year': '2024'},
        ]