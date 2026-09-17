EXPORT DATA OPTIONS (
  uri='gs://reports-baluc/reports/generated/report_20260917_131648_20260701_20260717_e0fa5fe9_*.csv', -- GCS URI for the exported CSV file
  format='CSV',
  overwrite=true,
  header=true,
  field_delimiter=','
) AS
WITH
-- Lookup table for mapping people, captions, and business units
-- EV and PV fact tables don't have caption to join with Print fact table
-- This lookup table is needed to map ppl to captions and business units
stage_mapping_ppl_caption_bu AS (
  SELECT DISTINCT
    CAST(ppl AS STRING) AS ppl,
    CAST(caption AS STRING) AS caption,
    CAST(bu AS STRING) AS bu
  FROM `balu-c.reporting_dataset.mapping_ppl_caption_bu`
),
stage_print_base AS (
  SELECT
    CAST(p.caption AS STRING) AS caption,
    CAST(p.pub_name AS STRING) AS pub_name,
    COALESCE(CAST(p.state AS STRING), 'Telangana') AS state, -- Default to 'Telangana' if state is NULL
    DATE(p.finalschdt) AS finalschdt
  FROM `balu-c.reporting_dataset.print` p
  WHERE DATE(p.finalschdt) BETWEEN DATE '2026-08-01' AND DATE '2026-08-31' -- Filter by the specified date range
    AND p.caption IS NOT NULL -- Ensure that the caption is not NULL
),
stage_print_enriched AS (
  SELECT
    mpc.bu,
    spb.caption,
    mpc.ppl,
    spb.state,
    spb.pub_name,
    spb.finalschdt
  FROM stage_print_base spb
  LEFT JOIN stage_mapping_ppl_caption_bu mpc
    ON spb.caption = mpc.caption
),
stage_print_grouped AS (
  SELECT
    bu,
    caption,
    ppl,
    state,
    pub_name,
    finalschdt,
    COUNT(1) AS row_count
  FROM stage_print_enriched
    GROUP BY 1, 2, 3, 4, 5, 6
),
stage_print_windows AS (
  SELECT
    bu,
    caption,
    ppl,
    state,
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
    CAST(e.ppl AS STRING) AS ppl,
    CAST(e.state AS STRING) AS state,
    CAST(e.zone AS STRING) AS zone,
    DATE(e.event_date) AS event_date,
    SAFE_CAST(e.gf_opportunity_created AS FLOAT64) AS gf_opportunity_created
  FROM `balu-c.reporting_dataset.ev` e
  WHERE DATE(e.event_date) BETWEEN DATE '2026-07-30' AND DATE '2026-09-02'
    AND (@ev_source_filter = '' OR LOWER(CAST(e.source AS STRING)) = LOWER(@ev_source_filter))
),
stage_contract_filtered AS (
  SELECT
    CAST(c.ppl AS STRING) AS ppl,
    CAST(c.state AS STRING) AS state,
    CAST(c.zone AS STRING) AS zone,
    DATE(c.event_date) AS event_date,
    SAFE_CAST(c.gf_opportunity_created AS FLOAT64) AS gf_opportunity_created
  FROM `balu-c.reporting_dataset.contact` c
  WHERE DATE(c.event_date) BETWEEN DATE '2026-07-30' AND DATE '2026-09-02'
    AND (@contract_source_filter = '' OR LOWER(CAST(c.source AS STRING)) = LOWER(@contract_source_filter))
),
stage_ev_grouped AS (
  SELECT
    mpc.bu,
    mpc.caption,
    sef.ppl,
    sef.state,
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
    scf.ppl,
    scf.state,
    scf.event_date,
    SUM(scf.gf_opportunity_created) AS total_gf_opportunity_created
  FROM stage_contract_filtered scf
  LEFT JOIN stage_mapping_ppl_caption_bu mpc
    ON scf.ppl = mpc.ppl
  GROUP BY 1, 2, 3, 4, 5
),
stage_ev_contract_combined AS (
  SELECT
    caption,
    state,
    event_date,
    SUM(total_gf_opportunity_created) AS total_gf_opportunity_created
  FROM (
    SELECT caption, state, event_date, total_gf_opportunity_created FROM stage_ev_grouped
    UNION ALL
    SELECT caption, state, event_date, total_gf_opportunity_created FROM stage_contract_grouped
  )
  GROUP BY 1, 2, 3
),
stage_final_report AS (
  SELECT
    '--' AS bu,
    p.caption,
    p.ppl,
    p.state,
    p.pub_name,
    p.finalschdt AS date,
    ev_m2.total_gf_opportunity_created AS ev_enquery_count_date_m2,
    ev_m1.total_gf_opportunity_created AS ev_enquery_count_date_m1,
    ev_t.total_gf_opportunity_created AS ev_enquery_count_date_t,
    ev_p1.total_gf_opportunity_created AS ev_enquery_count_date_p1,
    ev_p2.total_gf_opportunity_created AS ev_enquery_count_date_p2,
    CASE
      WHEN ev_m2.total_gf_opportunity_created IS NULL
        AND ev_m1.total_gf_opportunity_created IS NULL THEN NULL
      ELSE (COALESCE(ev_m2.total_gf_opportunity_created, 0) + COALESCE(ev_m1.total_gf_opportunity_created, 0)) / 2
    END AS ev_perf_enquery_count_date_m2_m1_avg,
    ev_t.total_gf_opportunity_created AS ev_perf_enquery_count_date_t_avg,
    CASE
      WHEN ev_p2.total_gf_opportunity_created IS NULL
        AND ev_p1.total_gf_opportunity_created IS NULL THEN NULL
      ELSE (COALESCE(ev_p2.total_gf_opportunity_created, 0) + COALESCE(ev_p1.total_gf_opportunity_created, 0)) / 2
    END AS ev_perf_enquery_count_date_p2_p1_avg,
    IFNULL(
      SAFE_DIVIDE(
        COALESCE(ev_t.total_gf_opportunity_created, 0),
        CASE
          WHEN ev_m2.total_gf_opportunity_created IS NULL
            AND ev_m1.total_gf_opportunity_created IS NULL THEN NULL
          ELSE (COALESCE(ev_m2.total_gf_opportunity_created, 0) + COALESCE(ev_m1.total_gf_opportunity_created, 0)) / 2
        END
      ) - 1,
      0
    ) AS ev_growth_enquery_count_date_t_vs_m2_avg,
    IFNULL(
      SAFE_DIVIDE(
        CASE
          WHEN ev_p2.total_gf_opportunity_created IS NULL
            AND ev_p1.total_gf_opportunity_created IS NULL THEN NULL
          ELSE (COALESCE(ev_p2.total_gf_opportunity_created, 0) + COALESCE(ev_p1.total_gf_opportunity_created, 0)) / 2
        END,
        COALESCE(ev_t.total_gf_opportunity_created, 0)
      ) - 1,
      0
    ) AS ev_growth_enquery_count_date_p2_vs_t_avg,
    
    pv_m2.total_gf_opportunity_created AS pv_enquery_count_date_m2,
    pv_m1.total_gf_opportunity_created AS pv_enquery_count_date_m1,
    pv_t.total_gf_opportunity_created AS pv_enquery_count_date_t,
    pv_p1.total_gf_opportunity_created AS pv_enquery_count_date_p1,
    pv_p2.total_gf_opportunity_created AS pv_enquery_count_date_p2,
    CASE
      WHEN pv_m2.total_gf_opportunity_created IS NULL
        AND pv_m1.total_gf_opportunity_created IS NULL THEN NULL
      ELSE (COALESCE(pv_m2.total_gf_opportunity_created, 0) + COALESCE(pv_m1.total_gf_opportunity_created, 0)) / 2
    END AS pv_perf_enquery_count_date_m2_m1_avg,
    pv_t.total_gf_opportunity_created AS pv_perf_enquery_count_date_t_avg,
    CASE
      WHEN pv_p2.total_gf_opportunity_created IS NULL
        AND pv_p1.total_gf_opportunity_created IS NULL THEN NULL
      ELSE (COALESCE(pv_p2.total_gf_opportunity_created, 0) + COALESCE(pv_p1.total_gf_opportunity_created, 0)) / 2
    END AS pv_perf_enquery_count_date_p2_p1_avg,
    IFNULL(
      SAFE_DIVIDE(
        COALESCE(pv_t.total_gf_opportunity_created, 0),
        CASE
          WHEN pv_m2.total_gf_opportunity_created IS NULL
            AND pv_m1.total_gf_opportunity_created IS NULL THEN NULL
          ELSE (COALESCE(pv_m2.total_gf_opportunity_created, 0) + COALESCE(pv_m1.total_gf_opportunity_created, 0)) / 2
        END
      ) - 1,
      0
    ) AS pv_growth_enquery_count_date_t_vs_m2_avg,
    IFNULL(
      SAFE_DIVIDE(
        CASE
          WHEN pv_p2.total_gf_opportunity_created IS NULL
            AND pv_p1.total_gf_opportunity_created IS NULL THEN NULL
          ELSE (COALESCE(pv_p2.total_gf_opportunity_created, 0) + COALESCE(pv_p1.total_gf_opportunity_created, 0)) / 2
        END,
        COALESCE(pv_t.total_gf_opportunity_created, 0)
      ) - 1,
      0
    ) AS pv_growth_enquery_count_date_p2_vs_t_avg,

    evc_m2.total_gf_opportunity_created AS evc_enquery_count_date_m2,
    evc_m1.total_gf_opportunity_created AS evc_enquery_count_date_m1,
    evc_t.total_gf_opportunity_created AS evc_enquery_count_date_t,
    evc_p1.total_gf_opportunity_created AS evc_enquery_count_date_p1,
    evc_p2.total_gf_opportunity_created AS evc_enquery_count_date_p2,
    CASE
      WHEN evc_m2.total_gf_opportunity_created IS NULL
        AND evc_m1.total_gf_opportunity_created IS NULL THEN NULL
      ELSE (COALESCE(evc_m2.total_gf_opportunity_created, 0) + COALESCE(evc_m1.total_gf_opportunity_created, 0)) / 2
    END AS evc_perf_enquery_count_date_m2_m1_avg,
    evc_t.total_gf_opportunity_created AS evc_perf_enquery_count_date_t_avg,
    CASE
      WHEN evc_p1.total_gf_opportunity_created IS NULL
        AND evc_p2.total_gf_opportunity_created IS NULL THEN NULL
      ELSE (COALESCE(evc_p1.total_gf_opportunity_created, 0) + COALESCE(evc_p2.total_gf_opportunity_created, 0)) / 2
    END AS evc_perf_enquery_count_date_p2_p1_avg,
    IFNULL(
      SAFE_DIVIDE(
        COALESCE(evc_t.total_gf_opportunity_created, 0),
        CASE
          WHEN evc_m2.total_gf_opportunity_created IS NULL
            AND evc_m1.total_gf_opportunity_created IS NULL THEN NULL
          ELSE (COALESCE(evc_m2.total_gf_opportunity_created, 0) + COALESCE(evc_m1.total_gf_opportunity_created, 0)) / 2
        END
      ) - 1,
      0
    ) AS evc_growth_enquery_count_date_t_vs_m2_avg,
    IFNULL(
      SAFE_DIVIDE(
        CASE
          WHEN evc_p1.total_gf_opportunity_created IS NULL
            AND evc_p2.total_gf_opportunity_created IS NULL THEN NULL
          ELSE (COALESCE(evc_p1.total_gf_opportunity_created, 0) + COALESCE(evc_p2.total_gf_opportunity_created, 0)) / 2
        END,
        COALESCE(evc_t.total_gf_opportunity_created, 0)
      ) - 1,
      0
    ) AS evc_growth_enquery_count_date_p2_vs_t_avg,

  FROM stage_print_windows p
  LEFT JOIN stage_ev_grouped ev_m2
    ON p.caption = ev_m2.caption AND p.state = ev_m2.state AND p.date_m2 = ev_m2.event_date
  LEFT JOIN stage_ev_grouped ev_m1
    ON p.caption = ev_m1.caption AND p.state = ev_m1.state AND p.date_m1 = ev_m1.event_date
  LEFT JOIN stage_ev_grouped ev_t
    ON p.caption = ev_t.caption AND p.state = ev_t.state AND p.date_t = ev_t.event_date
  LEFT JOIN stage_ev_grouped ev_p1
    ON p.caption = ev_p1.caption AND p.state = ev_p1.state AND p.date_p1 = ev_p1.event_date
  LEFT JOIN stage_ev_grouped ev_p2
    ON p.caption = ev_p2.caption AND p.state = ev_p2.state AND p.date_p2 = ev_p2.event_date
  LEFT JOIN stage_contract_grouped pv_m2
    ON p.caption = pv_m2.caption AND p.state = pv_m2.state AND p.date_m2 = pv_m2.event_date
  LEFT JOIN stage_contract_grouped pv_m1
    ON p.caption = pv_m1.caption AND p.state = pv_m1.state AND p.date_m1 = pv_m1.event_date
  LEFT JOIN stage_contract_grouped pv_t
    ON p.caption = pv_t.caption AND p.state = pv_t.state AND p.date_t = pv_t.event_date
  LEFT JOIN stage_contract_grouped pv_p1
    ON p.caption = pv_p1.caption AND p.state = pv_p1.state AND p.date_p1 = pv_p1.event_date
  LEFT JOIN stage_contract_grouped pv_p2
    ON p.caption = pv_p2.caption AND p.state = pv_p2.state AND p.date_p2 = pv_p2.event_date

  LEFT JOIN stage_ev_contract_combined evc_m2
    ON p.caption = evc_m2.caption AND p.state = evc_m2.state AND p.date_m2 = evc_m2.event_date
  LEFT JOIN stage_ev_contract_combined evc_m1
    ON p.caption = evc_m1.caption AND p.state = evc_m1.state AND p.date_m1 = evc_m1.event_date
  LEFT JOIN stage_ev_contract_combined evc_t
    ON p.caption = evc_t.caption AND p.state = evc_t.state AND p.date_t = evc_t.event_date
  LEFT JOIN stage_ev_contract_combined evc_p1
    ON p.caption = evc_p1.caption AND p.state = evc_p1.state AND p.date_p1 = evc_p1.event_date
  LEFT JOIN stage_ev_contract_combined evc_p2
    ON p.caption = evc_p2.caption AND p.state = evc_p2.state AND p.date_p2 = evc_p2.event_date
)
SELECT *
FROM stage_final_report
ORDER BY caption, state, pub_name, date