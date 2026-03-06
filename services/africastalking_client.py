# Copyright 2024 Strathmore University
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
services/africastalking_client.py
==================================

Standalone HTTP client for the Africa's Talking Messaging REST API (v1).

Design goals
------------
* **No Odoo import** – this module is independently importable and unit-testable
  without a running Odoo instance.
* **Standard library only** – uses ``urllib`` so no third-party packages are
  required.  The ``africastalking`` SDK is intentionally avoided because it
  pins an old ``requests`` version that conflicts with Odoo's vendored deps.
* **Structured exceptions** – all failure modes raise :class:`ATError` with
  enough context for the caller to decide how to classify the record.
* **Single responsibility** – this class only handles HTTP communication and
  response parsing.  Credential management and ORM writes stay in the models.

Africa's Talking API reference
-------------------------------
Endpoint : POST https://api.africastalking.com/version1/messaging
Sandbox  : POST https://api.sandbox.africastalking.com/version1/messaging

Request headers::

    Accept: application/json
    ApiKey: <your-api-key>
    Content-Type: application/x-www-form-urlencoded

Form fields::

    username  – AT account username
    to        – comma-separated E.164 phone numbers
    message   – SMS body text (max ~1 600 chars for multi-part)
    from      – (optional) registered sender ID / short-code

Response body (JSON)::

    {
      "SMSMessageData": {
        "Message": "Sent to 2/2 Total Cost: KES 1.0000",
        "Recipients": [
          {
            "statusCode": 101,
            "number": "+254712345678",
            "status": "Success",
            "cost": "KES 0.8000",
            "messageId": "ATXid_...",
            "messageParts": 1
          }
        ]
      }
    }

AT ``statusCode`` values:
  100  Processed        (should not appear; means queued)
  101  Sent             (accepted by carrier)
  102  Queued
  401  Risk Hold
  402  InvalidSenderId
  403  InvalidPhoneNumber
  404  UnsupportedNumberType
  405  InsufficientBalance
  406  UserInBlacklist
  407  CouldNotRoute
  409  DoNotDisturb
  500  InternalServerError
  501  GatewayError
  502  RejectedByGateway
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

LIVE_URL = "https://api.africastalking.com/version1/messaging"
SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"

#: Maximum recipients in a single AT API call.
AT_BATCH_LIMIT: int = 1_000

#: Default HTTP timeout in seconds.
DEFAULT_TIMEOUT: int = 30

#: AT ``status`` strings that map to a successful Odoo send state.
#: "Success" is the send-time acceptance status; "Delivered" arrives via the
#: delivery-report webhook.  We accept both so a single send response can
#: optimistically mark records as sent even before the webhook fires.
AT_SUCCESS_STATUSES: frozenset[str] = frozenset({"Success", "Sent", "Delivered"})

#: AT ``status`` strings that indicate the message is still in transit.
#: Keep the record as "sent" (Odoo has no "pending_delivery" state) and wait
#: for a delivery webhook to either confirm or deny.
AT_BUFFERED_STATUSES: frozenset[str] = frozenset({"Buffered", "Queued"})


# ---------------------------------------------------------------------------
#  Exceptions
# ---------------------------------------------------------------------------


class ATError(Exception):
    """
    Base exception for Africa's Talking API errors.

    Attributes
    ----------
    message:
        Human-readable description.
    http_status:
        HTTP response code, or ``None`` for network-level failures.
    raw_body:
        Raw response body string, or ``None`` if no body was received.
    retryable:
        ``True`` when the failure is likely transient (5xx, timeout,
        connection error) and the caller *may* retry.
    """

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        raw_body: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.raw_body = raw_body
        self.retryable = retryable

    def __repr__(self) -> str:
        return (
            f"ATError({self.args[0]!r}, "
            f"http_status={self.http_status}, "
            f"retryable={self.retryable})"
        )


class ATAuthError(ATError):
    """Raised when AT returns HTTP 401 or when credentials are missing."""


class ATValidationError(ATError):
    """Raised when AT returns HTTP 400 (bad request / bad payload)."""


# ---------------------------------------------------------------------------
#  Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ATRecipientResult:
    """
    Represents the per-recipient outcome from a single AT API call.

    All fields are populated from the ``Recipients`` array in the AT response.
    """

    number: str
    """E.164 phone number as echoed back by AT."""

    status: str
    """AT status string, e.g. ``'Success'``, ``'InvalidPhoneNumber'``."""

    message_id: str
    """AT message ID used to correlate delivery-report callbacks."""

    status_code: int
    """AT numeric status code (101 = sent, 402 = invalid sender, etc.)."""

    cost: str = ""
    """Cost string as returned by AT, e.g. ``'KES 0.8000'``."""

    message_parts: int = 1
    """Number of SMS segments consumed."""

    @property
    def succeeded(self) -> bool:
        """``True`` when AT accepted the message for delivery."""
        return self.status in AT_SUCCESS_STATUSES

    @property
    def buffered(self) -> bool:
        """``True`` when AT accepted but delivery is still pending."""
        return self.status in AT_BUFFERED_STATUSES

    @property
    def failed(self) -> bool:
        """``True`` when AT definitively rejected the message."""
        return not self.succeeded and not self.buffered


# ---------------------------------------------------------------------------
#  Client
# ---------------------------------------------------------------------------


class AfricasTalkingClient:
    """
    Thin HTTP client for the Africa's Talking Messaging API.

    Parameters
    ----------
    username:
        AT account username.  Use ``"sandbox"`` for testing.
    api_key:
        AT API key from your AT dashboard.
    sender_id:
        Registered alphanumeric sender ID or short-code.  Pass ``""`` or
        ``None`` to use the shared short-code.
    sandbox:
        When ``True`` all requests go to the AT sandbox endpoint.
    timeout:
        Per-request HTTP timeout in seconds.

    Example
    -------
    >>> client = AfricasTalkingClient("myuser", "secret-key", sandbox=True)
    >>> results = client.send(["+254712345678"], "Hello from Odoo!")
    >>> results[0].succeeded
    True
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        *,
        sender_id: str = "",
        sandbox: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        if not username:
            raise ATAuthError(
                "Africa's Talking username is required.",
                retryable=False,
            )
        if not api_key:
            raise ATAuthError(
                "Africa's Talking API key is required.",
                retryable=False,
            )

        self.username = username.strip()
        self.api_key = api_key.strip()
        self.sender_id = (sender_id or "").strip()
        self.sandbox = sandbox
        self.timeout = timeout
        self._url = SANDBOX_URL if sandbox else LIVE_URL

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def send(
        self,
        to: list[str],
        message: str,
    ) -> list[ATRecipientResult]:
        """
        Send *message* to every phone number in *to*.

        The caller is responsible for chunking the recipient list to at most
        :data:`AT_BATCH_LIMIT` entries before calling this method.

        Parameters
        ----------
        to:
            Non-empty list of E.164 phone numbers.
        message:
            Plain-text SMS body.  Must not be blank.

        Returns
        -------
        list[ATRecipientResult]
            Per-recipient results.  May be empty if AT returns an empty
            ``Recipients`` array (rare but handled defensively).

        Raises
        ------
        ATAuthError
            On HTTP 401.
        ATValidationError
            On HTTP 400 (malformed payload).
        ATError
            On HTTP 5xx, timeout or network failure.
        ValueError
            If *to* is empty or *message* is blank.
        """
        if not to:
            raise ValueError("Recipient list 'to' must not be empty.")
        if not message or not message.strip():
            raise ValueError("Message body must not be blank.")

        payload = self._build_payload(to, message)
        raw = self._post(payload)
        return self._parse(raw)

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self, to: list[str], message: str) -> bytes:
        """Encode POST body as ``application/x-www-form-urlencoded``."""
        data: dict[str, str] = {
            "username": self.username,
            "to": ",".join(to),
            "message": message,
        }
        if self.sender_id:
            data["from"] = self.sender_id
        return urllib.parse.urlencode(data).encode("utf-8")

    def _post(self, payload: bytes) -> dict[str, Any]:
        """
        Execute the HTTP POST and return the parsed JSON response body.

        Raises
        ------
        ATAuthError
            On HTTP 401.
        ATValidationError
            On HTTP 400.
        ATError
            On any other HTTP error, timeout or connection failure.
        """
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Accept": "application/json",
                "ApiKey": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        _logger.debug(
            "AT POST %s  sandbox=%s  sender_id=%r",
            self._url,
            self.sandbox,
            self.sender_id or "(shared short-code)",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            _logger.error("AT HTTP %d – %s", exc.code, raw[:500])
            if exc.code == 401:
                raise ATAuthError(
                    f"Africa's Talking rejected the API key (HTTP 401).",
                    http_status=401,
                    raw_body=raw,
                    retryable=False,
                ) from exc
            if exc.code == 400:
                raise ATValidationError(
                    f"Africa's Talking rejected the request (HTTP 400): {raw[:200]}",
                    http_status=400,
                    raw_body=raw,
                    retryable=False,
                ) from exc
            # 5xx – transient; caller may retry
            raise ATError(
                f"Africa's Talking returned HTTP {exc.code}: {raw[:200]}",
                http_status=exc.code,
                raw_body=raw,
                retryable=exc.code >= 500,
            ) from exc
        except TimeoutError as exc:
            _logger.error("AT request timed out after %ds.", self.timeout)
            raise ATError(
                f"Africa's Talking API timed out after {self.timeout}s.",
                retryable=True,
            ) from exc
        except urllib.error.URLError as exc:
            _logger.error("AT connection error: %s", exc.reason)
            raise ATError(
                f"Could not reach Africa's Talking API: {exc.reason}",
                retryable=True,
            ) from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            _logger.error("AT non-JSON response: %s", body[:500])
            raise ATError(
                "Africa's Talking returned a non-JSON response.",
                raw_body=body,
                retryable=False,
            ) from exc

    @staticmethod
    def _parse(data: dict[str, Any]) -> list[ATRecipientResult]:
        """
        Extract ``Recipients`` from the AT response envelope.

        AT wraps results under ``SMSMessageData.Recipients``.  If that key is
        absent the batch likely failed at the account level (e.g. zero balance)
        and an empty list is returned so the caller can mark all records as
        errored.
        """
        sms_data = data.get("SMSMessageData") or {}
        summary = sms_data.get("Message", "")
        recipients_raw: list[dict[str, Any]] = sms_data.get("Recipients") or []

        _logger.info(
            "AT response: %s  (%d recipient result(s))",
            summary,
            len(recipients_raw),
        )

        results: list[ATRecipientResult] = []
        for r in recipients_raw:
            results.append(
                ATRecipientResult(
                    number=str(r.get("number", "")).strip(),
                    status=str(r.get("status", "")).strip(),
                    message_id=str(r.get("messageId", "")).strip(),
                    status_code=int(r.get("statusCode", 0)),
                    cost=str(r.get("cost", "")),
                    message_parts=int(r.get("messageParts", 1)),
                )
            )

        return results
