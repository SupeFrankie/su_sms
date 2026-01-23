"""
Models Package - Import Order Matters!
======================================

CRITICAL: Models must be imported in dependency order:
1. Base models first (no dependencies on other custom models)
2. Models that extend Odoo core models
3. Models that depend on the above
4. Complex models with cross-dependencies last

"""

# ========== LEVEL 1: Base Configuration Models ==========
# These have no dependencies on other custom models
from . import sms_type
from . import sms_blacklist
from . import sms_gateway_config

# ========== LEVEL 2: Odoo Core Model Extensions ==========
# These extend existing Odoo models (hr.department, res.users, res.partner)
from . import hr_department
from . import res_users
from . import res_partner

# ========== LEVEL 3: Core SMS Models ==========
# Independent SMS-specific models
from . import sms_contact
from . import sms_template

# ========== LEVEL 4: Organizational Models ==========
# Models that depend on contacts
from . import sms_mailing_list

# ========== LEVEL 5: Campaign & Messaging ==========
# Main campaign model (depends on contacts, templates, gateways)
from . import sms_campaign

# Campaign recipients (depends on sms_campaign)
from . import sms_recipient

# ========== LEVEL 6: Administrative Models ==========
# Department and administrator models for billing
from . import sms_department
from . import sms_administrator

# ========== LEVEL 7: Message Tracking ==========
# Legacy message models (if you need them alongside campaigns)
from . import sms_message
from . import sms_detail

# ========== LEVEL 8: Wizards & Filters ==========
# Transient models for UI interactions
from . import sms_staff_filter
from . import sms_student_filter

# ========== LEVEL 9: Reporting & Views ==========
# SQL views and reporting models (loaded last)
from . import sms_department_expenditure