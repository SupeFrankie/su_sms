# models/sms_at_analytics.py

"""
models/sms_at_analytics.py
============================

``sms.at.analytics`` - live SMS analytics dashboard for Africa's Talking.

Opened as a wizard (transient form view) so metrics are always freshly
computed from ``sms.sms`` records at the moment the user opens the dashboard.

Metrics
-------
* Total Sent - records with ``state = 'sent'``
* Total Failed - records with ``state = 'error'``
* Total Queued - records with ``state = 'queued'``
* Delivery Rate - sent / (sent + failed) × 100
* Total Cost - sum of ``at_cost`` float values
* Messages Sent Today
* Messages Sent This Month

v1.3 change: ``at_cost`` is now a Float field (was Char), so cost aggregation
uses a direct sum instead of string parsing.
"""

from __future__ import annotations

import logging
from datetime import date

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class SmsAtAnalytics(models.TransientModel):
    """Live SMS analytics populated on wizard open via default_get."""

    _name = "sms.at.analytics"
    _description = "Africa's Talking SMS Analytics Dashboard"

    # ------------------------------------------------------------------
    #  Fields (stored in transient table; populated by default_get)
    # ------------------------------------------------------------------

    total_sent = fields.Integer(
        string="Total SMS Sent",
        readonly=True,
        help="Total sms.sms records with state = 'sent' across all time.",
    )
    total_failed = fields.Integer(
        string="Total SMS Failed",
        readonly=True,
        help="Total sms.sms records with state = 'error' across all time.",
    )
    total_queued = fields.Integer(
        string="Currently Queued",
        readonly=True,
        help="Records waiting in state = 'queued' for the cron to dispatch.",
    )
    delivery_rate = fields.Float(
        string="Delivery Rate",
        digits=(5, 1),
        readonly=True,
        help="Percentage of messages that reached the 'sent' state: sent / (sent + failed) × 100.",
    )
    total_cost = fields.Char(
        string="Total Cost",
        readonly=True,
        help="Sum of all at_cost float values across all sms.sms records.",
    )
    sent_today = fields.Integer(
        string="Sent Today",
        readonly=True,
        help="sms.sms records with state = 'sent' and create_date on today's date.",
    )
    sent_this_month = fields.Integer(
        string="Sent This Month",
        readonly=True,
        help="sms.sms records with state = 'sent' and create_date in the current calendar month.",
    )
    last_refreshed = fields.Datetime(
        string="Last Refreshed",
        readonly=True,
        help="Timestamp at which these metrics were computed.",
    )

    # ------------------------------------------------------------------
    #  Populate on create via default_get
    # ------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list: list[str]) -> dict:
        """Compute all analytics metrics fresh from sms.sms records."""
        res = super().default_get(fields_list)

        SmsModel = self.env["sms.sms"].sudo()

        # --- State totals ---
        total_sent = SmsModel.search_count([("state", "=", "sent")])
        total_failed = SmsModel.search_count([("state", "=", "error")])
        total_queued = SmsModel.search_count([("state", "=", "queued")])
        total = total_sent + total_failed
        delivery_rate = round((total_sent / total * 100.0) if total else 0.0, 1)

        # --- Cost aggregation: at_cost is now Float — sum directly ---
        records_with_cost = SmsModel.search([("at_cost", ">", 0.0)])
        total_cost_amount = sum(sms.at_cost for sms in records_with_cost)
        total_cost_str = (
            f"KES {total_cost_amount:,.4f}"
            if records_with_cost
            else "No cost data"
        )

        # --- Today ---
        today_str = date.today().strftime("%Y-%m-%d 00:00:00")
        sent_today = SmsModel.search_count(
            [("state", "=", "sent"), ("create_date", ">=", today_str)]
        )

        # --- This month ---
        month_start = date.today().replace(day=1).strftime("%Y-%m-%d 00:00:00")
        sent_this_month = SmsModel.search_count(
            [("state", "=", "sent"), ("create_date", ">=", month_start)]
        )

        _logger.info(
            "sms_africastalking: analytics computed — sent=%d, failed=%d, queued=%d, "
            "rate=%.1f%%, cost=%s, today=%d, month=%d",
            total_sent,
            total_failed,
            total_queued,
            delivery_rate,
            total_cost_str,
            sent_today,
            sent_this_month,
        )

        res.update(
            {
                "total_sent": total_sent,
                "total_failed": total_failed,
                "total_queued": total_queued,
                "delivery_rate": delivery_rate,
                "total_cost": total_cost_str,
                "sent_today": sent_today,
                "sent_this_month": sent_this_month,
                "last_refreshed": fields.Datetime.now(),
            }
        )
        return res

    # ------------------------------------------------------------------
    #  Refresh button
    # ------------------------------------------------------------------

    def action_refresh(self) -> dict:
        """Re-open the analytics dashboard with freshly computed data."""
        self.ensure_one()
        new_record = self.create({})
        return {
            "type": "ir.actions.act_window",
            "res_model": "sms.at.analytics",
            "res_id": new_record.id,
            "view_mode": "form",
            "target": "new",
        }
