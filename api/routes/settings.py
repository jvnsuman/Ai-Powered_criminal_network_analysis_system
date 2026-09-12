"""
api/routes/settings.py

Per-user preferences backing the Settings page's toggles (dark mode,
email alerts, auto-refresh graph, ...). Stored as a JSON blob on
UserORM.preferences (see db.repository.update_user_preferences) rather
than one column per toggle, so the frontend can add new preference
keys without a schema migration.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db import repository as repo
from db.connection import get_db
from schema.user import User

router = APIRouter()


@router.get("/")
def get_settings_endpoint(user: User = Depends(get_current_user)) -> dict:
    """Return the current user's stored preferences."""
    return {"preferences": user.preferences}


@router.put("/")
def update_settings_endpoint(
    data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Merge the given key/value pairs into the current user's stored
    preferences (a partial update — keys not included are left
    unchanged, so toggling one preference never clobbers the others).
    """
    updated = repo.update_user_preferences(db, user.id, data)
    return {"preferences": updated.preferences}
