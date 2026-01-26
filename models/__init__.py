# models/__init__.py
"""
Models Package - Import Order Matters!
NO circular dependencies - each import only depends on models imported above it.
"""

# ============================================
# LEVEL 1: Base models (no dependencies)
# ============================================
from . import sms_type
from . import sms_blacklist
from . import sms_gateway_config
from . import sms_dashboard  # Stats model (no dependencies)

# ============================================
# LEVEL 2: Odoo core extensions
# ============================================
from . import hr_department  # Extends hr.department
from . import res_partner     # Extends res.partner
from . import res_users       # Extends res.users (depends on res_partner, hr_department)

# ============================================
# LEVEL 3: SMS contacts and templates
# ============================================
from . import sms_contact     # Depends on hr_department
from . import sms_template    # No dependencies

# ============================================
# LEVEL 4: Mailing lists (depends on contacts)
# ============================================
from . import sms_mailing_list  # Depends on sms_contact

# ============================================
# LEVEL 5: Campaigns and recipients
# ============================================
from . import sms_campaign    # Depends on sms_gateway_config, sms_contact
from . import sms_recipient   # Depends on sms_campaign

# ============================================
# LEVEL 6: Department and administrators
# ============================================
from . import sms_department       # Depends on hr_department
from . import sms_administrator    # Depends on res_users, sms_department

# ============================================
# LEVEL 7: Messages (depends on campaigns)
# ============================================
from . import sms_message     # Depends on sms_administrator
from . import sms_detail      # Depends on sms_message

# ============================================
# LEVEL 8: Filter wizards
# ============================================
from . import sms_staff_filter    # Depends on hr_department
from . import sms_student_filter  # Depends on hr_department

# ============================================
# LEVEL 9: Reporting views (depends on everything)
# ============================================
from . import sms_department_expenditure  # Database view - load last

# ============================================
# LEVEL 10: Other models
# ============================================
from . import sms_incoming    
from . import mock_webservice 