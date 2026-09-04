"""
api/main.py

Flask/FastAPI application entrypoint. Wires together the ingestion,
query, and evidence routes (api/routes/) plus auth (api/auth.py).

Status: [TODO] — Dec P1, not started. Sep slice runs pipeline modules
directly via scripts/notebooks; this HTTP layer is what turns that into
a servable backend for the dashboard.
"""

# from fastapi import FastAPI
# from api.routes import ingestion, query, evidence
# from api import auth

# app = FastAPI(title="SIH26189 Criminal Network Analysis API")

# app.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
# app.include_router(query.router, prefix="/query", tags=["query"])
# app.include_router(evidence.router, prefix="/evidence", tags=["evidence"])


def create_app():
    """[TODO] App factory — instantiate and configure the Flask/FastAPI
    app, register routes, wire up DB connection for evidence-trail
    storage (PostgreSQL or SQLite per project notes Section 10).
    """
    raise NotImplementedError
