"""
api/routes/cases.py

Case creation, listing, and investigator assignment. Every route here
enforces agency scoping: an ADMIN can only manage cases and assign
investigators within their own agency; only a SUPER_ADMIN can act
across agencies. See schema.user.Role for the full role hierarchy.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user, require_role
from db import repository as repo
from db.connection import get_db
from schema.case import Case
from schema.user import Role, User

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_case(data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Create a new case, defaulting to the creator's own agency. Only
    a SUPER_ADMIN may create a case for a different agency. The
    creator is automatically assigned as an investigator on the case.
    """
    title = data.get("title")
    if not title or not str(title).strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required")

    agency_id = data.get("agency_id", user.agency_id)
    if agency_id != user.agency_id and user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a super admin can create a case for another agency",
        )

    case = Case(id=str(uuid.uuid4()), title=title, agency_id=agency_id, created_by_user_id=user.id)
    created = repo.create_case(db, case)
    repo.assign_investigator(db, created.id, user.id)

    return created.to_dict()


@router.get("/")
def list_cases(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """List every case this user is authorized to see (role/agency
    scoped — see db.repository.get_cases_for_user).
    """
    cases = repo.get_cases_for_user(db, user)
    return {"cases": [c.to_dict() for c in cases]}


@router.get("/{case_id}")
def get_case_endpoint(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Fetch a single case by ID, if the user is authorized to see it."""
    if case_id not in {c.id for c in repo.get_cases_for_user(db, user)}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this case")
    case = repo.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case.to_dict()


@router.post("/{case_id}/assign")
def assign_investigator_endpoint(
    case_id: str, data: dict, user: User = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db)
) -> dict:
    """Assign an investigator (by user_id) to a case. Requires ADMIN
    or SUPER_ADMIN. An ADMIN may only manage cases in their own
    agency; SUPER_ADMIN can act across agencies.
    """
    case = repo.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if case.agency_id != user.agency_id and user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage cases within your own agency",
        )

    investigator_id = data.get("user_id")
    if not investigator_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    updated = repo.assign_investigator(db, case_id, investigator_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case or user not found")

    return updated.to_dict()
