# services/sms_encoding.py


"""
services/sms_encoding.py
==========================

Accurate SMS character-count and segment calculation.

The original module always assumed 160 characters per SMS segment, which is
only correct for single-part GSM-7 encoded messages.  This module implements
the full encoding rules:

GSM-7 (7-bit) encoding
-----------------------
* Characters in the GSM 03.38 basic character set count as **1** unit each.
* Characters in the GSM 03.38 *extension table* (``[``, ``]``, ``{``, ``}``,
  ``\\``, ``^``, ``~``, ``|``, ``€``) count as **2** units each (ESC + char).
* Single-part message capacity: **160** GSM-7 units.
* Multi-part segment capacity: **153** GSM-7 units (7 units consumed by the
  UDH concatenation header per part).

UCS-2 (Unicode) encoding
--------------------------
* Any character *outside* the GSM-7 basic + extension set triggers UCS-2.
* Single-part message capacity: **70** characters.
* Multi-part segment capacity: **67** characters per part.

Reference: ETSI TS 123 038 (3GPP TS 23.038)
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
#  GSM-7 character tables
# ---------------------------------------------------------------------------

# Basic character set (each char = 1 GSM-7 unit)
_GSM7_BASIC: frozenset[str] = frozenset(
    # Row 0
    "@£$¥èéùìòÇ\nØø\rÅå"
    # Row 1
    "ΔΦΓΛΩΠΨΣΘΞÆæßÉ"
    # Row 2  (space through ?)
    " !\"#¤%&'()*+,-./0123456789:;<=>?"
    # Row 3  (¡ through U-umlaut)
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
    # Row 4  (¿ through à)
    "¿abcdefghijklmnopqrstuvwxyzäöñüà"
)

# Extension table characters (each = 2 GSM-7 units: ESC + char)
_GSM7_EXTENDED: frozenset[str] = frozenset("[]{}\\^~|€\f")

# Combined set - all characters that can be encoded in GSM-7
_GSM7_ALL: frozenset[str] = _GSM7_BASIC | _GSM7_EXTENDED

# ---------------------------------------------------------------------------
#  Thresholds
# ---------------------------------------------------------------------------

_GSM7_SINGLE = 160
_GSM7_MULTI = 153
_UCS2_SINGLE = 70
_UCS2_MULTI = 67


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SmsStats:
    """Result of analysing an SMS body."""

    encoding: str
    """``'gsm7'`` or ``'ucs2'``."""

    units: int
    """Total encoding units (GSM-7 counts extended chars as 2)."""

    segments: int
    """Number of SMS parts required to send this message."""

    chars: int
    """Raw character count (``len(body)``)."""


def analyse(body: str) -> SmsStats:
    """
    Analyse *body* and return encoding, unit count and segment count.

    Parameters
    ----------
    body:
        Plain-text message body (merge tokens should already be resolved if
        you want accurate counts for a specific recipient).

    Returns
    -------
    SmsStats
        Encoding details for the message.

    Examples
    --------
    >>> s = analyse("Hello World")
    >>> s.encoding
    'gsm7'
    >>> s.segments
    1

    >>> s = analyse("Hello 🌍")
    >>> s.encoding
    'ucs2'
    >>> s.segments
    1
    """
    if not body:
        return SmsStats(encoding="gsm7", units=0, segments=0, chars=0)

    chars = len(body)

    # Check whether every character fits in GSM-7
    is_gsm7 = all(ch in _GSM7_ALL for ch in body)

    if is_gsm7:
        # Count extended chars as 2 units each
        units = sum(2 if ch in _GSM7_EXTENDED else 1 for ch in body)
        if units <= _GSM7_SINGLE:
            segments = 1
        else:
            # Ceiling division
            segments = -(-units // _GSM7_MULTI)
        return SmsStats(encoding="gsm7", units=units, segments=segments, chars=chars)
    else:
        # UCS-2: every character is one unit but capacity is much lower
        units = chars
        if units <= _UCS2_SINGLE:
            segments = 1
        else:
            segments = -(-units // _UCS2_MULTI)
        return SmsStats(encoding="ucs2", units=units, segments=segments, chars=chars)


def is_gsm7(body: str) -> bool:
    """Return ``True`` when *body* can be encoded entirely in GSM-7."""
    return all(ch in _GSM7_ALL for ch in body)
