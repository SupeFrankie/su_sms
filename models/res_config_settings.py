# models/res_config_settings.py

"""
models/res_config_settings.py
==============================

Extends ``res.config.settings`` with Africa's Talking configuration.

System-parameter keys
---------------------
``sms_africastalking.provider``
    Which SMS backend to use: ``"africastalking"`` (default) or ``"odoo_iap"``.
``sms_africastalking.username``
    AT account username (use ``"sandbox"`` for testing).
``sms_africastalking.api_key``
    AT API key.
``sms_africastalking.sender_id``
    Registered alphanumeric sender ID or short-code (empty = shared).
``sms_africastalking.sandbox``
    Stored as the string ``"True"`` when sandbox mode is enabled.
``sms_africastalking.webhook_token``
    Optional secret for authenticating delivery callbacks.
``sms_africastalking.request_timeout``
    Per-request HTTP timeout in seconds (default 30).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# ---------------------------------------------------------------------------
#  System-parameter key constants
# ---------------------------------------------------------------------------

PARAM_PROVIDER = "sms_africastalking.provider"
PARAM_USERNAME = "sms_africastalking.username"
PARAM_API_KEY = "sms_africastalking.api_key"
PARAM_SENDER_ID = "sms_africastalking.sender_id"
PARAM_SANDBOX = "sms_africastalking.sandbox"
PARAM_WEBHOOK_TOKEN = "sms_africastalking.webhook_token"
PARAM_REQUEST_TIMEOUT = "sms_africastalking.request_timeout"

_DEFAULT_TIMEOUT = 30


class ResConfigSettings(models.TransientModel):
    """Africa's Talking credential, provider, and webhook settings."""

    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    #  Provider selection
    # ------------------------------------------------------------------

    at_provider = fields.Selection(
        selection=[
            ("africastalking", "Africa's Talking"),
            ("odoo_iap", "Odoo IAP (built-in)"),
        ],
        string="SMS Provider",
        config_parameter=PARAM_PROVIDER,
        default="africastalking",
        help=(
            "Choose which SMS gateway Odoo uses when sending messages.\n\n"
            "Africa's Talking: routes all outgoing SMS through the Africa's Talking "
            "REST API using the credentials below.  Recommended for Kenya / East Africa.\n\n"
            "Odoo IAP: uses Odoo's built-in IAP SMS credit system (the default before "
            "this module was installed).  Credentials below are ignored."
        ),
    )

    # ------------------------------------------------------------------
    #  API Credentials
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
        help="The API key displayed in your Africa's Talking dashboard (Settings --> API Key).",
    )
    at_sender_id = fields.Char(
        string="Sender ID / Short-code",
        config_parameter=PARAM_SENDER_ID,
        help=(
            "Alphanumeric sender ID or short-code registered with Africa's Talking.  "
            "Leave blank to use the AT shared short-code.\n\n"
            "KENYA (Safaricom): without an approved Sender ID, messages may be "
            "delivered to the *456# promotional inbox instead of the main SMS inbox.  "
            "Register a Sender ID in your AT dashboard and await Safaricom approval."
        ),
    )
    at_sandbox = fields.Boolean(
        string="Use Sandbox",
        config_parameter=PARAM_SANDBOX,
        help=(
            "When enabled all messages are routed through the Africa's Talking sandbox "
            "- no real SMS messages are sent and no charges are incurred.  "
            "Disable this in production."
        ),
    )
    at_webhook_token = fields.Char(
        string="Webhook Verification Token",
        config_parameter=PARAM_WEBHOOK_TOKEN,
        help=(
            "Secret token for authenticating Africa's Talking delivery callbacks.  "
            "When set, the webhook controller rejects any request whose "
            "'Authorization: Bearer <token>' header does not match this value.  "
            "Leave blank to accept all callbacks without authentication "
            "(not recommended for production)."
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
    #  Balance check button action
    # ------------------------------------------------------------------

    def action_check_at_balance(self) -> dict:
        """
        Fetch and display the current Africa's Talking account balance.

        Reads credentials directly from ``ir.config_parameter`` so the admin
        does not need to save the settings form before clicking the button.

        Returns
        -------
        dict
            ``display_notification`` client action showing the balance.

        Raises
        ------
        UserError
            When credentials are not yet configured.
        """
        # Import here to avoid circular imports at module load time
        from ..services.africastalking_client import AfricasTalkingClient, ATError

        creds = self._get_at_credentials()

        if not creds["username"] or not creds["api_key"]:
            raise UserError(
                _(
                    "Africa's Talking credentials are not configured.  "
                    "Please enter your Username and API Key above, save the settings, "
                    "then try again."
                )
            )

        try:
            client = AfricasTalkingClient(
                username=creds["username"],
                api_key=creds["api_key"],
                sandbox=creds["sandbox"],
                timeout=creds["request_timeout"],
            )
            balance = client.get_balance()
        except ATError as exc:
            raise UserError(
                _(
                    "Could not retrieve Africa's Talking balance:\n%(error)s",
                    error=str(exc),
                )
            ) from exc

        sandbox_note = _(" (Sandbox)") if creds["sandbox"] else ""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Africa's Talking Balance%(sandbox)s", sandbox=sandbox_note),
                "message": _("Account balance: %(balance)s", balance=balance),
                "type": "info",
                "sticky": True,
            },
        }

    # ------------------------------------------------------------------
    #  Class-level credential helper (used by sms_sms._send())
    # ------------------------------------------------------------------

    @api.model
    def _get_at_credentials(self) -> dict:
        """
        Return the current Africa's Talking settings as a plain dict.

        Reads directly from ``ir.config_parameter`` so no TransientModel
        record needs to exist.

        Returns
        -------
        dict
            Keys: ``provider`` (str), ``username`` (str), ``api_key`` (str),
            ``sender_id`` (str), ``sandbox`` (bool), ``webhook_token`` (str),
            ``request_timeout`` (int).
        """
        get = self.env["ir.config_parameter"].sudo().get_param

        sandbox_raw = get(PARAM_SANDBOX, "False")
        sandbox = isinstance(sandbox_raw, str) and sandbox_raw == "True"

        timeout_raw = get(PARAM_REQUEST_TIMEOUT, str(_DEFAULT_TIMEOUT))
        try:
            timeout = int(timeout_raw)
            if timeout <= 0:
                timeout = _DEFAULT_TIMEOUT
        except (TypeError, ValueError):
            timeout = _DEFAULT_TIMEOUT

        return {
            "provider": get(PARAM_PROVIDER, "africastalking") or "africastalking",
            "username": get(PARAM_USERNAME, "") or "",
            "api_key": get(PARAM_API_KEY, "") or "",
            "sender_id": get(PARAM_SENDER_ID, "") or "",
            "sandbox": sandbox,
            "webhook_token": get(PARAM_WEBHOOK_TOKEN, "") or "",
            "request_timeout": timeout,
        }
