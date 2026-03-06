# Copyright 2024 Strathmore University
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "SU SMS – Africa's Talking Provider",
    "summary": (
        "Send SMS via Africa's Talking with delivery reports, "
        "webhook authentication, templates and mailing-list integration."
    ),
    "description": """
Africa's Talking SMS Provider for Odoo 19
==========================================

Replaces Odoo's default IAP SMS gateway with Africa's Talking.

Key features
------------
* Overrides ``sms.sms._send()`` to dispatch through Africa's Talking REST API.
* Batches up to 1 000 recipients per AT call; groups by message body so AT
  returns per-recipient ``messageId`` values used to correlate delivery reports.
* Falls back to Odoo IAP when AT credentials are not configured, so the module
  is safe to install before credentials are set.
* Phone numbers are normalised to E.164 before dispatch; invalid numbers are
  marked with ``sms_number_format`` rather than being sent.
* **Retry button** on failed SMS records; resets state and re-dispatches.
* **Delivery webhook** at ``/sms/africastalking/delivery`` with optional
  Bearer-token verification, accurate status mapping, and a stored failure
  reason field.
* **Settings page** – username, API key, sender ID, sandbox toggle and
  webhook verification token stored as ``ir.config_parameter`` entries.
* **SMS Templates** (``sms.at.template``) supporting ``{{first_name}}``,
  ``{{last_name}}``, ``{{email}}`` and ``{{phone}}`` merge tokens, linked to
  mailing lists via Many2many.  Accurate GSM-7 vs Unicode segment counting.
    """,
    "author": "Strathmore University",
    "website": "https://www.strathmore.edu",
    "category": "Marketing/SMS Marketing",
    "version": "19.0.1.1.0",
    "license": "LGPL-3",
    "depends": [
        "sms",           # sms.sms model & send scheduler
        "base_setup",    # res.config.settings
        "mass_mailing",  # mailing.list / mailing.contact
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sms_template_data.xml",
        "views/res_config_settings_views.xml",
        "views/sms_sms_views.xml",
        "views/sms_at_template_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
