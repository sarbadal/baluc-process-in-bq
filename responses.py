"""HTTP response helpers."""

from __future__ import annotations

import json


def json_response(payload: dict[str, object], status_code: int):
    """Serialize JSON response for Cloud Function.

    Args:
        payload: The JSON-serializable dictionary to return in the response.
        status_code: The HTTP status code for the response.

    Returns:
        A tuple containing the JSON string, status code, and HTTP headers.

    Example Return:
        (
            '{"key": "value"}',  # JSON string
            200,  # HTTP status code
            {"Content-Type": "application/json"}  # HTTP headers
        )
    """
    return (
        json.dumps(payload),  # JSON serialized payload
        status_code,  # HTTP status code
        {"Content-Type": "application/json"}  # HTTP headers
    )
