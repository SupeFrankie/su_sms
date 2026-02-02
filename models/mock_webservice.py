# models/mock_webservice.py
"""
Strathmore University Data Adapter
===================================

Connects to:
1. LDAP (Active Directory) for authentication and user lookup
2. Strathmore Juba dataservices for extended student/staff data
Falls back to mock data if services unavailable.
"""

from odoo import models, api
import logging
import requests
import os
import json
from datetime import datetime

_logger = logging.getLogger(__name__)

# LDAP imports with error handling
try:
    from ldap3 import Server, Connection, ALL, SIMPLE
    LDAP_AVAILABLE = True
except ImportError:
    _logger.warning('ldap3 not installed. LDAP features disabled. Install: pip3 install ldap3 --break-system-packages')
    LDAP_AVAILABLE = False


class WebServiceAdapter(models.AbstractModel):
    """
    Unified adapter for LDAP + Dataservices
    """
    
    _name = 'sms.webservice.adapter'
    _description = 'Strathmore LDAP & Dataservice Adapter'
    
    # ========================================
    # LDAP Configuration
    # ========================================
    
    @api.model
    def _get_ldap_config(self):
        """Load LDAP configuration from environment"""
        return {
            'host': os.getenv('LDAP_HOST', '192.168.170.20'),
            'port': int(os.getenv('LDAP_PORT', '3268')),
            'username': os.getenv('LDAP_USERNAME', 'ldapt@strathmore.local'),
            'password': os.getenv('LDAP_PASSWORD', ''),
            'base_dn': os.getenv('LDAP_BASE_DN', 'dc=strathmore,dc=local'),
            'timeout': int(os.getenv('LDAP_TIMEOUT', '5')),
            'use_ssl': os.getenv('LDAP_SSL', 'false').lower() == 'true',
            'use_tls': os.getenv('LDAP_TLS', 'false').lower() == 'true',
            'staff_domain': os.getenv('STRATHMORE_DOMAIN', 'strathmore.local'),
            'student_domain': os.getenv('STUDENTS_DOMAIN', 'std.strathmore.local'),
            'staff_tree': os.getenv('LDAP_STAFF_TREE', 'OU=Strathmore University,DC=strathmore,DC=local'),
            'student_tree': os.getenv('LDAP_STUDENT_TREE', 'ou=strathmore university students,dc=std,dc=strathmore,dc=local'),
        }
    
    @api.model
    def _is_student(self, username):
        """
        Check if username is numeric (student) or alphanumeric (staff)
        
        POLICY: This check can be overridden via system parameter 'sms.student_username_pattern'
        Default: numeric usernames = students, alphanumeric = staff
        """
        # Allow override via system parameter
        pattern = self.env['ir.config_parameter'].sudo().get_param('sms.student_username_pattern', 'numeric')
        
        if pattern == 'numeric':
            return username.isnumeric()
        else:
            # Future: could support regex patterns
            return username.isnumeric()
    
    @api.model
    def _get_domain_for(self, username):
        """Get LDAP domain based on username type"""
        config = self._get_ldap_config()
        return config['student_domain'] if self._is_student(username) else config['staff_domain']
    
    @api.model
    def _get_tree_for(self, username):
        """Get LDAP search tree based on username type"""
        config = self._get_ldap_config()
        return config['student_tree'] if self._is_student(username) else config['staff_tree']
    
    # ========================================
    # LDAP Connection Methods
    # ========================================
    
    @api.model
    def _ldap_bind(self, username=None, password=None):
        """
        Bind to LDAP server
        If username/password provided: binds as that user
        Otherwise: binds with service account
        """
        if not LDAP_AVAILABLE:
            raise Exception('LDAP library not available')
        
        config = self._get_ldap_config()
        
        # Use service account if no credentials provided
        if username is None:
            bind_user = config['username']
            bind_pass = config['password']
        else:
            domain = self._get_domain_for(username)
            bind_user = f"{username}@{domain}"
            bind_pass = password
        
        try:
            server = Server(
                config['host'],
                port=config['port'],
                get_info=ALL,
                use_ssl=config['use_ssl']
            )
            
            conn = Connection(
                server,
                user=bind_user,
                password=bind_pass,
                authentication=SIMPLE,
                auto_bind=True
            )
            
            if conn.bound:
                return conn
            
            raise Exception('LDAP bind failed - connection not bound')
            
        except Exception as e:
            _logger.error(f'LDAP bind error for {bind_user}: {str(e)}')
            raise
    
    @api.model
    def ldap_authenticate_user(self, username, password):
        """
        Authenticate user against LDAP.
        IMPORTANT:
        - This helper is intended ONLY for staff authentication into the SMS service.
        - Student identities (numeric usernames) are intentionally rejected here.
        - Any future login/session integration must call this method (or equivalent logic)
          and must NOT bypass the student check enforced here.
        Returns: (success: bool, user_data: dict)
        """
        if not LDAP_AVAILABLE:
            _logger.warning('LDAP not available - cannot authenticate')
            return False, None
        
        try:
            # Try to bind as the user
            conn = self._ldap_bind(username=username, password=password)
            conn.unbind()
            
            # Get user data using service account
            user_data = self.ldap_get_user_data(username)
            # Enforce policy: student identities (numeric usernames) must never authenticate
            # Note: student details are still accessible via read-only helpers elsewhere (e.g. _get_students)
            if user_data and user_data.get('is_student'):
                _logger.warning(f'LDAP authentication denied for student account: {username}')
                return False, None
            
            return True, user_data
            
        except Exception as e:
            _logger.error(f'LDAP authentication failed for {username}: {str(e)}')
            return False, None
    
    @api.model
    def ldap_get_user_data(self, username):
        """
        Fetch user details from LDAP using service account
        Returns: dict with username, first_name, last_name, email
        """
        if not LDAP_AVAILABLE:
            return None
        
        try:
            search_filter = f"(sAMAccountName={username})"
            search_tree = self._get_tree_for(username)
            
            attrs = [
                'cn',
                'displayName',
                'givenName',
                'mail',
                'name',
                'sAMAccountName',
                'sn',
            ]
            
            # Bind with service account
            conn = self._ldap_bind()
            
            # Search for user
            conn.search(search_tree, search_filter, attributes=attrs)
            
            if not conn.entries:
                _logger.warning(f'LDAP user not found: {username}')
                conn.unbind()
                return None
            
            # Parse first entry
            entry_json = conn.entries[0].entry_to_json()
            entry_dict = json.loads(entry_json)
            conn.unbind()
            
            data = entry_dict['attributes']
            
            user_data = {
                'username': data['sAMAccountName'][0].lower(),
                'first_name': data.get('givenName', [''])[0],
                'last_name': data.get('sn', [''])[0],
                'email': data.get('mail', [''])[0].lower(),
                'display_name': data.get('displayName', [''])[0],
                'is_student': self._is_student(username),
            }
            
            return user_data
            
        except Exception as e:
            _logger.error(f'Error getting LDAP user data for {username}: {str(e)}')
            return None
    
    @api.model
    def test_ldap_connection(self):
        """
        Test LDAP connection with timeout enforcement
        Returns dict with connection status
        """
        if not LDAP_AVAILABLE:
            return {
                'success': False,
                'message': 'LDAP library not installed',
                'config': None,
            }
        
        config = self._get_ldap_config()
        
        try:
            # Enforce short timeout for test
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(5)
            
            try:
                conn = self._ldap_bind()
                server_info = conn.server.info if conn.server else 'No server info'
                conn.unbind()
                
                return {
                    'success': True,
                    'message': 'LDAP connection successful',
                    'config': {
                        'host': config['host'],
                        'port': config['port'],
                        'base_dn': config['base_dn'],
                        'staff_domain': config['staff_domain'],
                        'student_domain': config['student_domain'],
                    },
                    'server_info': str(server_info),
                }
            finally:
                socket.setdefaulttimeout(original_timeout)
            
        except Exception as e:
            return {
                'success': False,
                'message': f'LDAP connection failed: {str(e)}',
                'config': config,
            }
    
    # ========================================
    # Dataservice Configuration
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
            'https://juba.strathmore.edu/dataservice/staff/getStaffByUsername/'
        )
    
    @api.model
    def _get_timeout(self):
        """Request timeout in seconds"""
        return int(os.getenv('DATASERVICE_TIMEOUT', '10'))
    
    @api.model
    def _use_mock_data(self):
        """Check if we should use mock data"""
        return os.getenv('DATASERVICE_USE_MOCK', 'false').lower() == 'true'
    
    # ========================================
    # Combined LDAP + Dataservice Methods
    # ========================================
    
    @api.model
    def get_staff_data(self, username=None, **filters):
        """
        Get staff data combining LDAP + Dataservice
        
        Process:
        1. If username provided: Get from LDAP first, then enrich with dataservice
        2. If filters provided: Get from dataservice
        3. Fallback to mock data if both fail
        """
        # Single staff lookup by username
        if username:
            # Try LDAP first
            ldap_data = self.ldap_get_user_data(username)
            
            if ldap_data:
                # Enrich with dataservice
                try:
                    url = f"{self._get_staff_base_url()}{username}"
                    response = requests.get(url, timeout=self._get_timeout(), verify=True)
                    
                    if response.status_code == 200:
                        dataservice_data = response.json()
                        # Merge LDAP + dataservice
                        return {**ldap_data, **dataservice_data}
                except Exception as e:
                    _logger.warning(f'Dataservice failed for {username}, using LDAP only')
                
                return ldap_data
        
        # Bulk staff query - use dataservice
        return self._get_staff(**filters)
    
    @api.model
    def _get_staff(self, **filters):
        """Get staff from dataservice with mock fallback"""
        if self._use_mock_data():
            return MockWebService.get_staff_by(**filters)
        
        try:
            base_url = self._get_staff_base_url()
            endpoint = 'getStaffBy' if filters else 'getAllStaff'
            url = f'{base_url.rstrip("/getStaffByUsername/")}/{endpoint}'
            
            response = requests.get(url, params=filters, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                return data
            return []
            
        except Exception as e:
            _logger.error(f'Staff dataservice error: {str(e)}. Using mock data.')
            return MockWebService.get_staff_by(**filters)
    
    @api.model
    def _get_students(self, **filters):
        """Get students from dataservice with mock fallback"""
        if self._use_mock_data():
            return MockWebService.get_students_academic(**filters)
        
        try:
            base_url = self._get_student_base_url()
            endpoint = 'getStudentsAcademic' if filters else 'getAllCurrentStudents'
            url = f'{base_url}{endpoint}'
            
            response = requests.get(url, params=filters, timeout=self._get_timeout(), verify=True)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                return data
            return []
            
        except Exception as e:
            _logger.error(f'Student dataservice error: {str(e)}. Using mock data.')
            return MockWebService.get_students_academic(**filters)
    
    # ========================================
    # Health Check
    # ========================================
    
    @api.model
    def test_all_connections(self):
        """Test both LDAP and dataservices with timeout enforcement"""
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5)
        
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'ldap': self.test_ldap_connection(),
                'student_service': {'status': 'unknown', 'message': ''},
                'staff_service': {'status': 'unknown', 'message': ''},
            }
            
            # Test Student Dataservice
            try:
                url = f"{self._get_student_base_url()}getAllSchools"
                response = requests.get(url, timeout=5, verify=True)
                
                if response.status_code == 200:
                    results['student_service']['status'] = 'online'
                    results['student_service']['message'] = f'Connected ({response.elapsed.total_seconds():.2f}s)'
                else:
                    results['student_service']['status'] = 'error'
                    results['student_service']['message'] = f'HTTP {response.status_code}'
            except Exception as e:
                results['student_service']['status'] = 'offline'
                results['student_service']['message'] = str(e)
            
            # Test Staff Dataservice
            try:
                base_url = self._get_staff_base_url().rstrip('/getStaffByUsername/')
                url = f"{base_url}/getAllDepartments"
                response = requests.get(url, timeout=5, verify=True)
                
                if response.status_code == 200:
                    results['staff_service']['status'] = 'online'
                    results['staff_service']['message'] = f'Connected ({response.elapsed.total_seconds():.2f}s)'
                else:
                    results['staff_service']['status'] = 'error'
                    results['staff_service']['message'] = f'HTTP {response.status_code}'
            except Exception as e:
                results['staff_service']['status'] = 'offline'
                results['staff_service']['message'] = str(e)
            
            return results
        finally:
            socket.setdefaulttimeout(original_timeout)


# ========================================
# Mock Data (Fallback)
# ========================================

class MockWebService:
    """Mock data provider - fallback when services unavailable"""
    
    @staticmethod
    def get_all_students():
        return [
            {
                'studentNo': '123456',
                'studentNames': 'Alice Wanjiru Kamau',
                'mobileNo': '+254712345001',
                'email': 'awanjiru@strathmore.edu',
                'programName': 'BSc Computer Science',
                'intakeName': 'September 2024',
                'academicYear': '2024/2025',
                'studentYear': '1'
            },
        ]
    
    @staticmethod
    def get_students_academic(**filters):
        students = MockWebService.get_all_students()
        student_year = filters.get('student_year')
        if student_year and student_year != '9999':
            students = [s for s in students if s.get('studentYear') == str(student_year)]
        return students
    
    @staticmethod
    def get_all_staff():
        return [
            {
                'firstName': 'Jane',
                'lastName': 'Kamau',
                'mobileNo': '+254711111001',
                'email': 'jkamau@strathmore.edu',
                'staffId': 'EMP001',
                'departmentName': 'ICT Department',
            },
        ]
    
    @staticmethod
    def get_staff_by(**filters):
        return MockWebService.get_all_staff()