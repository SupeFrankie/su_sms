"""
Models Package - COMPLETE Import Order
=======================================

CRITICAL: Import order prevents circular dependencies.
Rule: Import models in dependency hierarchy (base → complex).

Current models in this package:
- Core: sms_type, sms_blacklist, sms_gateway_config, sms_credit, mock_webservice
- Queue: sms_queue
- Extensions: hr_department, res_partner, res_users
- Contacts: sms_contact, sms_template, sms_mailing_list
- Campaigns: sms_campaign, sms_recipient
- Admin: sms_department, sms_administrator
- Messages: sms_message, sms_detail
- Wizards: sms_staff_filter, sms_student_filter
- Reports: sms_department_expenditure, sms_incoming
"""

# =============================================================================
# LAYER 1: INDEPENDENT BASE MODELS (no dependencies on other SMS models)
# =============================================================================
from . import sms_type
from . import sms_blacklist
from . import sms_gateway_config
from . import sms_credit
from . import mock_webservice
from . import sms_queue

# =============================================================================
# LAYER 2: ODOO CORE EXTENSIONS (depend on hr/base modules only)
# =============================================================================
from . import hr_department
from . import res_partner
from . import res_users

# =============================================================================
# LAYER 3: SMS CONTACT MODELS (depend on Layer 1 & 2)
# =============================================================================
from . import sms_contact
from . import sms_template
from . import sms_mailing_list

# =============================================================================
# LAYER 4: DEPARTMENT & ADMIN (mutual dependency - import together)
# =============================================================================
from . import sms_department
from . import sms_administrator

# =============================================================================
# LAYER 5: CAMPAIGN MODELS (depend on contacts, departments, admin)
# =============================================================================
from . import sms_campaign
from . import sms_recipient

# =============================================================================
# LAYER 6: MESSAGE MODELS (depend on campaigns)
# =============================================================================
from . import sms_message
from . import sms_detail

# =============================================================================
# LAYER 7: FILTER WIZARDS (transient models - depend on everything above)
# =============================================================================
from . import sms_staff_filter
from . import sms_student_filter

# =============================================================================
# LAYER 8: REPORTING & VIEWS (SQL views and reports - absolute last)
# =============================================================================
from . import sms_department_expenditure
from . import sms_incoming