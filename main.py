"""Cloud Function entrypoint for BigQuery-native report generation."""

from report_service import process_report_request as _process_report_request


def process_report_request(request):
	"""Cloud Function HTTP entrypoint."""
	return _process_report_request(request)


__all__ = ["process_report_request"]
