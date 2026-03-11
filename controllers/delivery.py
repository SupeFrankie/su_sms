# controllers/delivery.py

"""
controllers/delivery.py
========================

HTTP controller for Africa's Talking delivery-report callbacks.

Endpoint
--------
``POST /sms/africastalking/delivery``

Configure this URL in your AT dashboard:
  SMS --> Delivery Reports --> Callback URL

Set it to::

    https://<your-odoo-domain>/sms/africastalking/delivery

Authentication
--------------
When a **Webhook Verification Token** is configured in Settings, every POST
request must include::

    Authorization: Bearer <your-token>

Requests that fail this check receive **HTTP 401**.  AT will retry failed
callbacks automatically.

Fields written on callback
--------------------------
``delivery_status``
    Unified delivery status field — written both at send time (by the cron)
    and here when the webhook confirms final delivery.
``state``
    Odoo-side state: ``"sent"`` or ``"error"``.
``at_failure_reason``
    Populated on failure callbacks; cleared on successful re-delivery.
``failure_type``
    Set to ``"sms_server"`` on permanent failures.

v1.3 change: ``at_status`` field removed; ``delivery_status`` is the single
source of truth for both send-time and webhook-confirmed status.
"""

from __future__ import annotations

import hmac
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  AT delivery-report status --> Odoo state
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[str, str] = {
    # Terminal success
    "Delivered": "sent",
    "Success": "sent",
    # Still in transit — keep as sent
    "Sent": "sent",
    "Buffered": "sent",
    # Terminal failures
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

_FAILURE_STATUSES: frozenset[str] = frozenset(
    s for s, state in _STATUS_MAP.items() if state == "error"
)


class AfricasTalkingDeliveryController(http.Controller):
    """Handle AT delivery-report callbacks."""

    # ------------------------------------------------------------------
    #  POST - delivery report
    # ------------------------------------------------------------------

    @http.route(
        "/sms/africastalking/delivery",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def delivery_report(self, **post: str) -> http.Response:
        """
        Process a single delivery-report callback from Africa's Talking.

        Returns HTTP 200 in all non-error cases; HTTP 401 when token
        validation fails (so AT retries with the correct token).
        """
        # ---- 1. Token authentication ------------------------------------
        auth_error = self._verify_webhook_token()
        if auth_error:
            return auth_error

        # ---- 2. Parse payload -------------------------------------------
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

        # ---- 3. Guard: messageId required --------------------------------
        if not at_message_id:
            _logger.warning(
                "AT delivery callback received without 'id' field — ignored."
            )
            return self._ok()

        # ---- 4. Resolve Odoo state --------------------------------------
        odoo_state = _STATUS_MAP.get(at_status)
        if odoo_state is None:
            _logger.warning(
                "AT delivery callback: unknown status %r for messageId=%s — "
                "state not updated.",
                at_status,
                at_message_id,
            )

        # ---- 5. Locate matching sms.sms records -------------------------
        sms_records = (
            request.env["sms.sms"]
            .sudo()
            .search([("at_message_id", "=", at_message_id)])
        )

        if not sms_records:
            _logger.warning(
                "AT delivery callback: no sms.sms found for messageId=%s  "
                "phone=%s — ignored (may have been deleted).",
                at_message_id,
                phone_number,
            )
            return self._ok()

        # ---- 6. Batch write ----------------------------------------------
        # delivery_status is the single unified field for AT status updates.
        write_vals: dict = {"delivery_status": at_status}

        if odoo_state:
            write_vals["state"] = odoo_state

        if at_status in _FAILURE_STATUSES:
            write_vals["at_failure_reason"] = (failure_reason or at_status)[:255]
            if odoo_state == "error":
                write_vals["failure_type"] = "sms_server"
        else:
            write_vals["at_failure_reason"] = False  # clear on re-delivery

        sms_records.write(write_vals)

        _logger.info(
            "AT delivery callback applied to %d record(s): "
            "at_status=%r --> odoo_state=%r",
            len(sms_records),
            at_status,
            odoo_state,
        )

        return self._ok()

    # ------------------------------------------------------------------
    #  GET - liveness check
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
        """Liveness probe — returns 200 OK with a plain-text confirmation."""
        return request.make_response(
            "Africa's Talking delivery webhook is active.",
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------

    def _verify_webhook_token(self) -> http.Response | None:
        """
        Validate the ``Authorization: Bearer <token>`` header.

        Returns ``None`` when verification passes or is disabled;
        returns an HTTP 401 response when it fails.
        """
        expected_token: str = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("sms_africastalking.webhook_token", "")
            or ""
        ).strip()

        if not expected_token:
            return None  # verification disabled

        auth_header: str = request.httprequest.headers.get("Authorization", "")
        scheme, _, provided_token = auth_header.partition(" ")

        token_ok = (
            scheme.lower() == "bearer"
            and bool(provided_token)
            and hmac.compare_digest(provided_token.strip(), expected_token)
        )

        if not token_ok:
            _logger.warning(
                "AT delivery callback: invalid or missing Bearer token from %s — "
                "HTTP 401.",
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
