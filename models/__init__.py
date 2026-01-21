"""
Models Package
==============

Contains all database models for the SMS module.

Order of import matters because of dependencies:
1. Base models first (contacts, blacklist)
2. Then models that reference them (mailing lists)
3. Finally messages and templates
"""

from . import sms_blacklist
from . import sms_type
from . import sms_gateway_config
from . import sms_contact
from . import sms_template
from . import sms_mailing_list
from . import sms_message
from . import sms_recipient
from . import sms_campaign
from . import res_partner
from . import res_users
from . import hr_department
from . import sms_staff_filter
from . import sms_student_filter
from . import sms_department_expenditure