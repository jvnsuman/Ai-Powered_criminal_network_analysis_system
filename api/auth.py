"""
api/auth.py

HTTP-layer authentication/authorization. Wraps schema.user's login/
authorize functions with request/session handling for the API.

Keep this separate from schema/user.py: schema/user.py defines *what*
a User and Role are; this file defines *how* the API checks them on
each request (headers, tokens, session cookies).

Status: [TODO] — Dec P1, not started.
"""

from schema.user import User, Role, login as schema_login, authorize as schema_authorize


def login_endpoint(credentials: dict):
    """[TODO] HTTP handler wrapping schema.user.login — validates
    request body, calls schema_login, returns a session token or error.
    """
    raise NotImplementedError


def require_role(required_role: Role):
    """[TODO] Decorator/dependency for route handlers — checks the
    requesting user's role via schema_authorize before allowing access.
    Used to scope Investigator (own cases) vs Analyst (cross-case,
    read-only) vs Admin (account management) access per project notes
    Section 13.
    """
    raise NotImplementedError
