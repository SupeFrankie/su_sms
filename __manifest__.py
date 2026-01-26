# __manifest__.py

{
    'name': 'Strathmore University - SMS Module',
    'version': '1.0.1',
    'category': 'Marketing/SMS',
    'summary': 'SMS Campaigns with Live Counters & CSV Wizards',
    'author': 'Francis Martine Nyabuto Agata',
    'website': 'https://github.com/SupeFrankie',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts', 'web', 'hr'],
    'data': [
        # =========================================================
        # 1. SECURITY (Load First)
        # =========================================================
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        
        # =========================================================
        # 2. DATA (Base Configuration)
        # =========================================================
        'data/sms_type_data.xml',
        'data/gateway_data.xml',
        'data/sms_template_data.xml',
        
        # =========================================================
        # 3. WIZARDS (Load before Views that reference them)
        # =========================================================
        'wizard/sms_compose_wizard_views.xml',
        'wizard/sms_import_wizard_views.xml',  # New CSV Import Wizard
        
        # =========================================================
        # 4. VIEWS (Standard Views)
        # =========================================================
        'views/sms_gateway_views.xml',
        'views/sms_contact_views.xml',
        'views/sms_blacklist_views.xml',
        'views/sms_template_views.xml',
        'views/sms_mailing_list_views.xml',
        'views/sms_recipient_views.xml',
        'views/sms_dashboard_views.xml', # New Dashboard View
        
        # =========================================================
        # 5. CAMPAIGN & MODULE SPECIFIC VIEWS
        # =========================================================
        'views/sms_campaign_views.xml',
        'views/sms_adhoc_views.xml',
        'views/sms_manual_views.xml',
        'views/sms_staff_views.xml',
        'views/sms_student_views.xml',
        
        # =========================================================
        # 6. INHERITED VIEWS & MENUS (Load Last)
        # =========================================================
        'views/hr_department_views.xml',
        'views/res_users_views.xml',
        'views/sms_department_expenditure_views.xml',
        'views/sms_administrator_views.xml',
        
        'views/menu_views.xml', # Menus must be last to find all actions
    ],
    'assets': {
        'web.assets_backend': [
            # Live Character Counter
            'su_sms/static/src/xml/sms_live_widget.xml',
            'su_sms/static/src/js/sms_live_widget.js',
            
            # Header Balance Display
            'su_sms/static/src/xml/sms_systray_balance.xml',
            'su_sms/static/src/js/sms_systray_balance.js',
        ],
    },
}