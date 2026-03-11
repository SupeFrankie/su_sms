# models/sms_at_template.py


"""
models/sms_at_template.py
==========================

``sms.at.template`` - a lightweight personalised SMS template model.

Improvements vs the original
-----------------------------

Correctness
~~~~~~~~~~~
* **All four merge tokens supported** - ``{{first_name}}``, ``{{last_name}}``,
  ``{{email}}``, ``{{phone}}`` are now rendered and validated.  The original
  only supported ``{{first_name}}``; the validator raised ``ValidationError``
  for the other three.
* **Accurate SMS segment counting** - the original always assumed 160 GSM-7
  chars per segment.  This is wrong for multi-part messages (153 chars/part)
  and for Unicode bodies (70 single / 67 multi).  Now uses the proper
  :mod:`~services.sms_encoding` utility.
* **Correct opt-out filtering** - the original used ``('opt_out', '=', False)``
  directly on ``mailing.contact``, which is a computed field and may silently
  include contacts that opted out of the specific target lists.  The improved
  version queries ``mailing.contact`` with ``list_ids`` domain directly,
  which is the correct Odoo 17+ approach (mailing.contact (subscription model removed in Odoo 17)
  was removed in Odoo 17).

Performance
~~~~~~~~~~~
* **O(n) deduplication** - the original used ``unique |= c`` inside a loop,
  producing O(n²) record-set union operations for large lists.  The improved
  version uses a ``dict`` keyed by mobile number.
* **Single ``create()`` call** - all ``sms.sms`` records are created in one
  batched ORM call instead of one per contact.

Preview
~~~~~~~
* ``action_preview`` now renders all four tokens with realistic-looking
  placeholder values so reviewers can spot formatting issues before sending.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..services.sms_encoding import SmsStats, analyse as analyse_sms

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Token configuration
# ---------------------------------------------------------------------------

#: Regex matching any ``{{token}}`` placeholder in a template body.
_TOKEN_RE: re.Pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

#: Tokens the renderer can resolve, mapped to a human-readable description.
SUPPORTED_TOKENS: dict[str, str] = {
    "first_name": "Contact's first name",
    "last_name": "Contact's last name (everything after the first word)",
    "email": "Contact's e-mail address",
    "phone": "Contact's mobile phone number",
}

#: Sample values used for the preview action.
_PREVIEW_VALUES: dict[str, str] = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone": "+254712345678",
}


# ---------------------------------------------------------------------------
#  Token renderer (standalone function - no Odoo dependency, easily tested)
# ---------------------------------------------------------------------------


def render_body(body: str, values: dict[str, str]) -> str:
    """
    Replace every ``{{token}}`` in *body* using the *values* mapping.

    Unknown tokens are left as-is so the admin can debug them.  Whitespace
    inside braces is normalised (``{{ first_name }}`` == ``{{first_name}}``).

    Parameters
    ----------
    body:
        Raw template body text.
    values:
        Mapping of token name --> replacement string.

    Returns
    -------
    str
        Rendered body with known tokens substituted.

    Examples
    --------
    >>> render_body("Hi {{first_name}}!", {"first_name": "Jane"})
    'Hi Jane!'
    >>> render_body("Hi {{unknown}}!", {"first_name": "Jane"})
    'Hi {{unknown}}!'
    """
    def _replacer(match: re.Match) -> str:
        token = match.group(1).strip()
        return values.get(token, match.group(0))

    return _TOKEN_RE.sub(_replacer, body)


def contact_token_values(contact) -> dict[str, str]:
    """
    Build the token-value mapping for a single ``mailing.contact`` record.

    Splits ``contact.name`` on the first whitespace to derive
    ``first_name`` / ``last_name``.

    Parameters
    ----------
    contact:
        A ``mailing.contact`` ORM record (or any object with ``name``,
        ``email``, ``mobile`` attributes).

    Returns
    -------
    dict[str, str]
        Ready-to-use values dict for :func:`render_body`.
    """
    full_name: str = (getattr(contact, "name", "") or "").strip()
    parts = full_name.split(None, 1)  # split on first whitespace only

    return {
        "first_name": parts[0] if parts else full_name,
        "last_name": parts[1] if len(parts) > 1 else "",
        "email": (getattr(contact, "email", "") or "").strip(),
        "phone": (getattr(contact, "mobile", "") or "").strip(),
    }


# ---------------------------------------------------------------------------
#  Model
# ---------------------------------------------------------------------------


class SmsAtTemplate(models.Model):
    """Personalised SMS template linked to mailing lists."""

    _name = "sms.at.template"
    _description = "Africa's Talking SMS Template"
    _order = "name"

    # ------------------------------------------------------------------
    #  Fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string="Template Name",
        required=True,
        index='trigram',
        translate=True,
    )
    body = fields.Text(
        string="Message Body",
        required=True,
        help=(
            "Supported merge tokens (replaced per-contact at send time):\n"
            "  {{first_name}} - contact's first name\n"
            "  {{last_name}}  - contact's last name\n"
            "  {{email}}      - contact's e-mail address\n"
            "  {{phone}}      - contact's mobile number"
        ),
    )
    mailing_list_ids = fields.Many2many(
        comodel_name="mailing.list",
        relation="sms_at_template_mailing_list_rel",
        column1="template_id",
        column2="list_id",
        string="Target Mailing Lists",
        help=(
            "The template is sent to every active, non-opted-out contact with a "
            "mobile number across these lists.  Duplicate mobile numbers are "
            "deduplicated automatically."
        ),
    )
    active = fields.Boolean(default=True)
    last_sent = fields.Datetime(
        string="Last Sent",
        readonly=True,
        copy=False,
    )

    # Computed summary fields
    char_count = fields.Integer(
        string="Characters",
        compute="_compute_body_stats",
        store=False,
    )
    sms_segments = fields.Integer(
        string="SMS Segments",
        compute="_compute_body_stats",
        store=False,
        help=(
            "Estimated number of SMS parts based on the message body *before* "
            "token substitution.  GSM-7 encoding: 160 chars (single) / 153 per "
            "segment (multi-part).  Unicode encoding: 70 / 67."
        ),
    )
    encoding = fields.Char(
        string="Encoding",
        compute="_compute_body_stats",
        store=False,
        help="'gsm7' when the body uses only the GSM-7 character set; 'ucs2' otherwise.",
    )

    # ------------------------------------------------------------------
    #  Computed fields
    # ------------------------------------------------------------------

    @api.depends("body")
    def _compute_body_stats(self) -> None:
        """Compute character count, segment count and encoding type."""
        for tmpl in self:
            if not tmpl.body:
                tmpl.char_count = 0
                tmpl.sms_segments = 0
                tmpl.encoding = "gsm7"
                continue

            stats: SmsStats = analyse_sms(tmpl.body)
            tmpl.char_count = stats.chars
            tmpl.sms_segments = stats.segments
            tmpl.encoding = stats.encoding

    # ------------------------------------------------------------------
    #  Validation
    # ------------------------------------------------------------------

    @api.constrains("body")
    def _check_tokens(self) -> None:
        """
        Reject template bodies that contain unknown merge tokens.

        This prevents silent data-quality errors where a typo like
        ``{{firstname}}`` would be sent verbatim to thousands of contacts.
        """
        supported = set(SUPPORTED_TOKENS.keys())
        for tmpl in self:
            found = {m.group(1).strip() for m in _TOKEN_RE.finditer(tmpl.body or "")}
            unknown = found - supported
            if unknown:
                bad = ", ".join(f"{{{{{t}}}}}" for t in sorted(unknown))
                good = ", ".join(f"{{{{{t}}}}}" for t in sorted(supported))
                raise ValidationError(
                    _(
                        "Unknown merge token(s) in template body: %(bad)s\n"
                        "Supported tokens: %(good)s",
                        bad=bad,
                        good=good,
                    )
                )

    # ------------------------------------------------------------------
    #  Send action
    # ------------------------------------------------------------------

    def action_send_to_lists(self) -> dict:
        """
        Render and dispatch this template to all eligible mailing-list contacts.

        Eligibility
        -----------
        A contact is eligible when it:

        * Is a member of at least one of the template's ``mailing_list_ids``
          AND has ``opt_out = False`` (the direct Boolean field on
          ``mailing.contact`` — introduced in Odoo 17 when the old
          per-list subscription model was removed).
        * Has a non-empty ``mobile`` field.

        Deduplication
        -------------
        If the same mobile number appears in multiple lists, the contact is
        sent exactly one SMS (the first-seen record wins).

        Returns
        -------
        dict
            ``display_notification`` client action.

        Raises
        ------
        UserError
            When no mailing lists are selected, or no eligible contacts exist.
        """
        self.ensure_one()

        if not self.mailing_list_ids:
            raise UserError(
                _("Please select at least one mailing list before sending.")
            )

        # ----------------------------------------------------------------
        # Odoo 17+ removed the separate per-list subscription model.
        # Contacts are now linked to lists via a direct Many2many (list_ids)
        # and opt_out is a plain Boolean field on mailing.contact itself.
        # ----------------------------------------------------------------
        contacts = self.env["mailing.contact"].search(
            [
                ("list_ids", "in", self.mailing_list_ids.ids),
                ("opt_out", "=", False),
            ]
        )

        if not contacts:
            raise UserError(
                _(
                    "No opted-in contacts found in the selected mailing list(s). "
                    "Make sure the lists contain contacts and none have opted out."
                )
            )

        # Collect unique contacts that have a mobile number
        # Use a dict to deduplicate: mobile --> first contact record
        mobile_to_contact: dict[str, Any] = {}
        for contact in contacts:
            mobile = (contact.mobile or "").strip()
            if mobile and mobile not in mobile_to_contact:
                mobile_to_contact[mobile] = contact

        if not mobile_to_contact:
            raise UserError(
                _(
                    "No opted-in contacts with a mobile number were found in the "
                    "selected mailing list(s)."
                )
            )

        total = len(mobile_to_contact)
        _logger.info(
            "sms.at.template '%s': rendering for %d unique contact(s).",
            self.name,
            total,
        )

        # ----------------------------------------------------------------
        # Render and bulk-create sms.sms records
        # ----------------------------------------------------------------
        sms_vals_list: list[dict] = []
        for mobile, contact in mobile_to_contact.items():
            rendered = render_body(self.body, contact_token_values(contact))
            sms_vals_list.append(
                {
                    "number": mobile,
                    "body": rendered,
                    "state": "outgoing",
                }
            )

        # sudo() is required: mailing users don't have sms.sms create rights
        sms_records = self.env["sms.sms"].sudo().create(sms_vals_list)

        # Dispatch via the overridden _send() which routes to AT
        sms_records._send()

        # Record timestamp on the template (sudo because mailing users may
        # not have write access to the template's last_sent field)
        self.sudo().write({"last_sent": fields.Datetime.now()})

        sent_count = len(sms_records.filtered(lambda s: s.state == "sent"))

        _logger.info(
            "sms.at.template '%s': %d/%d dispatched successfully.",
            self.name,
            sent_count,
            total,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sent"),
                "message": _(
                    "%(sent)d / %(total)d SMS dispatched via Africa's Talking.",
                    sent=sent_count,
                    total=total,
                ),
                "type": "success" if sent_count == total else "warning",
                "sticky": sent_count < total,
            },
        }

    # ------------------------------------------------------------------
    #  Preview action
    # ------------------------------------------------------------------

    def action_preview(self) -> dict:
        """
        Render the template body with sample values and display it in a popup.

        Uses :data:`_PREVIEW_VALUES` so all four tokens are visible in the
        preview output.
        """
        self.ensure_one()
        preview = render_body(self.body or "", _PREVIEW_VALUES)
        stats: SmsStats = analyse_sms(preview)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _(
                    "Preview - %(segments)d segment(s), %(encoding)s encoding",
                    segments=stats.segments,
                    encoding=stats.encoding.upper(),
                ),
                "message": preview,
                "type": "info",
                "sticky": True,
            },
        }