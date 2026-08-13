# process_in_bq Cloud Function

This folder contains the standalone BigQuery processing Cloud Function.

This function accepts report requests, executes the full report logic in BigQuery SQL, exports final CSV to GCS, and updates status JSON.

## Entry Point

- Function name: process_report_request
- File: main.py

## Request Format

HTTP POST JSON body:

```json
{
  "start_date": "2026-07-01",
  "end_date": "2026-07-03"
}
```

The payload must include:

- start_date
- end_date

## Required Environment Variables

- GOOGLE_CLOUD_PROJECT (or PROJECT_ID)
- BQ_DATASET
- TARGET_BUCKET

## Optional Environment Variables

- BQ_PRINT_TABLE (default: print_fact)
- BQ_EV_TABLE (default: ev_fact)
- BQ_CONTRACT_TABLE (default: contact_fact)
- BQ_MAPPING_PPL_TABLE (default: mapping_ppl_caption_bu)
- BQ_MAPPING_PUBLICATION_TABLE (default: mapping_publications)
- TARGET_REPORTS_PREFIX (default: reports/generated)
- TARGET_STATUS_OBJECT (default: reports/report_history.json)
- STATUS_HISTORY_LIMIT (default: 100)
- BQ_LOCATION (default: US)
- EV_SOURCE_FILTER (default: Natural)
- CONTRACT_SOURCE_FILTER (default: Natural)

## Deploy Example

From repository root:

```bash
gcloud functions deploy process-in-bq \
  --gen2 \
  --runtime python312 \
  --region us-central1 \
  --source process_in_bq \
  --entry-point process_report_request \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=balu-c,BQ_DATASET=<dataset>,BQ_PRINT_TABLE=print_fact,BQ_EV_TABLE=ev_fact,BQ_CONTRACT_TABLE=contact_fact,BQ_MAPPING_PPL_TABLE=mapping_ppl_caption_bu,BQ_MAPPING_PUBLICATION_TABLE=mapping_publications,TARGET_BUCKET=reports-baluc,TARGET_REPORTS_PREFIX=reports/generated,TARGET_STATUS_OBJECT=reports/report_history.json
```

## Deploy Using Python Script

This repository also includes a deployment helper script.

1. Update values in `deploy.env`.
2. Run:

```bash
python deployment.py --env-file deploy.env
```

Optional dry run:

```bash
python deployment.py --env-file deploy.env --dry-run
```

## Response

On success, this function returns status SUCCESS, report_id, and generated report_file path.

On failure, this function returns status FAILED with error details.
