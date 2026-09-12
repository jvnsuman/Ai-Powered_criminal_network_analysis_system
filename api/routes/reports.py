"""
api/routes/reports.py

Generate and retrieve case reports (a Markdown case summary or a CSV
export of per-document-type ingestion counts). Reports are built on
demand from whatever is actually persisted for a case right now —
case metadata (db.repository.get_case) and per-document-type
ingestion counts (db.repository.get_document_summary_for_case) — then
stored so the Reports page can list and re-download them without
regenerating.

There's no PDF export: that would need an extra rendering dependency
(e.g. reportlab/weasyprint) not currently in requirements.txt.
Markdown and CSV cover the same underlying data with the stdlib alone.
"""

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db import repository as repo
from db.connection import get_db
from schema.case import Case
from schema.report import VALID_REPORT_FORMATS, Report
from schema.user import User

router = APIRouter()


def _check_case_access(db: Session, case_id: str, user: User) -> Case:
    """Shared authorization + existence check, same pattern as
    api/routes/query.py: 403 if the user can't see this case at all,
    404 if it doesn't exist.
    """
    authorized_case_ids = {c.id for c in repo.get_cases_for_user(db, user)}
    if case_id not in authorized_case_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this case")
    case = repo.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def _build_markdown(case: Case, sources: list[dict]) -> str:
    """A short, real Markdown summary — case metadata plus whatever
    document ingestion counts actually exist. No entity/relationship
    section: those aren't persisted yet (see api/routes/ingestion.py),
    so a report can't honestly claim findings about them.
    """
    lines = [
        f"# Case Summary — {case.title}",
        "",
        f"- Case ID: {case.id}",
        f"- Status: {case.status.value}",
        f"- Opened: {case.opened_at}",
        "",
        "## Ingested sources",
        "",
    ]
    if not sources:
        lines.append("No documents ingested for this case yet.")
    else:
        lines.append("| Document type | Count | Last updated |")
        lines.append("|---|---|---|")
        for s in sources:
            lines.append(f"| {s['document_type']} | {s['count']} | {s['last_updated']} |")
    return "\n".join(lines) + "\n"


def _build_csv(sources: list[dict]) -> str:
    """The same per-document-type counts as _build_markdown, as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["document_type", "count", "last_updated"])
    for s in sources:
        writer.writerow([s["document_type"], s["count"], s["last_updated"]])
    return buf.getvalue()


@router.post("/{case_id}/generate", status_code=status.HTTP_201_CREATED)
def generate_report_endpoint(
    case_id: str, data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Generate a new report for a case and persist it.
    Body: {"format": "markdown" | "csv"}.
    """
    case = _check_case_access(db, case_id, user)
    fmt = data.get("format", "markdown")
    if fmt not in VALID_REPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"format must be one of {sorted(VALID_REPORT_FORMATS)}"
        )

    sources = repo.get_document_summary_for_case(db, case_id)
    content = _build_markdown(case, sources) if fmt == "markdown" else _build_csv(sources)

    report = Report(id=str(uuid.uuid4()), case_id=case_id, title=f"Case summary — {case.title}", format=fmt, content=content)
    created = repo.create_report(db, report)
    return created.to_dict()


@router.get("/{case_id}")
def list_reports_endpoint(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """List previously generated reports for a case (metadata only — no content)."""
    _check_case_access(db, case_id, user)
    reports = repo.list_reports_for_case(db, case_id)
    return {"reports": [r.to_dict() for r in reports]}


@router.get("/{case_id}/{report_id}/download")
def download_report_endpoint(
    case_id: str, report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    """Return a report's raw content with a Content-Disposition
    header so the browser downloads it as a file.
    """
    _check_case_access(db, case_id, user)
    report = repo.get_report(db, report_id)
    if report is None or report.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    media_type = "text/markdown" if report.format == "markdown" else "text/csv"
    extension = "md" if report.format == "markdown" else "csv"
    return Response(
        content=report.content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.id}.{extension}"'},
    )
