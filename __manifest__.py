{
    'name': 'ICT Operations - SMS Module (Main Communications)',
    'version': '2.0.0',
    'category': 'Marketing/SMS',
    'summary': 'SMS Campaigns with Africa\'s Talking API for Mass University Communication at Strathmore University',
    'description': """
        Strathmore University SMS Communication & Management System
        ================================================
        Features:
        ---------
        * Send bulk SMS to students, staff, clubs, departments and parents.
        * Africa's Talking API integration.
        * Import recipients list from CSV/DOC/DOCX.
        * Personalised messages with name, admission number, staff ID
        * Opt-in/Opt-out management.
        * Blacklist functionality.
        * Department & group-based campaigns.
        
        * **SMS Modules:**
          - Staff SMS Module - Send to staff members
          - Students SMS Module - Send to students with advanced filtering
          - Ad Hoc SMS Module - Upload CSV contacts
          - Manual SMS Module - Send to individual numbers
        
        * **User Roles:**
          - System Administrator - Full access
          - Administrator - Staff and Students SMS
          - Faculty Administrator - Students SMS only
          - Staff Administrator - Staff SMS for their department
          - Basic User - Ad Hoc and Manual SMS only
        
        * **Features:**
          - Africa's Talking API integration
          - Department-based billing (Kuali integration ready)
          - CSV import for bulk contacts
          - Personalized messages
          - Opt-in/Opt-out management
          - Blacklist functionality
          - Comprehensive reporting
          - Financial tracking per department.
          
        Based on Strathmore University legacy PHP system.
    """,
    'author': 'Francis Martine Nyabuto Agata',
    'website': 'SupeFrankie@github.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts', 'web', 'hr'],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sms_type_data.xml',
        'data/sms_template_data.xml',
        
        # Views
        'views/menu_views.xml',
        
        # Wizards
        'wizard/sms_composer_views.xml',
        'wizard/import_recipients_wizard.xml',
        
        # Main Views
        'views/sms_template_views.xml',
        'views/sms_contact_views.xml',
        'views/sms_mailing_list_views.xml',
        'views/sms_club_tag_views.xml',
        'views/sms_campaign_views.xml',
        'views/sms_recipient_views.xml',
        'views/sms_blacklist_views.xml',
        'views/sms_gateway_views.xml',
        'views/sms_adhoc_views.xml',
        'views/sms_manual_views.xml',
        'views/sms_staff_views.xml',
        'views/sms_student_views.xml',
        'views/sms_department_expenditure_views.xml',
        'views/opt_out_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
