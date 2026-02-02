{
    'name': 'Strathmore University - SMS Module',
    'version': '1.0.1',
    'category': 'Marketing/SMS',
    'summary': 'SMS Campaigns with Africa\'s Talking Integration',
    'author': 'Francis Martine Nyabuto Agata',
    'website': 'https://github.com/SupeFrankie',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts', 'web', 'hr'],
    'data': [
        # 1. SECURITY
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        
        # 2. DATA
        'data/sms_type_data.xml',
        'data/gateway_data.xml',
        'data/sms_template_data.xml',
        
        # 3. WIZARDS
        'wizard/sms_compose_wizard_views.xml',
        'wizard/sms_import_wizard_views.xml',  
        
        # 4. VIEWS
        'views/sms_gateway_views.xml',
        'views/sms_contact_views.xml',
        'views/sms_blacklist_views.xml',
        'views/sms_template_views.xml',
        'views/sms_mailing_list_views.xml',
        'views/sms_recipient_views.xml',
        'views/sms_dashboard_views.xml',
        #'views/sms_dashboard_action.xml',
        
        
        # 5. CAMPAIGNS
        'views/sms_campaign_views.xml',
        'views/sms_adhoc_views.xml',
        'views/sms_manual_views.xml',
        'views/sms_staff_views.xml',
        'views/sms_student_views.xml',
        
        # 6. INHERITED VIEWS
        'views/hr_department_views.xml',
        'views/res_users_views.xml',
        'views/sms_department_expenditure_views.xml',
        'views/sms_administrator_views.xml',
        'views/ldap_test_views.xml',
        'views/dataservice_test_views.xml',
        
        # 7. MENUS
        'views/menu_views.xml',
        
        # 8. OTHER
        'views/opt_out_templates.xml',
    ],
    
    # ASSETS DISABLED FOR NOW
    # 'assets': {
    #     'web.assets_backend': [
            
        
            # ''su_sms/static/src/css/sms_dashboard.css',
            #'su_sms/static/src/xml/sms_dashboard.xml',
            #'su_sms/static/src/js/sms_dashboard.js','        
    #         'su_sms/static/src/xml/sms_live_widget.xml',
    #         'su_sms/static/src/js/sms_live_widget.js',
    #         'su_sms/static/src/xml/sms_systray_balance.xml',
    #         'su_sms/static/src/js/sms_systray_balance.js',
    #     ],
    # },
    
    'external_dependencies': {
        'python': ['requests'],
    },
    
    'installable': True,
    'application': True,
    'auto_install': False,
}