"""
api/main.py

FastAPI application entrypoint. Wires together auth (api/auth.py) and
the route modules (api/routes/) into one app.

Adds the alerts router (api/routes/alerts.py) for the sidebar-nav
dashboard's Recent Alerts panel, and the reports/settings routers
(api/routes/reports.py, api/routes/settings.py) for the Reports and
Settings pages — everything else unchanged.

Run locally with: uvicorn api.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api import auth
from api.routes import alerts, cases, evidence, ingestion, query, reports
from api.routes import settings as settings_routes
from config import get_settings
from db.connection import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the app starts up: creates any missing database
    tables so a fresh deployment doesn't need a separate manual
    migration step for the initial schema.
    """
    init_db()
    yield


def create_app() -> FastAPI:
    """App factory — instantiate the FastAPI app, configure CORS for
    the dashboard dev server, and register every route.
    """
    app = FastAPI(title="SIH26189 Criminal Network Analysis API", lifespan=lifespan)
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        """Liveness check — used by orchestration/monitoring, not auth-gated."""
        return {"status": "ok"}

    @app.post("/auth/login", tags=["auth"])
    def login(credentials: dict, db: Session = Depends(get_db)) -> dict:
        return auth.login_endpoint(credentials, db)

    @app.post("/auth/logout", tags=["auth"])
    def logout(token: str) -> dict:
        auth.logout_endpoint(token)
        return {"status": "logged_out"}

    app.include_router(cases.router, prefix="/cases", tags=["cases"])
    app.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
    app.include_router(query.router, prefix="/query", tags=["query"])
    app.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
    app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
    app.include_router(reports.router, prefix="/reports", tags=["reports"])
    app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])

    return app


app = create_app()
