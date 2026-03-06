# Copyright 2024 Strathmore University
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
models/sms_sms.py
==================

Extends ``sms.sms`` to dispatch outgoing SMS records through Africa's Talking
instead of Odoo's default IAP gateway.

Changes vs the original
-----------------------

Bug fixes
~~~~~~~~~
* **Wrong recordset marked on API error** – the original marked the entire
  ``batch`` instead of only the ``sms_list`` records for the failing body group.
* **Silent no-op when credentials absent** – now falls back to ``super()._send()``
  so Odoo IAP behaviour is preserved until credentials are configured.
* **``num_index`` lost duplicate numbers** – a plain dict comprehension keeps
  only the *last* record for any duplicate number.  Fixed to map number → list
  of records and write to all of them.
* **Status mapping incomplete** – the original only treated ``"Success"`` as
  sent.  AT also returns ``"Sent"`` and ``"Buffered"`` at dispatch time; both
  now map to ``"sent"`` (we wait for the delivery webhook for final status).

New features
~~~~~~~~~~~~
* **Phone normalisation** – every number is normalised to E.164 before it is
  sent to AT.  Records with un-normalisable numbers are marked
  ``sms_number_format`` immediately, avoiding a wasted API call.
* **``at_failure_reason`` field** – stores the AT failure description in the
  database so it survives delivery-report callbacks and can be shown in the UI.
* **Retry safety** – ``action_retry_send`` reports the split between records
  that re-sent successfully and those that still failed.
* **Service layer** – HTTP logic delegated to :class:`~services.AfricasTalkingClient`.
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

# ---------------------------------------------------------------------------
#  AT status → Odoo sms.sms.state
# ---------------------------------------------------------------------------
# Used only for the initial send-time response.  Final delivery status arrives
# via the delivery-report webhook and is handled in controllers/delivery.py.

# AT status strings that mean "we accepted it; more news to follow"
_AT_ACCEPTED: frozenset[str] = frozenset({"Success", "Sent", "Buffered", "Queued"})


