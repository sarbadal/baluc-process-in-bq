EXPORT DATA OPTIONS (
  uri='{output_gcs_uri}',
  format='CSV',
  overwrite=true,
  header=true,
  field_delimiter=','
) AS
WITH
stage_mapping_ppl_caption_bu AS (
  SELECT DISTINCT
    CAST({mapping_ppl_column} AS STRING) AS ppl,
    CAST({mapping_caption_column} AS STRING) AS caption,
    CAST({mapping_bu_column} AS STRING) AS bu
  FROM {fq_mapping_ppl}
),
stage_mapping_publication AS (
  SELECT DISTINCT
    CAST({publication_map_pub_name_column} AS STRING) AS pub_name,
    CAST({publication_map_publication_column} AS STRING) AS publication
  FROM {fq_mapping_publication}
),
stage_print_base AS (
  SELECT
    CAST(p.{print_caption_column} AS STRING) AS caption,
    CAST(p.{print_pub_name_column} AS STRING) AS pub_name,
    CAST(p.{print_state_column} AS STRING) AS state,
    DATE(p.{print_date_column}) AS finalschdt
  FROM {fq_print} p
  WHERE DATE(p.{print_date_column}) BETWEEN @start_date AND @end_date
),
stage_print_enriched AS (
  SELECT
    mpc.bu,
    spb.caption,
    mpc.ppl,
    spb.state,
    mp.publication,
    spb.pub_name,
    spb.finalschdt
  FROM stage_print_base spb
  LEFT JOIN stage_mapping_ppl_caption_bu mpc
    ON spb.caption = mpc.caption
  LEFT JOIN stage_mapping_publication mp
    ON spb.pub_name = mp.pub_name
),
stage_print_grouped AS (
  SELECT
    bu,
    caption,
    ppl,
    state,
    publication,
    pub_name,
    finalschdt,
    COUNT(1) AS row_count
  FROM stage_print_enriched
  GROUP BY 1, 2, 3, 4, 5, 6, 7
),
stage_print_windows AS (
  SELECT
    bu,
    caption,
    ppl,
    state,
    publication,
    pub_name,
    finalschdt,
    DATE_SUB(finalschdt, INTERVAL 2 DAY) AS date_m2,
    DATE_SUB(finalschdt, INTERVAL 1 DAY) AS date_m1,
    finalschdt AS date_t,
    DATE_ADD(finalschdt, INTERVAL 1 DAY) AS date_p1,
    DATE_ADD(finalschdt, INTERVAL 2 DAY) AS date_p2
  FROM stage_print_grouped
),
stage_ev_filtered AS (
  SELECT
    CAST(e.{ev_ppl_column} AS STRING) AS ppl,
    CAST(e.{ev_state_column} AS STRING) AS state,
    CAST(e.{ev_zone_column} AS STRING) AS zone,
    DATE(e.{ev_date_column}) AS event_date,
    SAFE_CAST(e.{ev_metric_column} AS FLOAT64) AS gf_opportunity_created
  FROM {fq_ev} e
  WHERE DATE(e.{ev_date_column}) BETWEEN DATE_SUB(@start_date, INTERVAL 2 DAY) AND DATE_ADD(@end_date, INTERVAL 2 DAY)
    AND (@ev_source_filter = '' OR LOWER(CAST(e.{ev_source_column} AS STRING)) = LOWER(@ev_source_filter))
),
stage_contract_filtered AS (
  SELECT
    CAST(c.{contract_ppl_column} AS STRING) AS ppl,
    CAST(c.{contract_state_column} AS STRING) AS state,
    CAST(c.{contract_zone_column} AS STRING) AS zone,
    DATE(c.{contract_date_column}) AS event_date,
    SAFE_CAST(c.{contract_metric_column} AS FLOAT64) AS gf_opportunity_created
  FROM {fq_contract} c
  WHERE DATE(c.{contract_date_column}) BETWEEN DATE_SUB(@start_date, INTERVAL 2 DAY) AND DATE_ADD(@end_date, INTERVAL 2 DAY)
    AND (@contract_source_filter = '' OR LOWER(CAST(c.{contract_source_column} AS STRING)) = LOWER(@contract_source_filter))
),
stage_ev_grouped AS (
  SELECT
    mpc.bu,
    mpc.caption,
    sef.state,
    sef.zone,
    sef.event_date,
    SUM(sef.gf_opportunity_created) AS total_gf_opportunity_created
  FROM stage_ev_filtered sef
  LEFT JOIN stage_mapping_ppl_caption_bu mpc
    ON sef.ppl = mpc.ppl
  GROUP BY 1, 2, 3, 4, 5
),
stage_contract_grouped AS (
  SELECT
    mpc.bu,
    mpc.caption,
    scf.state,
    scf.zone,
    scf.event_date,
    SUM(scf.gf_opportunity_created) AS total_gf_opportunity_created
  FROM stage_contract_filtered scf
  LEFT JOIN stage_mapping_ppl_caption_bu mpc
    ON scf.ppl = mpc.ppl
  GROUP BY 1, 2, 3, 4, 5
),
stage_final_report AS (
  SELECT
    p.bu,
    p.caption,
    p.state,
    p.publication,
    p.pub_name,
    p.finalschdt AS date,
    ev_m2.total_gf_opportunity_created AS ev_enquery_count_date_m2,
    ev_m1.total_gf_opportunity_created AS ev_enquery_count_date_m1,
    ev_t.total_gf_opportunity_created AS ev_enquery_count_date_t,
    ev_p1.total_gf_opportunity_created AS ev_enquery_count_date_p1,
    ev_p2.total_gf_opportunity_created AS ev_enquery_count_date_p2,
    pv_m2.total_gf_opportunity_created AS pv_enquery_count_date_m2,
    pv_m1.total_gf_opportunity_created AS pv_enquery_count_date_m1,
    pv_t.total_gf_opportunity_created AS pv_enquery_count_date_t,
    pv_p1.total_gf_opportunity_created AS pv_enquery_count_date_p1,
    pv_p2.total_gf_opportunity_created AS pv_enquery_count_date_p2
  FROM stage_print_windows p
  LEFT JOIN stage_ev_grouped ev_m2
    ON p.bu = ev_m2.bu AND p.caption = ev_m2.caption AND p.state = ev_m2.state AND p.date_m2 = ev_m2.event_date
  LEFT JOIN stage_ev_grouped ev_m1
    ON p.bu = ev_m1.bu AND p.caption = ev_m1.caption AND p.state = ev_m1.state AND p.date_m1 = ev_m1.event_date
  LEFT JOIN stage_ev_grouped ev_t
    ON p.bu = ev_t.bu AND p.caption = ev_t.caption AND p.state = ev_t.state AND p.date_t = ev_t.event_date
  LEFT JOIN stage_ev_grouped ev_p1
    ON p.bu = ev_p1.bu AND p.caption = ev_p1.caption AND p.state = ev_p1.state AND p.date_p1 = ev_p1.event_date
  LEFT JOIN stage_ev_grouped ev_p2
    ON p.bu = ev_p2.bu AND p.caption = ev_p2.caption AND p.state = ev_p2.state AND p.date_p2 = ev_p2.event_date
  LEFT JOIN stage_contract_grouped pv_m2
    ON p.bu = pv_m2.bu AND p.caption = pv_m2.caption AND p.state = pv_m2.state AND p.date_m2 = pv_m2.event_date
  LEFT JOIN stage_contract_grouped pv_m1
    ON p.bu = pv_m1.bu AND p.caption = pv_m1.caption AND p.state = pv_m1.state AND p.date_m1 = pv_m1.event_date
  LEFT JOIN stage_contract_grouped pv_t
    ON p.bu = pv_t.bu AND p.caption = pv_t.caption AND p.state = pv_t.state AND p.date_t = pv_t.event_date
  LEFT JOIN stage_contract_grouped pv_p1
    ON p.bu = pv_p1.bu AND p.caption = pv_p1.caption AND p.state = pv_p1.state AND p.date_p1 = pv_p1.event_date
  LEFT JOIN stage_contract_grouped pv_p2
    ON p.bu = pv_p2.bu AND p.caption = pv_p2.caption AND p.state = pv_p2.state AND p.date_p2 = pv_p2.event_date
)
SELECT *
FROM stage_final_report
ORDER BY date, bu, caption, state, publication, pub_name
