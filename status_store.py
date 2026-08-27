"""Persistence helpers for report status history in GCS."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging

from google.api_core.exceptions import NotFound
from google.cloud import storage


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusStoreParams:
    storage_client: storage.Client
    bucket_name: str
    status_object_name: str


@dataclass(frozen=True)
class LoadStatusHistoryParams(StatusStoreParams):
    pass


@dataclass(frozen=True)
class UpsertStatusEntryParams(StatusStoreParams):
    entry: dict[str, object]
    history_limit: int


def upsert_status_entry(params: UpsertStatusEntryParams) -> None:
    """Insert or update one status row in report status JSON file."""
    rows = load_status_history(
        LoadStatusHistoryParams(
            storage_client=params.storage_client,
            bucket_name=params.bucket_name,
            status_object_name=params.status_object_name,
        )
    )
    report_id = str(params.entry.get("report_id", "")).strip()
    if not report_id:
        raise ValueError("entry.report_id is required")

    replaced = False
    for index, row in enumerate(rows):
        if str(row.get("report_id", "")).strip() == report_id:
            rows[index] = params.entry
            replaced = True
            break

    if not replaced:
        rows.insert(0, params.entry)

    payload = json.dumps(rows[: max(1, params.history_limit)], indent=2)
    blob = params.storage_client.bucket(params.bucket_name).blob(params.status_object_name)
    blob.upload_from_string(payload, content_type="application/json")


def load_status_history(params: LoadStatusHistoryParams) -> list[dict[str, object]]:
    """Read report status JSON list from GCS."""
    blob = (
        params
        .storage_client.bucket(params.bucket_name)
        .blob(params.status_object_name)
    )
    try:
        if not blob.exists(params.storage_client):
            return []
    except NotFound:
        return []

    text = blob.download_as_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(
            "Invalid status JSON in gs://%s/%s", 
            params.bucket_name, 
            params.status_object_name
        )
        return []

    if not isinstance(parsed, list):
        return []

    normalized: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized
