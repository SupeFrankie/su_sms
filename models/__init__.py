"""
Models Package - Import Order Matters!
"""

# Base models first (no dependencies)
from . import sms_type
from . import sms_blacklist
from . import sms_gateway_config
from . import sms_dashboard  # NEW: Added Dashboard Model

# Models with basic dependencies
from . import hr_department
from . import res_partner
from . import res_users

# Contact and related models
from . import sms_contact

# Templates - MAKE SURE THIS IS HERE
from . import sms_template

# Mailing lists (depends on contacts)
from . import sms_mailing_list

# Campaigns and recipients
from . import sms_campaign
from . import sms_recipient

# Department and administrator models
from . import sms_department
from . import sms_administrator

# Message models
from . import sms_message
from . import sms_detail

# Filter wizards
from . import sms_staff_filter
from . import sms_student_filter

# Expenditure reporting - LOAD LAST
from . import sms_department_expenditure

# Incoming SMS
from . import sms_incoming

# Web service
from . import mock_webservice