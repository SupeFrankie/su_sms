{
    'name': 'Strathmore University - SMS Module',
    'version': '1.0.0',
    'category': 'Marketing/SMS',
    'summary': 'SMS Campaigns with Africa\'s Talking API for Mass University Communication',
    'description': """
        Strathmore University SMS Communication & Management System
        ================================================
        
        Features:
        * Send bulk SMS to students, staff, clubs, departments and parents
        * Africa's Talking API integration
        * Import recipients from CSV/DOC/DOCX
        * Personalized messages with name, admission number, staff ID
        * Opt-in/Opt-out management
        * Blacklist functionality
        * Department-based campaigns
        
        SMS Modules:
        - Staff SMS: Send to staff by department, gender, category
        - Students SMS: Advanced filtering by school, program, course, year
        - Ad Hoc SMS: Upload CSV contacts
        - Manual SMS: Direct phone number entry
        
        User Roles:
        - System Administrator: Full access + configuration
        - Administrator: Staff and Students SMS
        - Faculty Administrator: Students SMS only
        - Department Administrator: Staff SMS for their department
        - Basic User: Ad Hoc and Manual SMS only
        
        Technical Features:
        - Africa's Talking API integration
        - Department-based billing (KFS5 ready)
        - CSV/DOCX import for bulk contacts
        - Personalized messaging
        - Opt-in/Opt-out web pages
        - Blacklist management
        - Comprehensive reporting
        - Financial tracking per department
        
        Based on Strathmore University legacy PHP system.
    """,
    'author': 'Francis Martine Nyabuto Agata',
    'website': 'https://github.com/SupeFrankie',
    'license': 'LGPL-3',
    'depends': ['base', 
                'mail', 
                'contacts', 
                'web', 
                'hr',
                'mass_mailing_sms',
                ],
    'data': [
        # Security FIRST
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        
        # Base data (dependencies for other files)
        'data/sms_type_data.xml',
        
        # --- LOAD WIZARDS EARLY (Dependencies for Views) ---
        'wizard/sms_composer_views.xml', 
        
        # --- LOAD VIEW FILES (DEFINING ACTIONS) ---
        'views/sms_gateway_views.xml',
        'views/sms_contact_views.xml',
        'views/sms_blacklist_views.xml',
        'views/sms_template_views.xml',
        'views/sms_mailing_list_views.xml',
        
        # Campaign views
        'views/sms_campaign_views.xml',
        'views/sms_recipient_views.xml',
        
        # Module-specific views
        'views/sms_adhoc_views.xml',
        'views/sms_manual_views.xml',
        'views/sms_staff_views.xml',
        'views/sms_student_views.xml',
        
        # Extended views
        'views/hr_department_views.xml',
        'views/res_users_views.xml',
        'views/sms_department_expenditure_views.xml',
        
        # --- LOAD MENUS LAST ---
        'views/menu_views.xml',
        
        # Other Wizards
        'wizard/import_recipients_wizard.xml',
        
        # Templates and other data 
        'data/sms_template_data.xml',
        'views/opt_out_templates.xml'
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}