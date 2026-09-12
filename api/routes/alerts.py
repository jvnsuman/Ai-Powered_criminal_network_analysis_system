"""
api/routes/alerts.py

Serves the "Recent Alerts" feed shown on the new dashboard home page
(see SIH26189_Project_Notes.md Section 12/17 for the mockup this
implements). This is NOT a separate alerting subsystem — it is a thin
read-only view over graph.analytics.detect_anomalies, which already
exists and is real (tested in tests/test_graph_pipeline.py). No
alert is synthesized or hardcoded here.

Entity/relationship persistence (schema/entities.py's Entity/
Relationship -> EntityORM/RelationshipORM) is now wired up in
ingestion.py, so this runs detect_anomalies against a real,
case-specific graph when one exists.

Known remaining limitation: detect_anomalies's financial-structuring
and communication-burst checks need documents shaped like
data/generate_synthetic.py's SyntheticDocument (.doc_id + .structured
fields) — real ingested documents (schema.entities.SourceDocument)
only carry raw_text, with no structured extraction of amounts/
timestamps. So only the graph-structural hub-and-spoke check runs
against real case data today; the other two only ever fire against
synthetic/demo documents. Passing real SourceDocuments to
detect_anomalies as-is would silently no-op those two checks rather
than error, which is safe but worth knowing if alerts look sparse.

Status: [DONE] — real code path, running for real once a case has
persisted entities. Honest empty-state (not fabricated) when it doesn't.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import graph.build as graph_build
from api.auth import get_current_user
from db import repository as repo
from db.connection import get_db
from graph.analytics import detect_anomalies
from nlp.resolution import resolve_entities
from schema.user import User

router = APIRouter()


# Anomaly-type -> (display title template, severity, hashtag-style tags)
# shown in the alert feed. Keeps api/routes/alerts.py decoupled from
# graph.analytics's internal finding "type" strings changing shape.
_ALERT_PRESENTATION = {
    "hub_and_spoke": {
        "title": "High Risk Connection Detected",
        "severity": "high",
        "tags": ["#HighRisk", "#Association"],
    },
    "financial_structuring": {
        "title": "Suspicious Transaction",
        "severity": "medium",
        "tags": ["#Financial", "#Suspicious"],
    },
    "communication_burst": {
        "title": "Communication Burst Identified",
        "severity": "medium",
        "tags": ["#Phone", "#Pattern"],
    },
}


@router.get("/{case_id}")
def list_alerts(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Return real anomaly-detection findings for a case, presented as
    alert-feed entries. Requires the same case authorization as
    api/routes/query.py — an alert feed is still case data.
    """
    authorized_case_ids = {c.id for c in repo.get_cases_for_user(db, user)}
    if case_id not in authorized_case_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view alerts for this case",
        )

    mentions = repo.get_entities_for_case(db, case_id)
    if mentions:
        resolved_entities = resolve_entities(mentions)
        relations = repo.get_relationships_for_case(db, case_id)
        graph = graph_build.build_graph(resolved_entities, relations)
        # No structured documents passed (see module docstring) — only
        # the graph-structural hub-and-spoke check runs against real data.
        findings = detect_anomalies(graph)
    else:
        findings = []

    alerts = []
    now = datetime.now(timezone.utc).isoformat()
    for finding in findings:
        presentation = _ALERT_PRESENTATION.get(
            finding["type"],
            {"title": finding["type"].replace("_", " ").title(), "severity": "medium", "tags": []},
        )
        alerts.append({
            "id": f"alert-{finding.get('doc_id') or finding.get('node_id')}-{finding['type']}",
            "title": presentation["title"],
            "detail": finding["detail"],
            "severity": presentation["severity"],
            "tags": presentation["tags"],
            "timestamp": now,
        })

    return {"case_id": case_id, "alerts": alerts}
