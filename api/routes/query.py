"""
api/routes/query.py

Retrieve a case's graph for the dashboard.

Authorization/case-scoping (via db.repository.get_cases_for_user) is
fully enforced here. graph.build itself is now real and working (see
graph/build.py) — what's still missing is a persisted store of
entities/relationships to build FROM: api/routes/ingestion.py runs
extraction but doesn't yet write EntityORM/RelationshipORM rows (see
that module's own docstring). So an authorized request still honestly
reports 501, but the reason is "nothing persisted to build a graph
from yet," not "graph.build doesn't exist."
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db import repository as repo
from db.connection import get_db
from schema.user import User

router = APIRouter()


@router.get("/{case_id}")
def query_endpoint(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Return the graph for a case. Checks the user is authorized to
    view this case (403 if not), then reports 501 since there's no
    persisted entity/relationship store to build a graph from yet.
    """
    authorized_case_ids = {c.id for c in repo.get_cases_for_user(db, user)}
    if case_id not in authorized_case_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this case",
        )

    # Integration point once entity/relationship persistence exists:
    # fetch this case's stored entities/relationships and hand them to
    # graph.build.build_graph(...).
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Authorized, but this case has no persisted entities/relationships "
            "to build a graph from yet (see api/routes/ingestion.py)."
        ),
    )
