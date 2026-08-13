"""Environment configuration loading and validation."""

from __future__ import annotations

import os

from constants import DEFAULT_BQ_LOCATION
from constants import DEFAULT_REPORTS_PREFIX
from constants import DEFAULT_STATUS_OBJECT
from validators import is_safe_bucket
from validators import is_safe_identifier
from validators import is_safe_object_name


ConfigValue = str | int
ConfigMap = dict[str, ConfigValue]


def load_config() -> ConfigMap:
    """Load and validate all env vars for standalone process_in_bq execution."""
    project_id = (
        os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        or os.getenv("PROJECT_ID", "").strip()
        or os.getenv("GCP_PROJECT", "").strip()
    )
    bq_dataset = os.getenv("BQ_DATASET", "").strip()

    print_table = os.getenv("BQ_PRINT_TABLE", "print_fact").strip()
    ev_table = os.getenv("BQ_EV_TABLE", "ev_fact").strip()
    contract_table = os.getenv("BQ_CONTRACT_TABLE", "contact_fact").strip()
    mapping_ppl_table = os.getenv("BQ_MAPPING_PPL_TABLE", "mapping_ppl_caption_bu").strip()
    mapping_publication_table = os.getenv("BQ_MAPPING_PUBLICATION_TABLE", "mapping_publications").strip()

    target_bucket = os.getenv("TARGET_BUCKET", "").strip()
    target_reports_prefix = os.getenv("TARGET_REPORTS_PREFIX", DEFAULT_REPORTS_PREFIX).strip().strip("/")
    status_object_name = os.getenv("TARGET_STATUS_OBJECT", DEFAULT_STATUS_OBJECT).strip()

    if not project_id:
        return {"error": "Missing GOOGLE_CLOUD_PROJECT or PROJECT_ID."}
    if not bq_dataset:
        return {"error": "Missing BQ_DATASET."}
    if not target_bucket:
        return {"error": "Missing TARGET_BUCKET."}

    identifier_values = [
        bq_dataset,
        print_table,
        ev_table,
        contract_table,
        mapping_ppl_table,
        mapping_publication_table,
        os.getenv("PRINT_DATE_COLUMN", "finalschdt").strip(),
        os.getenv("PRINT_CAPTION_COLUMN", "caption").strip(),
        os.getenv("PRINT_PUB_NAME_COLUMN", "pub_name").strip(),
        os.getenv("PRINT_STATE_COLUMN", "state").strip(),
        os.getenv("EV_DATE_COLUMN", "event_date").strip(),
        os.getenv("EV_PPL_COLUMN", "ppl").strip(),
        os.getenv("EV_STATE_COLUMN", "state").strip(),
        os.getenv("EV_ZONE_COLUMN", "zone").strip(),
        os.getenv("EV_SOURCE_COLUMN", "source").strip(),
        os.getenv("EV_METRIC_COLUMN", "gf_opportunity_created").strip(),
        os.getenv("CONTRACT_DATE_COLUMN", "event_date").strip(),
        os.getenv("CONTRACT_PPL_COLUMN", "ppl").strip(),
        os.getenv("CONTRACT_STATE_COLUMN", "state").strip(),
        os.getenv("CONTRACT_ZONE_COLUMN", "zone").strip(),
        os.getenv("CONTRACT_SOURCE_COLUMN", "source").strip(),
        os.getenv("CONTRACT_METRIC_COLUMN", "gf_opportunity_created").strip(),
        os.getenv("MAPPING_PPL_COLUMN", "ppl").strip(),
        os.getenv("MAPPING_CAPTION_COLUMN", "caption").strip(),
        os.getenv("MAPPING_BU_COLUMN", "bu").strip(),
        os.getenv("PUBLICATION_MAP_PUB_NAME_COLUMN", "pub_name").strip(),
        os.getenv("PUBLICATION_MAP_PUBLICATION_COLUMN", "publication").strip(),
    ]
    for value in identifier_values:
        if not is_safe_identifier(value):
            return {"error": f"Invalid SQL identifier: {value}"}

    if not is_safe_bucket(target_bucket):
        return {"error": "TARGET_BUCKET has unsupported characters."}
    if target_reports_prefix and not is_safe_object_name(target_reports_prefix):
        return {"error": "TARGET_REPORTS_PREFIX has unsupported characters."}
    if not is_safe_object_name(status_object_name):
        return {"error": "TARGET_STATUS_OBJECT has unsupported characters."}

    status_history_limit = 100
    try:
        status_history_limit = max(1, min(1000, int(os.getenv("STATUS_HISTORY_LIMIT", "100").strip())))
    except ValueError:
        pass

    return {
        "project_id": project_id,
        "bq_dataset": bq_dataset,
        "print_table": print_table,
        "ev_table": ev_table,
        "contract_table": contract_table,
        "mapping_ppl_table": mapping_ppl_table,
        "mapping_publication_table": mapping_publication_table,
        "target_bucket": target_bucket,
        "target_reports_prefix": target_reports_prefix or DEFAULT_REPORTS_PREFIX,
        "status_object_name": status_object_name or DEFAULT_STATUS_OBJECT,
        "status_history_limit": status_history_limit,
        "bq_location": os.getenv("BQ_LOCATION", DEFAULT_BQ_LOCATION).strip() or DEFAULT_BQ_LOCATION,
        "ev_source_filter": os.getenv("EV_SOURCE_FILTER", "Natural").strip(),
        "contract_source_filter": os.getenv("CONTRACT_SOURCE_FILTER", "Natural").strip(),
        "print_date_column": os.getenv("PRINT_DATE_COLUMN", "finalschdt").strip(),
        "print_caption_column": os.getenv("PRINT_CAPTION_COLUMN", "caption").strip(),
        "print_pub_name_column": os.getenv("PRINT_PUB_NAME_COLUMN", "pub_name").strip(),
        "print_state_column": os.getenv("PRINT_STATE_COLUMN", "state").strip(),
        "ev_date_column": os.getenv("EV_DATE_COLUMN", "event_date").strip(),
        "ev_ppl_column": os.getenv("EV_PPL_COLUMN", "ppl").strip(),
        "ev_state_column": os.getenv("EV_STATE_COLUMN", "state").strip(),
        "ev_zone_column": os.getenv("EV_ZONE_COLUMN", "zone").strip(),
        "ev_source_column": os.getenv("EV_SOURCE_COLUMN", "source").strip(),
        "ev_metric_column": os.getenv("EV_METRIC_COLUMN", "gf_opportunity_created").strip(),
        "contract_date_column": os.getenv("CONTRACT_DATE_COLUMN", "event_date").strip(),
        "contract_ppl_column": os.getenv("CONTRACT_PPL_COLUMN", "ppl").strip(),
        "contract_state_column": os.getenv("CONTRACT_STATE_COLUMN", "state").strip(),
        "contract_zone_column": os.getenv("CONTRACT_ZONE_COLUMN", "zone").strip(),
        "contract_source_column": os.getenv("CONTRACT_SOURCE_COLUMN", "source").strip(),
        "contract_metric_column": os.getenv("CONTRACT_METRIC_COLUMN", "gf_opportunity_created").strip(),
        "mapping_ppl_column": os.getenv("MAPPING_PPL_COLUMN", "ppl").strip(),
        "mapping_caption_column": os.getenv("MAPPING_CAPTION_COLUMN", "caption").strip(),
        "mapping_bu_column": os.getenv("MAPPING_BU_COLUMN", "bu").strip(),
        "publication_map_pub_name_column": os.getenv("PUBLICATION_MAP_PUB_NAME_COLUMN", "pub_name").strip(),
        "publication_map_publication_column": os.getenv("PUBLICATION_MAP_PUBLICATION_COLUMN", "publication").strip(),
    }
