"""Request handlers for report generation and status retrieval."""

from __future__ import annotations

import logging
import uuid

from google.cloud import bigquery
from google.cloud import storage

from config import load_config
from responses import json_response
from sql_builder import build_bq_sql_script
from status_store import load_status_history
from status_store import upsert_status_entry
from utils import build_download_url
from utils import build_report_object_name
from utils import now_iso
from validators import is_iso_date


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def process_report_request(request):
    """Accept report request and execute full report processing using BigQuery SQL only."""
    if request.method == "GET":
        return _handle_get_status(request)
    if request.method != "POST":
        return json_response({"error": "Method not allowed. Use POST or GET."}, 405)

    payload = request.get_json(silent=True) or {}
    start_date = str(payload.get("start_date", "")).strip()
    end_date = str(payload.get("end_date", "")).strip()

    if not start_date or not end_date:
        return json_response(
            {"error": "start_date and end_date are required in request body (YYYY-MM-DD)."},
            400,
        )
    if not is_iso_date(start_date) or not is_iso_date(end_date):
        return json_response(
            {"error": "start_date and end_date must be in YYYY-MM-DD format."},
            400,
        )

    config = load_config()
    if "error" in config:
        return json_response(config, 500)

    report_id = str(uuid.uuid4())
    requested_at = now_iso()
    output_object_name = build_report_object_name(
        reports_prefix=str(config["target_reports_prefix"]),
        start_date=start_date,
        end_date=end_date,
        report_id=report_id,
    )
    output_object_prefix = output_object_name.removesuffix(".csv") + "_"
    output_object_wildcard_name = output_object_prefix + "*.csv"
    output_gcs_uri = f"gs://{config['target_bucket']}/{output_object_wildcard_name}"

    storage_client = storage.Client(project=str(config["project_id"]))
    bq_client = bigquery.Client(project=str(config["project_id"]))

    generating_entry = {
        "report_id": report_id,
        "report_type": "BQ_PRINT",
        "start_date": start_date,
        "end_date": end_date,
        "requested_at": requested_at,
        "updated_at": requested_at,
        "status": "Processing",
        "success": False,
        "csv_object_name": None,
        "download_object_name": None,
        "download_url": None,
        "report_file": None,
        "error": None,
    }
    upsert_status_entry(
        storage_client=storage_client,
        bucket_name=str(config["target_bucket"]),
        status_object_name=str(config["status_object_name"]),
        entry=generating_entry,
        history_limit=int(config["status_history_limit"]),
    )

    try:
        sql_script = build_bq_sql_script(config=config, output_gcs_uri=output_gcs_uri)
        query_job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
                bigquery.ScalarQueryParameter("ev_source_filter", "STRING", str(config["ev_source_filter"])),
                bigquery.ScalarQueryParameter(
                    "contract_source_filter",
                    "STRING",
                    str(config["contract_source_filter"]),
                ),
            ]
        )
        query_job = bq_client.query(
            sql_script,
            location=str(config["bq_location"]),
            job_config=query_job_config,
        )
        query_job.result()

        exported_objects = _find_exported_objects(
            storage_client=storage_client,
            bucket_name=str(config["target_bucket"]),
            prefix=output_object_prefix,
        )
        report_file = exported_objects[0] if exported_objects else output_object_wildcard_name
        download_url = (
            build_download_url(str(config["target_bucket"]), report_file)
            if exported_objects
            else None
        )

        completed_entry = {
            "report_id": report_id,
            "report_type": "BQ_PRINT",
            "start_date": start_date,
            "end_date": end_date,
            "requested_at": requested_at,
            "updated_at": now_iso(),
            "status": "Completed",
            "success": True,
            "csv_object_name": report_file,
            "download_object_name": report_file,
            "download_url": download_url,
            "report_file": report_file,
            "report_files": exported_objects,
            "error": None,
        }
        upsert_status_entry(
            storage_client=storage_client,
            bucket_name=str(config["target_bucket"]),
            status_object_name=str(config["status_object_name"]),
            entry=completed_entry,
            history_limit=int(config["status_history_limit"]),
        )

        return json_response(
            {
                "status": "SUCCESS",
                "report_id": report_id,
                "start_date": start_date,
                "end_date": end_date,
                "report_file": report_file,
                "report_files": exported_objects,
                "download_url": completed_entry["download_url"],
                "status_object": str(config["status_object_name"]),
            },
            200,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_in_bq execution failed: %s", exc)
        failed_entry = {
            "report_id": report_id,
            "report_type": "BQ_PRINT",
            "start_date": start_date,
            "end_date": end_date,
            "requested_at": requested_at,
            "updated_at": now_iso(),
            "status": "Failed",
            "success": False,
            "csv_object_name": None,
            "download_object_name": None,
            "download_url": None,
            "report_file": None,
            "error": str(exc),
        }
        upsert_status_entry(
            storage_client=storage_client,
            bucket_name=str(config["target_bucket"]),
            status_object_name=str(config["status_object_name"]),
            entry=failed_entry,
            history_limit=int(config["status_history_limit"]),
        )
        return json_response(
            {
                "status": "FAILED",
                "report_id": report_id,
                "start_date": start_date,
                "end_date": end_date,
                "error": str(exc),
            },
            500,
        )


def _handle_get_status(request):
    """Return all status rows or one status row by report_id."""
    config = load_config()
    if "error" in config:
        return json_response(config, 500)

    report_id = str(request.args.get("report_id", "")).strip()
    storage_client = storage.Client(project=str(config["project_id"]))
    history = load_status_history(
        storage_client=storage_client,
        bucket_name=str(config["target_bucket"]),
        status_object_name=str(config["status_object_name"]),
    )

    if report_id:
        for row in history:
            if str(row.get("report_id", "")).strip() == report_id:
                return json_response({"report": row}, 200)
        return json_response({"error": "Report not found."}, 404)

    return json_response({"reports": history}, 200)


def _find_exported_objects(
    storage_client: storage.Client,
    bucket_name: str,
    prefix: str,
) -> list[str]:
    """Return exported CSV object names for a report prefix, sorted by name."""
    blobs = storage_client.list_blobs(bucket_or_name=bucket_name, prefix=prefix)
    names = [blob.name for blob in blobs if blob.name.endswith(".csv")]
    names.sort()
    return names
