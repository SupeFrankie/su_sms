# sms\_africastalking\_provider

Odoo 19 add-on that replaces the default Odoo IAP SMS gateway with
[Africa's Talking](https://africastalking.com/).

---

## What's new in v1.1.0

| Area | Change |
|------|--------|
| **Security** | Delivery webhook now validates an optional `Authorization: Bearer` token — unauthenticated callbacks can no longer alter SMS states |
| **Reliability** | Phone numbers are normalised to E.164 before dispatch; invalid numbers fail fast with `sms_number_format` instead of wasting an API call |
| **Correctness** | Bug fix: API errors previously marked the entire 1 000-record batch as failed; now only the affected body-group records are marked |
| **Correctness** | Bug fix: `num_index` dict lost duplicate phone numbers; fixed to map number --> *list* of records |
| **Correctness** | Fallback to Odoo IAP when AT credentials are absent (was a silent no-op before) |
| **Tokens** | Templates now support `{{last_name}}`, `{{email}}` and `{{phone}}` in addition to `{{first_name}}` |
| **SMS counting** | Accurate GSM-7 vs Unicode segment calculation (was always 160 chars/part regardless of encoding) |
| **Performance** | O(n) contact deduplication (was O(n²) `|=` loop) |
| **Opt-out** | Queries `mailing.contact.subscription` directly for correct per-list opt-out filtering |
| **Architecture** | HTTP client extracted to `services/africastalking_client.py` — independently testable without Odoo |
| **Observability** | New `at_failure_reason` field stores AT error descriptions persistently on each record |
| **Settings** | New Webhook Verification Token and API Request Timeout settings |

---

## Features

| Feature | Detail |
|---------|--------|
| **AT Gateway** | All `sms.sms` records dispatched via Africa's Talking REST API |
| **IAP Fallback** | Transparently falls back to Odoo IAP when AT credentials are not configured |
| **Phone normalisation** | Numbers normalised to E.164; invalid numbers marked immediately |
| **Delivery reports** | Webhook at `/sms/africastalking/delivery` with Bearer-token authentication |
| **Retry button** | Visible only on error records; reports sent vs still-failed counts |
| **SMS Templates** | `sms.at.template` with four merge tokens and accurate segment counting |
| **Mailing lists** | Reuses native `mailing.list` / `mailing.contact` — no new model |
| **Settings** | Credentials, sandbox toggle, webhook token and timeout in General Settings |

---

## Installation

1. Copy `sms_africastalking_provider/` into your Odoo addons path.
2. Restart Odoo and update the apps list.
3. Install **SU SMS - Africa's Talking Provider** from the Apps menu.

**Required Odoo modules** (declared as dependencies, installed automatically):

- `sms`
- `base_setup`
- `mass_mailing`

---

## Configuration

### 1 - API credentials

Go to **Settings --> General Settings --> SMS - Africa's Talking** and fill in:

| Field | Description |
|-------|-------------|
| Username | Your AT account username (use `sandbox` while testing) |
| API Key | Found in your AT dashboard under **Settings --> API Key** |
| Sender ID | Alphanumeric sender or short-code (leave empty for shared short-code) |
| Use Sandbox | Routes all messages through AT sandbox when enabled |
| API Request Timeout | Per-request timeout in seconds (default: 30) |

### 2 - Delivery webhook

In your Africa's Talking dashboard go to **SMS --> Delivery Reports** and set
the callback URL to:

```
https://<your-odoo-domain>/sms/africastalking/delivery
```

Verify the URL is live by opening it in a browser — it returns a plain-text
confirmation message.

### 3 - Webhook token (recommended for production)

Generate a random secret (e.g. `openssl rand -hex 32`) and:

1. Enter it in **Settings --> General Settings --> SMS - Africa's Talking -->
   Webhook Verification Token**.
2. Configure Africa's Talking to include the header
   `Authorization: Bearer <your-secret>` in every callback.

When the token is set the controller rejects requests with a wrong or absent
token with HTTP 401, causing AT to retry with corrected credentials.

---

## Usage

### Sending a template to mailing lists

1. Go to **Email Marketing --> Africa's Talking SMS --> SMS Templates**.
2. Create a template.  Use merge tokens in the body:

   | Token | Resolves to |
   |-------|-------------|
   | `{{first_name}}` | Contact's first name |
   | `{{last_name}}`  | Contact's last name |
   | `{{email}}`      | Contact's e-mail address |
   | `{{phone}}`      | Contact's mobile number |

3. Click **Preview** to see a rendered sample before sending.
4. Select one or more **Target Mailing Lists**.
5. Click **Send to Lists**.  Only opted-in contacts with a mobile number
   receive the SMS; duplicate numbers are sent exactly one message.

### Retrying failed SMS

1. Go to **Email Marketing --> Africa's Talking SMS --> SMS Queue**.
2. Open or select records with state **Error**.
3. Click **Retry Send**.  The notification tells you how many succeeded and
   how many still failed.

### Phone number format

Africa's Talking requires E.164 format (`+<country><subscriber>`).  Store
numbers on `mailing.contact.mobile` with the full country code:

| Format | Result |
|--------|--------|
| `+254712345678` | ✅ Accepted as-is |
| `254712345678` | ✅ `+` prepended automatically |
| `0712345678` | ❌ Rejected — prepend country code before storing |

---

## Delivery status mapping

| Africa's Talking status | Odoo `sms.sms.state` |
|------------------------|----------------------|
| `Success`, `Sent`, `Buffered`, `Delivered` | `sent` |
| `Failed`, `Rejected`, `UserInBlacklist`, others | `error` |

Final delivery confirmation (`Delivered`) arrives via the webhook and
updates the record from `sent` to `sent` (no change) or logs the failure
reason if delivery ultimately failed.

---

## Architecture

```
sms_africastalking_provider/
├── __manifest__.py
├── __init__.py
├── requirements.txt
├── controllers/
│   └── delivery.py          # Webhook: auth, status mapping, batch write
├── models/
│   ├── res_config_settings.py  # Settings fields + _get_at_credentials()
│   ├── sms_sms.py           # _send() override, retry button, AT fields
│   └── sms_at_template.py   # Template model with token rendering
├── services/                 # No Odoo imports - independently testable
│   ├── africastalking_client.py  # HTTP client, ATError hierarchy
│   ├── phone_normalizer.py  # E.164 normalisation
│   └── sms_encoding.py      # GSM-7 / UCS-2 segment counting
├── views/
│   ├── res_config_settings_views.xml
│   ├── sms_sms_views.xml
│   ├── sms_at_template_views.xml
│   └── menus.xml
├── security/
│   └── ir.model.access.csv
└── data/
    └── sms_template_data.xml
```

**Key design decisions:**

- The `services/` package contains **pure Python** with zero Odoo dependencies.
  This makes unit-testing the HTTP client and encoding logic trivial.
- `sms.sms._send()` falls back to `super()` (Odoo IAP) when AT credentials
  are absent, so the module is safe to deploy before credentials are entered.
- `sudo()` is used only where genuinely required (mailing users writing
  `sms.sms` records, webhook controller with `auth='none'`).  It is never
  used to bypass intentional access restrictions.

---

## License

LGPL-3.0 or later - see [LICENSE](https://www.gnu.org/licenses/lgpl-3.0.html).
