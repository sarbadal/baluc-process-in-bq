"""General utility helpers."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone


def now_iso() -> str:
    """Return UTC timestamp in ISO-8601 Z format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_report_object_name(reports_prefix: str, start_date: str, end_date: str, report_id: str) -> str:
    """Build final CSV object path in target reports folder."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    start = start_date.replace("-", "")
    end = end_date.replace("-", "")
    return f"{reports_prefix}/report_{stamp}_{start}_{end}_{report_id[:8]}.csv"


def build_download_url(bucket_name: str, object_name: str) -> str:
    """Build direct download URL for generated report object."""
    return f"https://storage.googleapis.com/{bucket_name}/{object_name.replace(' ', '%20')}"
