"""Persistence helpers for report status history in GCS."""

from __future__ import annotations

import json
import logging

from google.api_core.exceptions import NotFound
from google.cloud import storage


logger = logging.getLogger(__name__)


def upsert_status_entry(storage_client: storage.Client, bucket_name: str, status_object_name: str, entry: dict[str, object], history_limit: int) -> None:
    """Insert or update one status row in report status JSON file."""
    rows = load_status_history(storage_client, bucket_name, status_object_name)
    report_id = str(entry.get("report_id", "")).strip()
    if not report_id:
        raise ValueError("entry.report_id is required")

    replaced = False
    for index, row in enumerate(rows):
        if str(row.get("report_id", "")).strip() == report_id:
            rows[index] = entry
            replaced = True
            break

    if not replaced:
        rows.insert(0, entry)

    payload = json.dumps(rows[: max(1, history_limit)], indent=2)
    blob = storage_client.bucket(bucket_name).blob(status_object_name)
    blob.upload_from_string(payload, content_type="application/json")


def load_status_history(storage_client: storage.Client, bucket_name: str, status_object_name: str) -> list[dict[str, object]]:
    """Read report status JSON list from GCS."""
    blob = storage_client.bucket(bucket_name).blob(status_object_name)
    try:
        if not blob.exists(storage_client):
            return []
    except NotFound:
        return []

    text = blob.download_as_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Invalid status JSON in gs://%s/%s", bucket_name, status_object_name)
        return []

    if not isinstance(parsed, list):
        return []

    normalized: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized
