# Copyright 2024 Strathmore University
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
models/res_config_settings.py
==============================

Extends ``res.config.settings`` with Africa's Talking configuration.

All values are persisted as ``ir.config_parameter`` (system parameters) so
they survive module upgrades and are accessible from any model or controller
without instantiating a settings record.

System-parameter keys
---------------------
``sms_africastalking.username``
    AT account username (use ``"sandbox"`` for testing).
``sms_africastalking.api_key``
    AT API key from the AT dashboard.
``sms_africastalking.sender_id``
    Registered alphanumeric sender ID or short-code (empty = shared).
``sms_africastalking.sandbox``
    Stored as the string ``"True"`` when sandbox mode is enabled.
``sms_africastalking.webhook_token``
    Optional secret used to authenticate incoming delivery callbacks.
    When non-empty the controller validates ``Authorization: Bearer <token>``.
``sms_africastalking.request_timeout``
    Per-request HTTP timeout in seconds (default 30).
"""

from odoo import api, fields, models

# ---------------------------------------------------------------------------
#  System-parameter key constants
#  Centralised so every module imports from here rather than duplicating strings
# ---------------------------------------------------------------------------

PARAM_USERNAME = "sms_africastalking.username"
PARAM_API_KEY = "sms_africastalking.api_key"
PARAM_SENDER_ID = "sms_africastalking.sender_id"
PARAM_SANDBOX = "sms_africastalking.sandbox"
PARAM_WEBHOOK_TOKEN = "sms_africastalking.webhook_token"
PARAM_REQUEST_TIMEOUT = "sms_africastalking.request_timeout"

_DEFAULT_TIMEOUT = 30


class ResConfigSettings(models.TransientModel):
    """Africa's Talking credential and webhook settings."""

    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    #  Fields
    # ------------------------------------------------------------------

    at_username = fields.Char(
        string="Africa's Talking Username",
        config_parameter=PARAM_USERNAME,
        help=(
            "Your Africa's Talking account username.  "
            "Use 'sandbox' to route messages through the AT testing environment "
            "at no cost."
        ),
    )
    at_api_key = fields.Char(
        string="API Key",
        config_parameter=PARAM_API_KEY,
        help="The API key displayed in your Africa's Talking dashboard (Settings → API Key).",
    )
    at_sender_id = fields.Char(
        string="Sender ID / Short-code",
        config_parameter=PARAM_SENDER_ID,
        help=(
            "Alphanumeric sender ID or short-code registered with Africa's Talking.  "
            "Leave blank to use the AT shared short-code."
        ),
    )
    at_sandbox = fields.Boolean(
        string="Use Sandbox",
        config_parameter=PARAM_SANDBOX,
        help=(
            "When enabled all messages are routed through the Africa's Talking sandbox "
            "– no real SMS messages are sent and no charges are incurred."
        ),
    )
    at_webhook_token = fields.Char(
        string="Webhook Verification Token",
        config_parameter=PARAM_WEBHOOK_TOKEN,
        help=(
            "Secret token for authenticating Africa's Talking delivery callbacks.  "
            "When set, the webhook controller rejects any request whose "
            "'Authorization: Bearer <token>' header does not match this value.  "
            "Leave blank to disable token verification (not recommended for production)."
        ),
    )
    at_request_timeout = fields.Integer(
        string="API Request Timeout (s)",
        config_parameter=PARAM_REQUEST_TIMEOUT,
        default=_DEFAULT_TIMEOUT,
        help=(
            f"Maximum seconds to wait for a response from Africa's Talking.  "
            f"Default: {_DEFAULT_TIMEOUT}s.  Increase if you experience timeout errors "
            "during large batch sends."
        ),
    )

    # ------------------------------------------------------------------
    #  Class-level credential helper
    # ------------------------------------------------------------------

    @api.model
    def _get_at_credentials(self) -> dict:
        """
        Return the current Africa's Talking settings as a plain dict.

        Reads directly from ``ir.config_parameter`` so no TransientModel
        record needs to exist.  Suitable for use inside ``sms.sms._send()``
        and the webhook controller.

        Returns
        -------
        dict
            Keys: ``username`` (str), ``api_key`` (str), ``sender_id`` (str),
            ``sandbox`` (bool), ``webhook_token`` (str),
            ``request_timeout`` (int).
        """
        get = self.env["ir.config_parameter"].sudo().get_param

        sandbox_raw = get(PARAM_SANDBOX, "False")
        # ir.config_parameter stores booleans as string "True"/"False".
        # Guard against None and handle "0" / "" as falsy.
        sandbox = isinstance(sandbox_raw, str) and sandbox_raw == "True"

        timeout_raw = get(PARAM_REQUEST_TIMEOUT, str(_DEFAULT_TIMEOUT))
        try:
            timeout = int(timeout_raw)
            if timeout <= 0:
                timeout = _DEFAULT_TIMEOUT
        except (TypeError, ValueError):
            timeout = _DEFAULT_TIMEOUT

        return {
            "username": get(PARAM_USERNAME, "") or "",
            "api_key": get(PARAM_API_KEY, "") or "",
            "sender_id": get(PARAM_SENDER_ID, "") or "",
            "sandbox": sandbox,
            "webhook_token": get(PARAM_WEBHOOK_TOKEN, "") or "",
            "request_timeout": timeout,
        }
