"""
api/routes/ingestion.py

Accepts multi-source data (FIRs, CDRs, financial records, etc.) via API
and hands it to nlp.extraction for processing.

Status: [TODO] — Dec P1, not started.
"""


def ingest_endpoint(data: dict):
    """[TODO] Accept multi-source data via API, validate against
    schema.entities.SourceDocument shape, queue for extraction.
    """
    raise NotImplementedError
