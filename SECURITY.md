# Security Policy

This system handles law-enforcement case data (FIRs, CDRs, financial
records, surveillance reports). Treat any suspected vulnerability as
sensitive.

## Reporting a vulnerability

Do not open a public GitHub issue for security problems. Instead,
contact the maintainer directly (see repository owner) with:

- A description of the issue and its potential impact
- Steps to reproduce
- Any relevant logs or payloads (redact real case data)

## Scope

- Authentication/session handling (`api/auth.py`, `schema/user.py`)
- Role/agency-based access control (`schema.user.authorize`,
  `schema.user.get_user_cases`)
- Data validation on ingestion (`schema/entities.py`,
  `api/routes/ingestion.py`)

## Known limitations (current development stage)

- Session tokens and user/agency/case data are stored in-memory by
  default; only the SQLite/PostgreSQL path via `db/` is durable, and
  even that has no encryption-at-rest configured yet.
- No rate limiting on `/auth/login` — brute-force protection is not
  yet implemented.
- No audit log yet for ADMIN/SUPER_ADMIN actions, despite the Role
  documentation referencing "view audit logs".

These are tracked as outstanding work, not accepted risk for a
production deployment.
