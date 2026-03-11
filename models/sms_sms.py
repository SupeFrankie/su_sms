# models/sms_sms.py

"""
models/sms_sms.py
==================

Extends ``sms.sms`` to dispatch outgoing SMS records through Africa's Talking
instead of Odoo's default IAP gateway.

Key changes in v1.3
-------------------
* **Cron-based queue** — ``_send()`` no longer blocks Odoo workers.  When the
  AT provider is active it marks records ``state='queued'`` and returns
  immediately.  The cron job ``_process_africastalking_queue()`` (runs every
  minute) picks up queued records and dispatches them via AT without any
  ``time.sleep()`` call in web-worker context.
* **at_cost as Float** — cost is now stored as a parsed float (e.g. 0.8) instead
  of the raw AT string ``"KES 0.8000"``.
* **Single delivery_status field** — ``at_status`` removed; both send-time and
  webhook-confirmed statuses write to ``delivery_status``.
* **Provider param renamed** — ``sms_africastalking.provider`` (was ``sms.provider``).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.africastalking_client import (
    AT_BATCH_LIMIT,
    ATError,
    ATRecipientResult,
    AfricasTalkingClient,
)
from ..services.phone_normalizer import PhoneNormalizeError, normalize_e164

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    """Extend sms.sms with Africa's Talking dispatch, cost tracking and retry."""

    _inherit = "sms.sms"

    # ------------------------------------------------------------------
    #  Extend state selection with 'queued'
    # ------------------------------------------------------------------

    state = fields.Selection(
        selection_add=[("queued", "Queued for AT")],
        ondelete={"queued": "set default"},
    )

    # ------------------------------------------------------------------
    #  Additional fields
    # ------------------------------------------------------------------

    at_message_id = fields.Char(
        string="AT Message ID",
        readonly=True,
        copy=False,
        index=True,
        help=(
            "Message ID returned by Africa's Talking at send time.  "
            "Used to correlate incoming delivery-report callbacks."
        ),
    )
    at_failure_reason = fields.Char(
        string="AT Failure Reason",
        readonly=True,
        copy=False,
        help=(
            "Human-readable failure description from Africa's Talking.  "
            "Set when AT rejects a number or reports a delivery failure."
        ),
    )
    at_cost = fields.Float(
        string="AT Cost",
        readonly=True,
        copy=False,
        digits=(10, 4),
        help=(
            "Per-message cost in the account currency as returned by Africa's "
            "Talking.  Parsed from the AT cost string, e.g. 'KES 0.8000' --> 0.8."
        ),
    )
    delivery_status = fields.Char(
        string="Delivery Status",
        readonly=True,
        copy=False,
        help=(
            "Status from Africa's Talking — set at send time and updated when "
            "a delivery-report webhook callback arrives "
            "(e.g. 'Success', 'Delivered', 'Failed')."
        ),
    )

    # ------------------------------------------------------------------
    #  Core override: _send()
    # ------------------------------------------------------------------

    def _send(
        self,
        unlink_failed: bool = False,
        unlink_sent: bool = False,
        raise_exception: bool = False,
    ) -> None:
        """
        Queue outgoing SMS records for Africa's Talking dispatch.

        When the AT provider is active this method marks records
        ``state='queued'`` and returns immediately — no HTTP calls, no
        ``time.sleep()``, no worker blocking.  The cron job
        ``_process_africastalking_queue()`` handles actual dispatch.

        Falls back to ``super()._send()`` when:
        * ``sms_africastalking.provider`` is set to ``"odoo_iap"``, or
        * AT credentials (username / api_key) are not yet configured.

        Parameters
        ----------
        unlink_failed:
            Passed through to ``super()`` when falling back to IAP.
        unlink_sent:
            Passed through to ``super()`` when falling back to IAP.
        raise_exception:
            Passed through to ``super()`` when falling back to IAP.
        """
        creds = self.env["res.config.settings"]._get_at_credentials()

        # ---- Provider toggle -------------------------------------------
        provider = creds.get("provider", "africastalking")
        if provider != "africastalking":
            _logger.info(
                "sms_africastalking: provider=%r — delegating to Odoo IAP.", provider
            )
            return super()._send(
                unlink_failed=unlink_failed,
                unlink_sent=unlink_sent,
                raise_exception=raise_exception,
            )

        # ---- Credential check: fall back to IAP when not configured ----
        if not creds["username"] or not creds["api_key"]:
            _logger.info(
                "sms_africastalking: credentials not configured — "
                "falling back to Odoo IAP gateway."
            )
            return super()._send(
                unlink_failed=unlink_failed,
                unlink_sent=unlink_sent,
                raise_exception=raise_exception,
            )

        # ---- Mark outgoing/error records as queued ---------------------
        pending = self.filtered(lambda s: s.state in ("outgoing", "error"))
        if not pending:
            return

        pending.write({"state": "queued", "at_failure_reason": False})

        _logger.info(
            "sms_africastalking: %d record(s) marked 'queued' "
            "— cron will dispatch them via Africa's Talking.",
            len(pending),
        )
        # The cron _process_africastalking_queue() will handle actual dispatch.

    # ------------------------------------------------------------------
    #  Cron worker: _process_africastalking_queue()
    # ------------------------------------------------------------------

    @api.model
    def _process_africastalking_queue(self) -> None:
        """
        Cron-called method: fetch queued records and dispatch via AT.

        Designed to be called by the ``ir.cron`` entry in
        ``data/sms_cron.xml`` (every minute).  Processes up to
        :data:`~services.AT_BATCH_LIMIT` records per run so each cron
        execution completes quickly.  The natural 60-second cadence of
        the cron provides rate limiting without any ``time.sleep()``.

        Workflow
        --------
        1. Read credentials; skip silently if not configured.
        2. Fetch at most ``AT_BATCH_LIMIT`` records with ``state='queued'``.
        3. Build an :class:`~services.AfricasTalkingClient` and call
           ``_at_dispatch_all()``.
        4. Any record still ``queued`` after dispatch (unexpected) is
           marked ``error`` to avoid getting stuck.
        """
        creds = self.env["res.config.settings"]._get_at_credentials()

        if creds.get("provider", "africastalking") != "africastalking":
            return

        if not creds["username"] or not creds["api_key"]:
            _logger.warning(
                "sms_africastalking cron: credentials not configured — skipped."
            )
            return

        queued = self.search([("state", "=", "queued")], limit=AT_BATCH_LIMIT)
        if not queued:
            _logger.debug("sms_africastalking cron: no queued records.")
            return

        _logger.info(
            "sms_africastalking cron: processing %d queued record(s) "
            "(sandbox=%s, sender_id=%r).",
            len(queued),
            creds["sandbox"],
            creds.get("sender_id") or "(shared short-code)",
        )

        client = AfricasTalkingClient(
            username=creds["username"],
            api_key=creds["api_key"],
            sender_id=creds.get("sender_id", ""),
            sandbox=creds["sandbox"],
            timeout=creds.get("request_timeout", 30),
        )

        try:
            self._at_dispatch_all(queued, client)
        except Exception:
            _logger.exception("sms_africastalking cron: unexpected error during dispatch.")

        # Safety net: any record still 'queued' after dispatch failed to update
        still_queued = queued.filtered(lambda s: s.state == "queued")
        if still_queued:
            _logger.error(
                "sms_africastalking cron: %d record(s) still 'queued' after dispatch — "
                "marking as error.",
                len(still_queued),
            )
            still_queued.write(
                {
                    "state": "error",
                    "failure_type": "sms_server",
                    "at_failure_reason": "Cron dispatch completed without updating this record.",
                }
            )

    # ------------------------------------------------------------------
    #  Dispatch orchestration (called by cron)
    # ------------------------------------------------------------------

    def _at_dispatch_all(
        self,
        records: "SmsSms",
        client: AfricasTalkingClient,
    ) -> None:
        """
        Orchestrate full dispatch of *records* through *client*.

        Steps
        -----
        1. Normalise phone numbers; mark invalid records as error immediately.
        2. Group valid records by message body (AT requires one body per
           API call to return per-recipient ``messageId`` values).
        3. Chunk each body group by :data:`~services.AT_BATCH_LIMIT` and
           call the AT API.

        No ``time.sleep()`` is used here.  Rate limiting is achieved by the
        cron cadence (one run per minute processes at most ``AT_BATCH_LIMIT``
        records).
        """
        # ---- Step 1: phone normalisation --------------------------------
        # ORM proxy objects do not support arbitrary attribute assignment, so
        # we track normalised numbers in a plain dict keyed by record ID.
        normalised_map: dict[int, str] = {}
        valid_records: list[Any] = []

        for sms in records:
            try:
                normalised = normalize_e164(sms.number or "")
            except PhoneNormalizeError as exc:
                _logger.warning(
                    "sms_africastalking: invalid number %r for record %d — %s",
                    sms.number,
                    sms.id,
                    exc,
                )
                sms.write(
                    {
                        "state": "error",
                        "failure_type": "sms_number_format",
                        "at_failure_reason": str(exc)[:255],
                    }
                )
                continue

            normalised_map[sms.id] = normalised
            valid_records.append(sms)

        if not valid_records:
            _logger.info("sms_africastalking: no valid numbers to dispatch.")
            return

        # ---- Step 2: group by body --------------------------------------
        by_body: dict[str, list[Any]] = defaultdict(list)
        for sms in valid_records:
            by_body[sms.body].append(sms)

        # ---- Step 3: chunk and send -------------------------------------
        for body, sms_list in by_body.items():
            for i in range(0, len(sms_list), AT_BATCH_LIMIT):
                chunk = sms_list[i : i + AT_BATCH_LIMIT]
                self._at_send_chunk(chunk, body, client, normalised_map)

    def _at_send_chunk(
        self,
        chunk: list[Any],
        body: str,
        client: AfricasTalkingClient,
        normalised_map: dict,
    ) -> None:
        """
        Send one chunk (<=AT_BATCH_LIMIT) of records sharing *body*.

        Builds a number --> [records] mapping (handles duplicate numbers
        correctly), calls the AT API, and writes results back to ORM records.
        Any number not mentioned in the AT response is marked as an error.

        Logging
        -------
        Each successful send logs::

            SMS sent via Africa's Talking
              Number    : +254712345678
              Status    : Success
              Cost      : 0.8000
              MessageId : ATXid_...

        Parameters
        ----------
        chunk:
            List of ``sms.sms`` browse records, all sharing the same body.
        body:
            Common SMS body text for this chunk.
        client:
            Configured :class:`~services.AfricasTalkingClient` instance.
        normalised_map:
            Dict mapping record id --> E.164 number string.
        """
        # Map normalised number --> list of records (handles duplicates correctly)
        num_to_records: dict[str, list[Any]] = defaultdict(list)
        for sms in chunk:
            num_to_records[normalised_map[sms.id]].append(sms)

        numbers = list(num_to_records.keys())

        _logger.info(
            "sms_africastalking: sending chunk — %d number(s), body %d char(s).",
            len(numbers),
            len(body),
        )

        try:
            results: list[ATRecipientResult] = client.send(
                to=numbers,
                message=body,
            )
        except ATError as exc:
            _logger.error(
                "sms_africastalking: AT API error for %d number(s): %s",
                len(numbers),
                exc,
            )
            failure_reason = str(exc)[:255]
            for sms_list in num_to_records.values():
                for sms in sms_list:
                    sms.write(
                        {
                            "state": "error",
                            "failure_type": "sms_server",
                            "at_failure_reason": failure_reason,
                        }
                    )
            return

        # ------------------------------------------------------------------
        #  Map per-recipient results back to ORM records
        # ------------------------------------------------------------------
        responded: set[str] = set()

        for result in results:
            number = result.number
            responded.add(number)
            target_records = num_to_records.get(number)

            if target_records is None:
                _logger.warning(
                    "sms_africastalking: AT result for unknown number %r — ignored.",
                    number,
                )
                continue

            cost_float = _parse_cost_float(result.cost)

            if result.succeeded or result.buffered:
                vals: dict[str, Any] = {
                    "state": "sent",
                    "delivery_status": result.status,
                    "at_cost": cost_float,
                    "at_failure_reason": False,
                }
                _logger.info(
                    "SMS sent via Africa's Talking\n"
                    "  Number    : %s\n"
                    "  Status    : %s\n"
                    "  Cost      : %.4f\n"
                    "  MessageId : %s",
                    number,
                    result.status,
                    cost_float,
                    result.message_id or "N/A",
                )
            else:
                vals = {
                    "state": "error",
                    "failure_type": "sms_server",
                    "delivery_status": result.status,
                    "at_failure_reason": _at_failure_description(result),
                }
                _logger.warning(
                    "sms_africastalking: FAILED  number=%s  status=%s  code=%d",
                    number,
                    result.status,
                    result.status_code,
                )

            if result.message_id:
                vals["at_message_id"] = result.message_id

            for sms in target_records:
                sms.write(vals)

        # ------------------------------------------------------------------
        #  Mark numbers absent from AT response as server errors
        # ------------------------------------------------------------------
        for number, sms_list in num_to_records.items():
            if number not in responded:
                _logger.warning(
                    "sms_africastalking: number %r absent from AT response — "
                    "marking as sms_server error.",
                    number,
                )
                for sms in sms_list:
                    sms.write(
                        {
                            "state": "error",
                            "failure_type": "sms_server",
                            "at_failure_reason": "Number not present in AT response.",
                        }
                    )

    # ------------------------------------------------------------------
    #  Retry button
    # ------------------------------------------------------------------

    def action_retry_send(self) -> dict:
        """
        Reset failed records to ``'outgoing'`` and queue them for AT retry.

        Only records with ``state == 'error'`` are processed.
        Already-sent records in the selection are silently skipped.

        After calling ``_send()``, records will be in ``state='queued'``
        (AT provider) or ``state='sent'/'error'`` (IAP fallback).

        Logs::

            Retrying failed SMS
            Count: X

        Returns
        -------
        dict
            A ``display_notification`` client action.

        Raises
        ------
        UserError
            When the selection contains no failed records.
        """
        failed = self.filtered(lambda s: s.state == "error")
        if not failed:
            raise UserError(
                _("No failed messages found in the current selection.")
            )

        _logger.info(
            "sms_africastalking: Retrying failed SMS\n  Count: %d", len(failed)
        )

        failed.write({"state": "outgoing", "at_failure_reason": False})
        failed._send()  # AT provider: marks them 'queued'; IAP: sends immediately

        now_queued = failed.filtered(lambda s: s.state == "queued")
        now_sent = failed.filtered(lambda s: s.state == "sent")
        still_failed = failed.filtered(lambda s: s.state == "error")

        if still_failed:
            notif_type = "warning"
            message = _(
                "%(failed)d message(s) still failed. "
                "Check AT credentials and the SMS Queue for details.",
                failed=len(still_failed),
            )
        elif now_queued:
            notif_type = "success"
            message = _(
                "%(count)d message(s) queued for retry via Africa's Talking. "
                "The cron job will dispatch them within the next minute.",
                count=len(now_queued),
            )
        else:
            notif_type = "success"
            message = _(
                "%(count)d message(s) successfully re-sent.",
                count=len(now_sent),
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Retry"),
                "message": message,
                "type": notif_type,
                "sticky": bool(still_failed),
            },
        }


# ---------------------------------------------------------------------------
#  Private helpers
# ---------------------------------------------------------------------------


def _parse_cost_float(cost_str: str) -> float:
    """
    Parse an AT cost string into a plain float.

    Examples
    --------
    >>> _parse_cost_float("KES 0.8000")
    0.8
    >>> _parse_cost_float("")
    0.0
    >>> _parse_cost_float("USD 1.2500")
    1.25
    """
    if not cost_str:
        return 0.0
    parts = cost_str.strip().split(None, 1)
    if len(parts) == 2:
        try:
            return float(parts[1])
        except ValueError:
            pass
    return 0.0


def _at_failure_description(result: ATRecipientResult) -> str:
    """Build a human-readable failure string from an ATRecipientResult."""
    description = f"{result.status} (code {result.status_code})"
    return description[:255]
