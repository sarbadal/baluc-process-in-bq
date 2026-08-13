"""Input and identifier validators."""

from __future__ import annotations

import re


def is_iso_date(value: str) -> bool:
    """Return True for ISO date string YYYY-MM-DD."""
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def is_safe_identifier(value: str) -> bool:
    """Allow letters, digits, underscores in SQL identifiers."""
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value))


def is_safe_bucket(value: str) -> bool:
    """Allow supported GCS bucket name characters."""
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]", value))


def is_safe_object_name(value: str) -> bool:
    """Allow safe object path characters for GCS output/status objects."""
    return bool(re.fullmatch(r"[A-Za-z0-9_./-]+", value))
