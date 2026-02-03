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
            'base_dn': os.getenv('LDAP_BASE_DN', 'DC=strathmore,DC=local'),
            'staff_domain': os.getenv('LDAP_STAFF_DOMAIN', 'strathmore.local'),
            'student_domain': os.getenv('LDAP_STUDENT_DOMAIN', 'students.strathmore.edu'),
        }
    
    @api.model
    def ldap_authenticate_user(self, username, password):
        """
        Authenticate a user against LDAP (Active Directory).
        Returns: (success_boolean, result_dictionary)
        """
        # 1. Check if library is installed
        if not LDAP_AVAILABLE:
            return False, {'error': 'ldap3 library not installed on server'}
        
        # 2. Load Config
        config = self._get_ldap_config()
        
        # 3. Determine Domain (Student vs Staff)
        # Logic: If username is all numbers (e.g. 123456), it's a student.
        if str(username).isdigit():
            domain = config['student_domain']
        else:
            domain = config['staff_domain']
            
        # 4. Construct the User DN (user@domain.com)
        user_principal = f"{username}@{domain}"
        
        try:
            # 5. Connect to Server
            server = Server(config['host'], port=config['port'], get_info=ALL)
            
            # 6. Try to Bind (Login)
            conn = Connection(
                server, 
                user=user_principal, 
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )
            
            # If we get here, login worked!
            conn.unbind()
            return True, {
                'username': username,
                'domain': domain,
                'message': 'Authentication successful'
            }
            
        except Exception as e:
            # Login failed or server error
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
            
            return {
                'success': True, 
                'config': config,
                'server_info': info
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ========================================
    # UI Actions (New Methods)
    # ========================================

    def action_test_ldap_ui(self):
        """Wrapper to test LDAP and show result in UI"""
        results = self.test_ldap_connection()

        if results['success']:
            config = results['config']
            message = f"""
✓ LDAP CONNECTION SUCCESSFUL

Host: {config['host']}:{config['port']}
Base DN: {config['base_dn']}

Staff Domain: {config['staff_domain']}
Student Domain: {config['student_domain']}

Server Info:
{results.get('server_info', 'N/A')}
"""
            raise UserError(message)
        else:
            raise UserError(f"✗ LDAP CONNECTION FAILED\n\n{results['message']}")

    def action_test_dataservice_ui(self):
        """Wrapper to test Dataservices and show result in UI"""
        results = self.test_all_connections()

        ldap_status = results['ldap']['success']
        student_status = results['student_service']['status']
        staff_status = results['staff_service']['status']

        message = f"""
=== SYSTEM CONNECTIVITY TEST ===

Timestamp: {results['timestamp']}

LDAP (Active Directory):
  Status: {'ONLINE' if ldap_status else 'OFFLINE'}
  Message: {results['ldap']['message']}

STUDENT DATASERVICE:
  Status: {student_status.upper()}
  Message: {results['student_service']['message']}

STAFF DATASERVICE:
  Status: {staff_status.upper()}
  Message: {results['staff_service']['message']}

================================
"""
        all_online = ldap_status and student_status == 'online' and staff_status == 'online'

        if all_online:
            raise UserError(f"✓ ALL SERVICES ONLINE\n\n{message}")
        else:
            raise UserError(f"⚠ SOME SERVICES OFFLINE\n\n{message}")

    # ========================================
    # Dataservice Connections
    # ========================================

    @api.model
    def test_student_dataservice(self):
        """Ping student dataservice"""
        url = os.getenv('STUDENT_SERVICE_URL', 'http://dataservices.strathmore.edu/api/students')
        try:
            # Short timeout for testing
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return {'status': 'online', 'message': 'Service reachable'}
            return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'offline', 'message': str(e)}

    @api.model
    def test_staff_dataservice(self):
        """Ping staff dataservice"""
        url = os.getenv('STAFF_SERVICE_URL', 'http://dataservices.strathmore.edu/api/staff')
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return {'status': 'online', 'message': 'Service reachable'}
            return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'offline', 'message': str(e)}

    @api.model
    def test_all_connections(self):
        """Run all connectivity tests"""
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ldap': self.test_ldap_connection(),
            'student_service': self.test_student_dataservice(),
            'staff_service': self.test_staff_dataservice(),
        }