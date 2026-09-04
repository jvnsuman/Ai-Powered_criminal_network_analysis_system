"""
schema/user.py

System-level User model — who logs in and uses the dashboard.

CRITICAL: this must stay completely separate from schema.entities.Entity
(EntityType.PERSON). Mixing "who's using the software" with "who's a
suspect in a case" is both a data-integrity bug and a serious privacy
problem. See project notes Section 13.

Status: [TODO] — Dec P1, not started
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Role(str, Enum):
    INVESTIGATOR = "investigator"  # view + edit own assigned cases, full dashboard access
    ANALYST = "analyst"            # cross-case read-only, no edit rights
    ADMIN = "admin"                 # manage accounts, view audit logs


@dataclass
class User:
    id: str
    name: str
    badge_id: str
    agency: str
    role: Role
    password_hash: Optional[str] = None  # or SSO token if integrating with agency identity system
    last_login: Optional[str] = None


def login(credentials: dict) -> Optional[User]:
    """[TODO] Authenticate a user and return the User object, or None."""
    raise NotImplementedError


def authorize(user: User, required_role: Role) -> bool:
    """[TODO] Check whether a user's role permits an action."""
    raise NotImplementedError


def get_user_cases(user: User) -> list:
    """[TODO] Return the list of case IDs this user can access, scoped by role."""
    raise NotImplementedError
