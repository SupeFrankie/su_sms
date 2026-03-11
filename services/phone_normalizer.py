# services/phone_normalizer.py


"""
services/phone_normalizer.py
=============================

Lightweight E.164 phone-number normaliser for Africa's Talking dispatch.

Africa's Talking requires numbers in E.164 format (``+<country><subscriber>``).
This module provides a best-effort normaliser that handles the most common
formats encountered in East African Odoo deployments without requiring the
``phonenumbers`` library (which would add ~10 MB to the module footprint).

If you need strict ITU-T E.164 validation install the ``phonenumbers`` package
and replace :func:`normalize_e164` with a ``phonenumbers.parse`` call.

Supported input formats
-----------------------
* Already correct - ``+254712345678``         --> ``+254712345678``
* Missing leading + - ``254712345678``         --> ``+254712345678``
* Local Kenyan 07xx / 01xx - ``0712345678``    --> **rejected** (no country code)
* Spaces, dashes, parentheses stripped first   - ``+254 712-345 678`` --> ``+254712345678``
* Short numbers (< 7 digits after country)     --> rejected

Callers that need to handle local numbers should prepend the country calling
code *before* storing the number on ``mailing.contact.mobile``.
"""

from __future__ import annotations

import re

# Strip every character except digits and a leading +
_STRIP_RE = re.compile(r"[^\d+]")
# E.164 pattern: optional leading +, 7-15 digits
_E164_RE = re.compile(r"^\+?\d{7,15}$")


class PhoneNormalizeError(ValueError):
    """Raised when a phone number cannot be normalised to E.164."""


def normalize_e164(raw: str) -> str:
    """
    Normalise *raw* to an E.164 phone number string.

    The function is intentionally lenient about formatting characters (spaces,
    dashes, parentheses) but strict about length and structure.

    Parameters
    ----------
    raw:
        Raw phone number string from any source.

    Returns
    -------
    str
        E.164 string beginning with ``+``, e.g. ``+254712345678``.

    Raises
    ------
    PhoneNormalizeError
        When the number cannot be coerced into a valid E.164 string.

    Examples
    --------
    >>> normalize_e164("+254712345678")
    '+254712345678'
    >>> normalize_e164("254712345678")
    '+254712345678'
    >>> normalize_e164("+254 712 345 678")
    '+254712345678'
    >>> normalize_e164("0712345678")
    Traceback (most recent call last):
        ...
    PhoneNormalizeError: ...
    """
    if not raw or not raw.strip():
        raise PhoneNormalizeError("Phone number is empty.")

    # Preserve a leading + before stripping non-digits
    raw = raw.strip()
    has_plus = raw.startswith("+")
    digits = _STRIP_RE.sub("", raw)

    if not digits:
        raise PhoneNormalizeError(f"No digits found in phone number: {raw!r}")

    # Reassemble with leading + if present or if it looks like a full
    # international number (>= 10 digits, does not start with 0)
    if has_plus:
        # Strip any accidental duplicate + that might appear after stripping
        candidate = f"+{digits.lstrip('+')}"
    elif digits.startswith("0"):
        # Local format - we cannot determine the country code
        raise PhoneNormalizeError(
            f"Phone number {raw!r} appears to be in local format (starts with 0). "
            "Prepend the country calling code (e.g. +254 for Kenya) before storing."
        )
    else:
        # Assume the country code is already present without the +
        candidate = f"+{digits}"

    if not _E164_RE.match(candidate):
        raise PhoneNormalizeError(
            f"Phone number {raw!r} could not be normalised to E.164 "
            f"(result {candidate!r} does not match the expected pattern)."
        )

    return candidate


def try_normalize_e164(raw: str) -> str | None:
    """
    Like :func:`normalize_e164` but returns ``None`` instead of raising.

    Convenient for filtering rather than exception-based flow control.

    >>> try_normalize_e164("+254712345678")
    '+254712345678'
    >>> try_normalize_e164("bad number") is None
    True
    """
    try:
        return normalize_e164(raw)
    except PhoneNormalizeError:
        return None
