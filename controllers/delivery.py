# Copyright 2024 Strathmore University
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
controllers/delivery.py
========================

HTTP controller for Africa's Talking delivery-report callbacks.

Endpoint
--------
``POST /sms/africastalking/delivery``

Configure this URL in your AT dashboard:
  **SMS → Delivery Reports → Callback URL**

Set the callback URL to::

    https://<your-odoo-domain>/sms/africastalking/delivery

Authentication
--------------
When a **Webhook Verification Token** is configured in *Settings → General
Settings → Africa's Talking SMS*, every POST request must include the header::

    Authorization: Bearer <your-token>

Requests that fail this check receive **HTTP 401** and are logged.  AT will
retry failed callbacks, so the next attempt with a correct token will succeed.

When no token is configured all POST requests are accepted (backward-compatible
with deployments that do not use token verification).

AT payload fields
-----------------
Sent as ``application/x-www-form-urlencoded``:

``id``
    messageId previously returned by the sending API call.
``status``
    Human-readable status string (see :data:`_STATUS_MAP`).
``phoneNumber``
    Recipient's phone number.
``networkCode``
    Carrier network code (optional, not stored).
``failureReason``
    Present when ``status == "Failed"`` (optional).
``retryCount``
    Number of delivery attempts so far (optional, not stored).

AT delivery status strings
--------------------------
``Success``         – accepted at dispatch (may appear in bulk send responses)
``Sent``            – delivered to carrier
``Buffered``        – queued, waiting for device to come online
``Delivered``       – confirmed received by the handset
``Failed``          – permanent failure
``Rejected``        – rejected by carrier or AT
``UserInBlacklist`` – number is on AT's opt-out list
``NotNetworkSubscriber`` / ``InvalidLinkId`` / others – various hard failures

Improvements vs the original
-----------------------------
* **Bearer-token authentication** – unauthenticated spoofed callbacks can no
  longer alter SMS delivery states.
* **Batch write** – the original called ``sms.write()`` inside a per-record
  loop.  Now a single ``sms_records.write()`` covers all records with the same
  ``at_message_id``.
* **Failure reason stored in database** – the original attempted
  ``message_post()`` on ``sms.sms`` which has no chatter; the message was
  silently discarded.  The failure reason is now written to ``at_failure_reason``
  directly on the record.
* **Correct environment handling** – the original used
  ``request.env(user=root).sudo()`` which is redundant.  Using
  ``request.env['sms.sms'].sudo()`` directly is cleaner and avoids an extra
  ``ref()`` query.
* **Status map additions** – added ``Delivered`` which is the most important
  final-confirmation status.
