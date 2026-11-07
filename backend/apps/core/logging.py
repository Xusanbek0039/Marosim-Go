"""Logging filter that keeps PINFLs, passwords and tokens out of every log line."""

import logging
import re

_PATTERNS = [
    (re.compile(r"(?<!\d)\d{14}(?!\d)"), "[PINFL]"),
    (
        re.compile(r"(?i)(\"?(?:password|pinfl|token|access|refresh|secret)\"?\s*[:=]\s*)\"?[^\s,&\"}]+"),
        r"\1[REDACTED]",
    ),
    (re.compile(r"(?i)bearer\s+[a-z0-9\-_.]+"), "Bearer [REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never break logging
            return True
        record.msg = redact(message)
        record.args = ()
        return True
