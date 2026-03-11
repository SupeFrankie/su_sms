{
    "name": "SU SMS - Africa's Talking Provider",
    "summary": (
        "Send SMS via Africa's Talking with delivery reports, "
        "provider toggle, cost tracking, analytics dashboard and "
        "mailing-list integration."
    ),
    "description": """
Africa's Talking SMS Provider for Odoo 19
==========================================

Replaces (or supplements) Odoo's default IAP SMS gateway with Africa's Talking.

Key features
------------
- Provider toggle — switch between Africa's Talking and Odoo IAP from
  Settings without touching code.
- Cron-based dispatch — ``_send()`` marks records ``queued`` and returns
  immediately; the cron job ``_process_africastalking_queue()`` dispatches
  them every minute without blocking Odoo web workers.
- Phone normalisation — numbers are normalised to E.164 before dispatch;
  invalid numbers are marked immediately without wasting an API call.
- Batch sending — recipients sharing the same message body are batched
  into a single AT API call; groups of > 1 000 are automatically chunked.
- Cost tracking — per-recipient cost stored as Float on ``sms.sms``
  for campaign cost analytics.
- SMS Analytics Dashboard — live metrics: total sent/failed/queued,
  delivery rate, total cost, messages today/this month.
- Balance check — "Check SMS Balance" button in Settings fetches the
  current AT account balance without leaving Odoo.
- Delivery webhook — ``POST /sms/africastalking/delivery`` with optional
  Bearer-token auth; updates ``delivery_status`` on receipt.
- SMS Templates — ``sms.at.template`` with ``{{first_name}}``,
  ``{{last_name}}``, ``{{email}}``, ``{{phone}}`` merge tokens linked to
  mailing lists.

Multi-tenant support
---------------------
Each Odoo database stores its own credentials via ``ir.config_parameter``,
so ``donations.strathmore.edu``, ``conferences.strathmore.edu``, and
``admissions.strathmore.edu`` are independently configured.

Kenya — Safaricom Promotional Filter
--------------------------------------
Without an approved Sender ID, messages to Safaricom subscribers may land
in the \*456# promotional inbox.  Register a Sender ID in your AT dashboard
(SMS --> Sender ID Management) and await Safaricom approval before going live.
    """,
    "author": "Strathmore University",
    "website": "https://www.strathmore.edu",
    "category": "Marketing/SMS Marketing",
    "version": "19.0.1.3.0",
    "license": "LGPL-3",
    "depends": [
        "sms",           # sms.sms model & send scheduler
        "base_setup",    # res.config.settings
        "mass_mailing",  # mailing.list / mailing.contact
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sms_template_data.xml",
        "data/sms_cron.xml",
        "views/res_config_settings_views.xml",
        "views/sms_sms_views.xml",
        "views/sms_at_template_views.xml",
        "views/sms_at_analytics_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
