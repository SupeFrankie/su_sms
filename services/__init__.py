# Copyright 2024 Strathmore University
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
services/
----------

Pure-Python helpers used by Odoo models.  No Odoo imports live here so
every module in this package is independently unit-testable.
"""
from .africastalking_client import (  # noqa: F401
    AT_BATCH_LIMIT,
    AT_BUFFERED_STATUSES,
    AT_SUCCESS_STATUSES,
    ATAuthError,
    ATError,
    ATRecipientResult,
    ATValidationError,
    AfricasTalkingClient,
    LIVE_URL,
    SANDBOX_URL,
)
from .phone_normalizer import (  # noqa: F401
    PhoneNormalizeError,
    normalize_e164,
    try_normalize_e164,
)
from .sms_encoding import (  # noqa: F401
    SmsStats,
    analyse as analyse_sms,
    is_gsm7,
)
