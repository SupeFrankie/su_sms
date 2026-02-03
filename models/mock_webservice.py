# models/mock_webservice.py
"""
Strathmore University Data Adapter
===================================
Connects to:
1. LDAP (Active Directory) for authentication
2. Dataservices for student/staff data
3. Falls back to Mock Data if services are down
"""

from odoo import models, api
from odoo.exceptions import UserError
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
    _logger.warning('ldap3 not installed. LDAP features disabled.')
    LDAP_AVAILABLE = False


class WebServiceAdapter(models.AbstractModel):
    """
    Unified adapter for LDAP + Dataservices
    """
    _name = 'sms.webservice.adapter'
    _description = 'Strathmore LDAP & Dataservice Adapter'
    
    # ========================================
    # 1. LDAP Configuration & Auth
    # ========================================
    
    @api.model
    def _get_ldap_config(self):
        return {
            'host': os.getenv('LDAP_HOST', '192.168.170.20'),
            'port': int(os.getenv('LDAP_PORT', '3268')),
            'username': os.getenv('LDAP_USERNAME', 'ldapt@strathmore.local'),
            'password': os.getenv('LDAP_PASSWORD', ''),
            'base_dn': os.getenv('LDAP_BASE_DN', 'DC=strathmore,DC=local'),
            'staff_domain': os.getenv('LDAP_STAFF_DOMAIN', 'strathmore.local'),
            'student_domain': os.getenv('LDAP_STUDENT_DOMAIN', 'students.strathmore.edu'),
        }
    
    @api.model
    def ldap_authenticate_user(self, username, password):
        """Authenticates user against Active Directory"""
        if not LDAP_AVAILABLE:
            return False, {'error': 'ldap3 library not installed'}
        
        config = self._get_ldap_config()
        
        # Determine domain based on username format
        if str(username).isdigit():
            domain = config['student_domain']
        else:
            domain = config['staff_domain']
            
        user_principal = f"{username}@{domain}"
        
        try:
            server = Server(config['host'], port=config['port'], get_info=ALL)
            conn = Connection(
                server, 
                user=user_principal, 
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )
            conn.unbind()
            return True, {
                'username': username,
                'domain': domain,
                'message': 'Authentication successful'
            }
        except Exception as e:
            return False, {'error': str(e)}

    @api.model
    def test_ldap_connection(self):
        """Test connection to LDAP server"""
        if not LDAP_AVAILABLE:
            return {'success': False, 'message': 'Python ldap3 library not installed'}

        config = self._get_ldap_config()
        try:
            server = Server(config['host'], port=config['port'], get_info=ALL)
            conn = Connection(
                server, 
                user=config['username'], 
                password=config['password'],
                authentication=SIMPLE,
                auto_bind=True
            )
            info = str(server.info)
            conn.unbind()
            return {'success': True, 'config': config, 'server_info': info}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ========================================
    # 2. UI Action Methods (Buttons)
    # ========================================

    def action_test_ldap_ui(self):
        """Button action to test LDAP"""
        results = self.test_ldap_connection()
        if results['success']:
            config = results['config']
            message = f"✓ LDAP CONNECTION SUCCESSFUL\n\nHost: {config['host']}\nBase DN: {config['base_dn']}"
            raise UserError(message)
        else:
            raise UserError(f"✗ LDAP CONNECTION FAILED\n\n{results['message']}")

    def action_test_dataservice_ui(self):
        """Button action to test all services"""
        results = self.test_all_connections()
        ldap_status = results['ldap']['success']
        msg = f"""=== SYSTEM STATUS ===
LDAP: {'ONLINE' if ldap_status else 'OFFLINE'}
Student API: {results['student_service']['status'].upper()}
Staff API: {results['staff_service']['status'].upper()}
"""
        raise UserError(msg)

    # ========================================
    # 3. Connection Tests
    # ========================================

    @api.model
    def test_student_dataservice(self):
        url = os.getenv('STUDENT_SERVICE_URL', 'http://dataservices.strathmore.edu/api/students')
        try:
            response = requests.get(url, timeout=5)
            return {'status': 'online', 'message': 'Service reachable'} if response.status_code == 200 else {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'offline', 'message': str(e)}

    @api.model
    def test_staff_dataservice(self):
        url = os.getenv('STAFF_SERVICE_URL', 'http://dataservices.strathmore.edu/api/staff')
        try:
            response = requests.get(url, timeout=5)
            return {'status': 'online', 'message': 'Service reachable'} if response.status_code == 200 else {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'offline', 'message': str(e)}

    @api.model
    def test_all_connections(self):
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ldap': self.test_ldap_connection(),
            'student_service': self.test_student_dataservice(),
            'staff_service': self.test_staff_dataservice(),
        }

    # ========================================
    # 4. Data Fetching 
    # ========================================

    @api.model
    def _get_students(self):
        """Fetch students: Tries API first, then falls back to Mock data"""
        url = os.getenv('STUDENT_SERVICE_URL', 'http://dataservices.strathmore.edu/api/students')
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass # Fallback to mock
            
        # Mock Data
        return [
            {'student_id': '090856', 'name': 'Francis K.', 'course': 'Bsc. Informatics', 'mobile': '+254700123456'},
            {'student_id': '100200', 'name': 'John Doe', 'course': 'DBIT', 'mobile': '+254711222333'},
            {'student_id': '100300', 'name': 'Jane Smith', 'course': 'BBIT', 'mobile': '+254722333444'},
        ]

    @api.model
    def _get_staff(self):
        """Fetch staff: Tries API first, then falls back to Mock data"""
        url = os.getenv('STAFF_SERVICE_URL', 'http://dataservices.strathmore.edu/api/staff')
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass # Fallback to mock

        # Mock Data
        return [
            {'staff_id': 'EMP001', 'name': 'Dr. Omondi', 'department': 'FIT', 'mobile': '+254733000001'},
            {'staff_id': 'EMP002', 'name': 'Admin Jane', 'department': 'HR', 'mobile': '+254733000002'},
        ]

# ========================================
# 5. Legacy Support 
# ========================================

class MockWebService:
    """
    Kept for backward compatibility.
    """
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