class SmsSms(models.Model):
    """Extend sms.sms with Africa's Talking dispatch and retry capability."""

    _inherit = "sms.sms"

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
    at_status = fields.Char(
        string="AT Delivery Status",
        readonly=True,
        copy=False,
        help="Most recent delivery status received from Africa's Talking.",
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

    # ------------------------------------------------------------------
    #  Core override: _send()
    # ------------------------------------------------------------------

    def _send(
        self,
        delete_all: bool = False,
        auto_commit: bool = False,
        raise_exception: bool = False,
    ) -> None:
        """
        Dispatch outgoing SMS records through Africa's Talking.

        Overrides the native Odoo ``_send()`` which dispatches via IAP.
        Falls back to ``super()._send()`` when AT credentials are absent so
        the module is safe to install even before credentials are configured.

        Send logic
        ----------
        1. Filter the recordset to records with ``state in ('outgoing', 'error')``.
        2. Normalise every phone number to E.164; records with invalid numbers
           are immediately marked ``failure_type = 'sms_number_format'``.
        3. Group remaining records by message body (AT requires one body per
           API call to return per-recipient ``messageId`` values).
        4. Chunk each body group to at most :data:`~services.AT_BATCH_LIMIT`
           recipients per API call.
        5. Map per-recipient API results back to ORM records.
        6. Any number not mentioned in the AT response is marked as errored.

        Parameters
        ----------
        delete_all:
            When ``True``, records successfully marked ``sent`` are deleted
            after dispatch (mirrors Odoo's scheduler behaviour).
        auto_commit:
            Accepted for signature compatibility; not used by the AT path.
        raise_exception:
            When ``True``, unhandled exceptions propagate to the caller.
        """
        creds = self.env["res.config.settings"]._get_at_credentials()

        if not creds["username"] or not creds["api_key"]:
            _logger.info(
                "sms_africastalking: credentials not configured – "
                "falling back to Odoo IAP gateway."
            )
            return super()._send(
                delete_all=delete_all,
                auto_commit=auto_commit,
                raise_exception=raise_exception,
            )

        pending = self.filtered(lambda s: s.state in ("outgoing", "error"))
        if not pending:
            return

        _logger.info(
            "sms_africastalking: dispatching %d record(s) (sandbox=%s).",
            len(pending),
            creds["sandbox"],
        )

        client = AfricasTalkingClient(
            username=creds["username"],
            api_key=creds["api_key"],
            sender_id=creds.get("sender_id", ""),
            sandbox=creds["sandbox"],
            timeout=creds.get("request_timeout", 30),
        )

        try:
            self._at_dispatch_all(pending, client)
        except Exception:
            if raise_exception:
                raise
            _logger.exception(
                "sms_africastalking: unexpected error during dispatch."
            )

        if delete_all:
            pending.filtered(lambda s: s.state == "sent").unlink()

    # ------------------------------------------------------------------
    #  Dispatch orchestration
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
        1. Normalise phone numbers; mark invalid records immediately.
        2. Group valid records by message body.
        3. Chunk each group by :data:`AT_BATCH_LIMIT` and call the AT API.
        """
        # ---- Step 1: phone normalisation --------------------------------
        valid_records: list[Any] = []
        for sms in records:
            try:
                normalised = normalize_e164(sms.number or "")
            except PhoneNormalizeError as exc:
                _logger.warning(
                    "sms_africastalking: invalid number %r for record %d – %s",
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

            # Attach the normalised number as a transient attribute so we
            # don't modify the stored number (user's original is preserved).
            sms._at_normalised_number = normalised
            valid_records.append(sms)

        if not valid_records:
            _logger.info("sms_africastalking: no valid numbers to dispatch.")
            return

        # ---- Step 2: group by body -------------------------------------
        by_body: dict[str, list[Any]] = defaultdict(list)
        for sms in valid_records:
            by_body[sms.body].append(sms)

        # ---- Step 3: chunk and send ------------------------------------
        for body, sms_list in by_body.items():
            for i in range(0, len(sms_list), AT_BATCH_LIMIT):
                chunk = sms_list[i : i + AT_BATCH_LIMIT]
                self._at_send_chunk(chunk, body, client)

    def _at_send_chunk(
        self,
        chunk: list[Any],
        body: str,
        client: AfricasTalkingClient,
    ) -> None:
        """
        Send one chunk (≤ :data:`AT_BATCH_LIMIT`) of records sharing *body*.

        Builds a number → [records] mapping (handles duplicate numbers
        correctly), calls the AT API, and writes results back to ORM records.
        Any number not mentioned in the AT response is marked as an error.

        Parameters
        ----------
        chunk:
            List of ``sms.sms`` browse records, all sharing the same body.
        body:
            Common SMS body text for this chunk.
        client:
            Configured :class:`~services.AfricasTalkingClient` instance.
        """
        # Map normalised number → list of records (handles duplicates correctly)
        num_to_records: dict[str, list[Any]] = defaultdict(list)
        for sms in chunk:
            num_to_records[sms._at_normalised_number].append(sms)

        numbers = list(num_to_records.keys())

        _logger.info(
            "sms_africastalking: sending chunk – %d number(s), body %d chars.",
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
                    "sms_africastalking: AT result for unknown number %r – ignored.",
                    number,
                )
                continue

            if result.succeeded or result.buffered:
                vals: dict[str, Any] = {
                    "state": "sent",
                    "at_status": result.status,
                    "at_failure_reason": False,  # clear any previous reason
                }
            else:
                vals = {
                    "state": "error",
                    "failure_type": "sms_server",
                    "at_status": result.status,
                    "at_failure_reason": _at_failure_description(result),
                }

            if result.message_id:
                vals["at_message_id"] = result.message_id

            _logger.info(
                "sms_africastalking: number=%s  status=%s  code=%d  "
                "messageId=%s  cost=%s → odoo_state=%s",
                number,
                result.status,
                result.status_code,
                result.message_id or "—",
                result.cost or "—",
                vals["state"],
            )

            for sms in target_records:
                sms.write(vals)

        # ------------------------------------------------------------------
        #  Mark numbers not in AT response as server errors
        # ------------------------------------------------------------------
        for number, sms_list in num_to_records.items():
            if number not in responded:
                _logger.warning(
                    "sms_africastalking: number %r absent from AT response – "
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
        Reset failed records to ``'outgoing'`` and re-dispatch via AT.

        Only records with ``state == 'error'`` are processed.  Non-error
        records in the selection are silently skipped, making the action
        safe to invoke from a multi-record list that may contain mixed states.

        Returns
        -------
        dict
            A ``display_notification`` client action with a success or
            warning message depending on the outcome.

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
            "sms_africastalking: retry requested for %d record(s).", len(failed)
        )

        failed.write({"state": "outgoing", "at_failure_reason": False})
        failed._send()

        # Re-read states after dispatch to report accurate counts
        now_sent = failed.filtered(lambda s: s.state == "sent")
        still_failed = failed.filtered(lambda s: s.state == "error")

        if still_failed:
            notif_type = "warning"
            message = _(
                "%(sent)d message(s) re-sent; %(failed)d still failed. "
                "Check AT credentials and the SMS Queue for details.",
                sent=len(now_sent),
                failed=len(still_failed),
            )
        else:
            notif_type = "success"
            message = _(
                "%(count)d message(s) successfully re-sent via Africa's Talking.",
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


def _at_failure_description(result: ATRecipientResult) -> str:
    """
    Build a human-readable failure string from an :class:`ATRecipientResult`.

    Combines the AT status string and numeric code for easy diagnosis.
    Truncated to 255 characters to fit the ``at_failure_reason`` field.
    """
    description = f"{result.status} (code {result.status_code})"
    return description[:255]
