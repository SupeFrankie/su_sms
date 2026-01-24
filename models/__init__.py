"""
Models Package - Import Order Matters!
"""

# Base models first (no dependencies)
from . import sms_type
from . import sms_blacklist
from . import sms_gateway_config

# Models with basic dependencies
from . import hr_department
from . import res_partner
from . import res_users

# Contact and related models
from . import sms_contact

# Templates
from . import sms_template

# Mailing lists (depends on contacts)
from . import sms_mailing_list

# Campaigns and recipients
from . import sms_campaign
from . import sms_recipient

# Filter wizards
from . import sms_staff_filter
from . import sms_student_filter

# Expenditure reporting
from . import sms_department_expenditure

# Credit and Queue models
from . import sms_credit
from . import sms_queue

# Incoming SMS
from . import sms_incoming

# Mock webservice (for testing)
from . import mock_webservice