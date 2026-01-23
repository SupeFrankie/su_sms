"""
Models Package - Correct Import Order (No Deleted Files)
"""

# Layer 1: Base models (no dependencies)
from . import sms_type
from . import sms_blacklist

# Layer 2: Gateway config
from . import sms_gateway_config

# Layer 3: Odoo core extensions
from . import hr_department
from . import res_users

# Layer 4: Contacts (depends on hr_department)
from . import sms_contact

# Layer 5: Partner extension (depends on sms_contact)
from . import res_partner

# Layer 6: Mailing lists (depends on sms_contact)
from . import sms_mailing_list

# Layer 7: Templates
from . import sms_template

# Layer 8: Campaigns (depends on res_users)
from . import sms_campaign

# Layer 9: Recipients (depends on sms_campaign)
from . import sms_recipient

# Layer 10: Filters (transient models)
from . import sms_staff_filter
from . import sms_student_filter

# Layer 11: Reporting view
from . import sms_department_expenditure

# Optional extras
try:
    from . import sms_credit
except ImportError:
    pass

try:
    from . import sms_incoming
except ImportError:
    pass

try:
    from . import sms_queue
except ImportError:
    pass