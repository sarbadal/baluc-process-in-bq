"""Build BigQuery SQL scripts for report generation."""

from __future__ import annotations

from pathlib import Path


SQL_TEMPLATE_PATH = Path(__file__).with_name("sql").joinpath("report_export.sql")
SQL_TEMPLATE = SQL_TEMPLATE_PATH.read_text(encoding="utf-8")


def build_bq_sql_script(config: dict[str, str | int], output_gcs_uri: str) -> str:
    """Build a parameterized BigQuery SQL script for report export.

    Uses configured table names and column mappings to render the SQL template
    that computes report metrics and exports the result to Cloud Storage.

    Args:
        config: Runtime configuration containing project, dataset, table, and
            column identifier settings used by the SQL template.
        output_gcs_uri: Destination GCS URI pattern used by BigQuery EXPORT DATA.

    Returns:
        Fully rendered SQL script ready to run with BigQuery query parameters.
    """
    project_id = str(config["project_id"])
    dataset = str(config["bq_dataset"])

    print_table = str(config["print_table"])
    ev_table = str(config["ev_table"])
    contract_table = str(config["contract_table"])
    mapping_ppl_table = str(config["mapping_ppl_table"])
    mapping_publication_table = str(config["mapping_publication_table"])

    print_date_column = str(config["print_date_column"])
    print_caption_column = str(config["print_caption_column"])
    print_pub_name_column = str(config["print_pub_name_column"])
    print_state_column = str(config["print_state_column"])

    ev_date_column = str(config["ev_date_column"])
    ev_ppl_column = str(config["ev_ppl_column"])
    ev_state_column = str(config["ev_state_column"])
    ev_zone_column = str(config["ev_zone_column"])
    ev_source_column = str(config["ev_source_column"])
    ev_metric_column = str(config["ev_metric_column"])

    contract_date_column = str(config["contract_date_column"])
    contract_ppl_column = str(config["contract_ppl_column"])
    contract_state_column = str(config["contract_state_column"])
    contract_zone_column = str(config["contract_zone_column"])
    contract_source_column = str(config["contract_source_column"])
    contract_metric_column = str(config["contract_metric_column"])

    mapping_ppl_column = str(config["mapping_ppl_column"])
    mapping_caption_column = str(config["mapping_caption_column"])
    mapping_bu_column = str(config["mapping_bu_column"])

    publication_map_pub_name_column = str(config["publication_map_pub_name_column"])
    publication_map_publication_column = str(config["publication_map_publication_column"])

    fq_print = f"`{project_id}.{dataset}.{print_table}`"
    fq_ev = f"`{project_id}.{dataset}.{ev_table}`"
    fq_contract = f"`{project_id}.{dataset}.{contract_table}`"
    fq_mapping_ppl = f"`{project_id}.{dataset}.{mapping_ppl_table}`"
    fq_mapping_publication = f"`{project_id}.{dataset}.{mapping_publication_table}`"

    query = SQL_TEMPLATE.format(
        output_gcs_uri=output_gcs_uri,
        mapping_ppl_column=mapping_ppl_column,
        mapping_caption_column=mapping_caption_column,
        mapping_bu_column=mapping_bu_column,
        publication_map_pub_name_column=publication_map_pub_name_column,
        publication_map_publication_column=publication_map_publication_column,
        print_caption_column=print_caption_column,
        print_pub_name_column=print_pub_name_column,
        print_state_column=print_state_column,
        print_date_column=print_date_column,
        ev_ppl_column=ev_ppl_column,
        ev_state_column=ev_state_column,
        ev_zone_column=ev_zone_column,
        ev_date_column=ev_date_column,
        ev_metric_column=ev_metric_column,
        ev_source_column=ev_source_column,
        contract_ppl_column=contract_ppl_column,
        contract_state_column=contract_state_column,
        contract_zone_column=contract_zone_column,
        contract_date_column=contract_date_column,
        contract_metric_column=contract_metric_column,
        contract_source_column=contract_source_column,
        fq_mapping_ppl=fq_mapping_ppl,
        fq_mapping_publication=fq_mapping_publication,
        fq_print=fq_print,
        fq_ev=fq_ev,
        fq_contract=fq_contract,
    ).strip()
    print(query)
    return query
