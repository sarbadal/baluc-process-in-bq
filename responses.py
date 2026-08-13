"""HTTP response helpers."""

from __future__ import annotations

import json


def json_response(payload: dict[str, object], status_code: int):
    """Serialize JSON response for Cloud Function."""
    return (json.dumps(payload), status_code, {"Content-Type": "application/json"})