"""

from __future__ import annotations

import hmac
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  AT status → Odoo sms.sms.state
# ---------------------------------------------------------------------------
# This map covers *delivery-report* statuses (webhook callbacks).
# Send-time statuses are handled separately in models/sms_sms.py.

_STATUS_MAP: dict[str, str] = {
    # --- Terminal success ---
    "Delivered": "sent",
    "Success": "sent",          # may appear in delivery reports too
    # --- Still in transit (keep as sent; we received confirmation AT has it) ---
    "Sent": "sent",             # carrier accepted
    "Buffered": "sent",         # waiting for device, not a failure
    # --- Terminal failures ---
    "Failed": "error",
    "Rejected": "error",
    "UserInBlacklist": "error",
    "NotNetworkSubscriber": "error",
    "InvalidLinkId": "error",
    "UserAccountSuspended": "error",
    "NotSubscribedToProduct": "error",
    "UserNotOnNet": "error",
    "DeliveryFailure": "error",
}

# AT statuses that represent permanent failures (store failure reason)
_FAILURE_STATUSES: frozenset[str] = frozenset(
    s for s, state in _STATUS_MAP.items() if state == "error"
)


class AfricasTalkingDeliveryController(http.Controller):
    """Handle AT delivery-report callbacks."""

    # ------------------------------------------------------------------
    #  POST – delivery report
    # ------------------------------------------------------------------

    @http.route(
        "/sms/africastalking/delivery",
        type="http",
        auth="none",       # no Odoo session – AT calls this as an external service
        methods=["POST"],
        csrf=False,        # AT does not send Odoo CSRF tokens
        save_session=False,
    )
    def delivery_report(self, **post: str) -> http.Response:
        """
        Process a single delivery-report callback from Africa's Talking.

        Returns HTTP 200 with body ``"OK"`` in all non-error cases so that AT
        does not keep retrying.  Returns HTTP 401 when token validation fails
        so that AT *will* retry (giving the admin a chance to correct the
        token mismatch).

        Parameters
        ----------
        **post:
            Form-encoded fields sent by Africa's Talking.
        """
        # ---- 1. Token authentication ----------------------------------------
        auth_error = self._verify_webhook_token()
        if auth_error:
            return auth_error

        # ---- 2. Parse payload fields ----------------------------------------
        at_message_id = (post.get("id") or "").strip()
        at_status = (post.get("status") or "").strip()
        phone_number = (post.get("phoneNumber") or "").strip()
        failure_reason = (post.get("failureReason") or "").strip()

        _logger.info(
            "AT delivery callback  id=%s  status=%s  phone=%s  failureReason=%s",
            at_message_id or "(empty)",
            at_status or "(empty)",
            phone_number or "(empty)",
            failure_reason or "—",
        )

        # ---- 3. Guard: messageId required -----------------------------------
        if not at_message_id:
            _logger.warning(
                "AT delivery callback received without 'id' field – ignored."
            )
            return self._ok()

        # ---- 4. Resolve Odoo state ------------------------------------------
        odoo_state = _STATUS_MAP.get(at_status)
        if odoo_state is None:
            _logger.warning(
                "AT delivery callback: unknown status %r for messageId=%s – "
                "state will not be updated.",
                at_status,
                at_message_id,
            )

        # ---- 5. Locate matching sms.sms records -----------------------------
        # sudo() required: auth='none' means request.env has no user context.
        sms_records = (
            request.env["sms.sms"]
            .sudo()
            .search([("at_message_id", "=", at_message_id)], limit=10)
        )

        if not sms_records:
            _logger.warning(
                "AT delivery callback: no sms.sms found for messageId=%s  "
                "phone=%s – ignored (message may have been deleted).",
                at_message_id,
                phone_number,
            )
            return self._ok()

        # ---- 6. Write state update in a single batch call -------------------
        write_vals: dict = {"at_status": at_status}

        if odoo_state:
            write_vals["state"] = odoo_state

        if at_status in _FAILURE_STATUSES:
            # Store failure reason so it is visible in the SMS Queue view
            write_vals["at_failure_reason"] = (failure_reason or at_status)[:255]
            if odoo_state == "error":
                write_vals["failure_type"] = "sms_server"
        else:
            # Clear any previous failure reason on re-delivery
            write_vals["at_failure_reason"] = False

        sms_records.write(write_vals)

        _logger.info(
            "AT delivery callback applied to %d record(s): "
            "at_status=%r → odoo_state=%r",
            len(sms_records),
            at_status,
            odoo_state,
        )

        return self._ok()

    # ------------------------------------------------------------------
    #  GET – liveness check
    # ------------------------------------------------------------------

    @http.route(
        "/sms/africastalking/delivery",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def delivery_report_probe(self, **_kwargs) -> http.Response:
        """
        Liveness probe for the webhook URL.

        Returns a plain-text confirmation so the AT dashboard "Test URL"
        button and manual browser checks give immediate feedback.
        No authentication required for the GET probe.
        """
        return request.make_response(
            "Africa's Talking delivery webhook is active.",
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------

    def _verify_webhook_token(self) -> http.Response | None:
        """
        Validate the ``Authorization: Bearer <token>`` header when a webhook
        verification token is configured.

        Returns
        -------
        None
            When verification passes (or is disabled).
        http.Response
            HTTP 401 response when the token is wrong or missing.
        """
        expected_token: str = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("sms_africastalking.webhook_token", "")
            or ""
        ).strip()

        if not expected_token:
            # No token configured – accept all requests (backward-compatible)
            return None

        auth_header: str = request.httprequest.headers.get("Authorization", "")
        scheme, _, provided_token = auth_header.partition(" ")

        # Use hmac.compare_digest to resist timing-based side-channel attacks
        token_ok = (
            scheme.lower() == "bearer"
            and bool(provided_token)
            and hmac.compare_digest(provided_token.strip(), expected_token)
        )

        if not token_ok:
            _logger.warning(
                "AT delivery callback: invalid or missing Bearer token from %s – "
                "request rejected (HTTP 401).",
                request.httprequest.remote_addr,
            )
            return request.make_response(
                "Unauthorized",
                status=401,
                headers=[("Content-Type", "text/plain; charset=utf-8")],
            )

        return None

    @staticmethod
    def _ok() -> http.Response:
        """Return a standard HTTP 200 OK plain-text response."""
        return request.make_response(
            "OK",
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )
