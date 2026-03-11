# services/africastalking_client.py

"""
services/africastalking_client.py
==================================

Standalone HTTP client for the Africa's Talking Messaging and User REST APIs.

No Odoo imports — independently unit-testable.

Safaricom Promotional Filter — Kenya
--------------------------------------
WITHOUT a registered Sender ID, messages to Safaricom subscribers may land in
the *456# promotional inbox rather than the standard SMS inbox.  This is a
Safaricom network policy, not an AT restriction.

To ensure delivery to the main inbox:
1. Register a Sender ID (e.g. "StrathmoreU") in your AT dashboard under
   SMS --> Sender ID Management.
2. Await Safaricom approval (typically 2–5 business days).
3. Configure the approved Sender ID in Odoo Settings --> General Settings -->
   Africa's Talking SMS --> Sender ID / Short-code.

Until approved, use the shared short-code and advise recipients to check *456#.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Messaging API endpoints
# ---------------------------------------------------------------------------

LIVE_URL = "https://api.africastalking.com/version1/messaging"
SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"

# ---------------------------------------------------------------------------
#  Balance / User API endpoints
# ---------------------------------------------------------------------------

BALANCE_LIVE_URL = "https://api.africastalking.com/version1/user"
BALANCE_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/user"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

#: Hard maximum recipients per AT API call (AT platform limit).
AT_BATCH_LIMIT: int = 1_000

#: Rate-limiting: recipients per API call before sleeping.
#: Keeping this at 1 000 uses AT's full capacity.  Reduce (e.g. to 50) if
#: you experience throttling errors on very high-volume sends.
AT_RATE_LIMIT_BATCH: int = 1_000

#: Seconds to sleep between successive AT API calls during a batch send.
AT_RATE_LIMIT_SLEEP: float = 1.0

#: Default HTTP timeout in seconds.
DEFAULT_TIMEOUT: int = 30

#: AT status strings that map to a successful Odoo send state at dispatch time.
AT_SUCCESS_STATUSES: frozenset[str] = frozenset({"Success", "Sent", "Delivered"})

#: AT status strings indicating message is queued / still in transit.
AT_BUFFERED_STATUSES: frozenset[str] = frozenset({"Buffered", "Queued"})


# ---------------------------------------------------------------------------
#  Exceptions
# ---------------------------------------------------------------------------


class ATError(Exception):
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
    """Raised when AT returns HTTP 400."""


# ---------------------------------------------------------------------------
#  Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ATRecipientResult:
    """Per-recipient outcome from a single AT send call."""

    number: str
    status: str
    message_id: str
    status_code: int
    cost: str = ""
    message_parts: int = 1

    @property
    def succeeded(self) -> bool:
        return self.status in AT_SUCCESS_STATUSES

    @property
    def buffered(self) -> bool:
        return self.status in AT_BUFFERED_STATUSES

    @property
    def failed(self) -> bool:
        return not self.succeeded and not self.buffered


# ---------------------------------------------------------------------------
#  Client
# ---------------------------------------------------------------------------


class AfricasTalkingClient:
    """
    Thin HTTP client for the Africa's Talking Messaging and User APIs.

    Parameters
    ----------
    username:
        AT account username.  Use ``"sandbox"`` for testing.
    api_key:
        AT API key from your AT dashboard.
    sender_id:
        Registered alphanumeric sender ID.  Leave blank for shared short-code.
        Required to bypass Safaricom promotional filter in Kenya.
    sandbox:
        When ``True`` all requests go to the AT sandbox endpoints.
    timeout:
        Per-request HTTP timeout in seconds.
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
            raise ATAuthError("Africa's Talking username is required.", retryable=False)
        if not api_key:
            raise ATAuthError("Africa's Talking API key is required.", retryable=False)

        self.username = username.strip()
        self.api_key = api_key.strip()
        self.sender_id = (sender_id or "").strip()
        self.sandbox = sandbox
        self.timeout = timeout
        self._url = SANDBOX_URL if sandbox else LIVE_URL
        self._balance_url = BALANCE_SANDBOX_URL if sandbox else BALANCE_LIVE_URL

    # ------------------------------------------------------------------
    #  Messaging API
    # ------------------------------------------------------------------

    def send(self, to: list[str], message: str) -> list[ATRecipientResult]:
        """
        Send *message* to every phone number in *to*.

        Caller must chunk recipient list to <= AT_BATCH_LIMIT before calling.

        Raises
        ------
        ATAuthError, ATValidationError, ATError, ValueError
        """
        if not to:
            raise ValueError("Recipient list 'to' must not be empty.")
        if not message or not message.strip():
            raise ValueError("Message body must not be blank.")

        payload = self._build_payload(to, message)
        raw = self._post(self._url, payload)
        return self._parse_messaging(raw)

    # ------------------------------------------------------------------
    #  Balance / User API
    # ------------------------------------------------------------------

    def get_balance(self) -> str:
        """
        Retrieve the current AT account balance.

        Returns
        -------
        str
            Balance string with currency code, e.g. ``"KES 1023.5000"``.

        Raises
        ------
        ATAuthError
            On HTTP 401.
        ATError
            On HTTP 5xx, timeout or network failure.
        """
        params = urllib.parse.urlencode({"username": self.username})
        full_url = f"{self._balance_url}?{params}"

        req = urllib.request.Request(
            full_url,
            headers={
                "Accept": "application/json",
                "ApiKey": self.api_key,
            },
            method="GET",
        )

        _logger.debug("AT GET balance  url=%s  sandbox=%s", self._balance_url, self.sandbox)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            _logger.error("AT balance HTTP %d - %s", exc.code, raw[:300])
            if exc.code == 401:
                raise ATAuthError(
                    "Africa's Talking rejected the API key (HTTP 401). "
                    "Check your username and API key in Settings.",
                    http_status=401,
                    raw_body=raw,
                    retryable=False,
                ) from exc
            raise ATError(
                f"Africa's Talking balance endpoint returned HTTP {exc.code}: {raw[:200]}",
                http_status=exc.code,
                raw_body=raw,
                retryable=exc.code >= 500,
            ) from exc
        except TimeoutError as exc:
            raise ATError(
                f"Balance request timed out after {self.timeout}s.",
                retryable=True,
            ) from exc
        except urllib.error.URLError as exc:
            raise ATError(
                f"Could not reach Africa's Talking API: {exc.reason}",
                retryable=True,
            ) from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            _logger.error("AT balance non-JSON response: %s", body[:300])
            raise ATError(
                "Africa's Talking returned a non-JSON response for the balance request.",
                raw_body=body,
                retryable=False,
            ) from exc

        user_data = data.get("UserData") or {}
        balance = user_data.get("balance", "Unknown")
        _logger.info("AT balance: %s (sandbox=%s)", balance, self.sandbox)
        return str(balance)

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self, to: list[str], message: str) -> bytes:
        data: dict[str, str] = {
            "username": self.username,
            "to": ",".join(to),
            "message": message,
        }
        if self.sender_id:
            data["from"] = self.sender_id
        return urllib.parse.urlencode(data).encode("utf-8")

    def _post(self, url: str, payload: bytes) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
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
            url,
            self.sandbox,
            self.sender_id or "(shared short-code)",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            _logger.error("AT HTTP %d - %s", exc.code, raw[:500])
            if exc.code == 401:
                raise ATAuthError(
                    "Africa's Talking rejected the API key (HTTP 401).",
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
    def _parse_messaging(data: dict[str, Any]) -> list[ATRecipientResult]:
        """Extract Recipients from the AT messaging response envelope."""
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
