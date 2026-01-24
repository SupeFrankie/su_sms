"""
Models Package - Import Order Matters!
======================================

CRITICAL: Models must be imported in dependency order:
1. Base models first (no dependencies on other custom models)
2. Models that extend Odoo core models
3. Models that depend on the above
4. Complex models with cross-dependencies last

"""

# 1. Base Configuration
from . import sms_type
from . import sms_blacklist
from . import sms_gateway_config

# 2. Odoo Core Extensions
from . import hr_department
from . import res_users
from . import res_partner

# 3. Core SMS Models
from . import sms_contact
from . import sms_template

# 4. THE CORE CAMPAIGN MODEL 
from . import sms_campaign  

# 5. Campaign Dependencies
from . import sms_recipient
from . import sms_mailing_list

# 6. Logic & Processing
from . import sms_queue        
from . import sms_credit       
from . import sms_incoming     

# 7. Filters & Reports
from . import sms_staff_filter
from . import sms_student_filter
from . import sms_department_expenditure