# AI-Powered Criminal Network Analysis System

**Smart India Hackathon — Problem Statement SIH26189**
**Org/Dept:** Ministry of Home Affairs — NCRB, Women Safety Division
**Theme:** Blockchain & Cybersecurity | **Category:** Software

A system that ingests fragmented, unstructured law-enforcement data (FIRs,
CDRs, financial records, surveillance, social media, criminal history,
intel reports), extracts entities, builds a relationship graph, identifies
key influencers, detects suspicious patterns, and gives investigators an
interactive dashboard to drill from a flagged pattern down to the exact
source evidence behind it.

> **Scope boundary:** this is network analysis of **known, already-open
> cases** — not predictive policing. The system flags network *positions*
> (high centrality, bridging roles) within a case's existing entity set; it
> does not score individuals outside an active investigation. Every flag
> traces back to source evidence, and the investigator makes the final
> call, not the algorithm. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
> for the full reasoning.

---

## Table of contents

- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
  - [Option A — Docker](#option-a--docker-simplest)
  - [Option B — Local development](#option-b--local-development)
- [Roles & permissions](#roles--permissions)
- [API surface](#api-surface)
- [Testing](#testing)
- [Current implementation status](#current-implementation-status)
- [Known limitations](#known-limitations)
- [Security](#security)
- [License](#license)

---

## Architecture

A 7-stage pipeline, with two cross-cutting concerns:

1. **Data ingestion** — multi-source adapters (FIR text, CDR, financial, social, intel)
2. **NLP entity extraction** — people, phones, locations, organizations, vehicles
3. **Entity resolution** — merge aliases, scripts, and partial matches across documents
4. **Graph construction** — typed nodes and edges (NetworkX)
5. **Graph analytics** — centrality, community detection, anomaly detection
6. **Explainability** — every flag traces back to the source document(s) behind it
7. **Investigator dashboard** — interactive graph UI with drill-down

*Cross-cutting:* a synthetic data generator feeds stage 1 for development/demo
purposes without touching real case data; ethics guardrails (no individual
risk-scoring, no predictive-policing framing) constrain stage 5.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the entity schema
(Person / Phone / Location / Vehicle / Organization / Event) and how
traceability back to raw source records is preserved end to end.

## Tech stack

| Layer | Stack |
|---|---|
| NLP entity extraction | spaCy (`en_core_web_sm`) |
| Entity resolution | RapidFuzz (fuzzy name/alias matching); scikit-learn planned for multi-signal confidence scoring |
| Relation classification | HuggingFace Transformers (`facebook/bart-large-mnli` zero-shot) |
| Graph | NetworkX — chosen over Neo4j deliberately (Neo4j Community is GPLv3, incompatible with this project's Apache 2.0 + permissive-license stack; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)) |
| Backend / API | FastAPI, SQLAlchemy, PostgreSQL (SQLite supported for tests), Alembic migrations |
| Frontend | React + Vite, Cytoscape.js (graph rendering) |
| Synthetic data | Faker |
| Testing | pytest, httpx (FastAPI `TestClient`) |

## Project structure

```
schema/          Domain models - Entity/Relationship types, Case, User/Role, SourceDocument, Report
nlp/             extraction.py (spaCy) -> resolution.py (RapidFuzz) -> relation_classification.py (zero-shot)
graph/           build.py (NetworkX construction + centrality), analytics.py (anomaly detection),
                 explainability.py (evidence-trail store)
db/              models.py (SQLAlchemy ORM), repository.py (all persistence/query functions), connection.py
alembic/         Database migrations
api/             FastAPI app (main.py, auth.py) + routes/ (cases, ingestion, query, evidence, alerts,
                 reports, settings)
dashboard/       React + Vite frontend (sidebar-nav layout: Sidebar, TopBar, GraphCanvas, EvidencePanel,
                 IngestionForm, AlertsFeed, MetricStrip, NetworkOverview, per-role pages)
data/            generate_synthetic.py - synthetic FIR/CDR/financial record generator for dev & demos
scripts/         seed_data.py (demo agencies/users/case), populate_demo_case.py (ingest synthetic
                 documents into a real case so the dashboard has something to show)
tests/           pytest suite - schema, NLP pipeline, graph pipeline, API routes, auth, persistence
docs/            ARCHITECTURE.md
```

## Getting started

### Option A — Docker (simplest)

```bash
docker compose up --build
```

This starts PostgreSQL (`5432`), the FastAPI backend (`8000`), and the
dashboard, served via nginx (`4173`, which also reverse-proxies `/api` to
the backend — see `dashboard/nginx.conf`).

### Option B — Local development

**Backend:**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# copy .env.example to .env and adjust DATABASE_URL if not using the
# default local PostgreSQL instance (postgresql://cna_user:cna_password@localhost:5432/cna)

python -m scripts.seed_data              # demo agencies + one user per role + one case
python -m scripts.populate_demo_case     # optional: ingest synthetic documents into a demo case

uvicorn api.main:app --reload            # http://localhost:8000
```

**Frontend:**
```bash
cd dashboard
npm install
npm run dev                              # http://localhost:5173, proxies /api to :8000
```

## Roles & permissions

Four roles (`schema/user.py`), enforced both in the UI (route-level
gating) and — authoritatively — in the API (`api/auth.require_role` /
per-endpoint authorization checks):

| Role | Scope |
|---|---|
| **Investigator** | View + edit own assigned cases; full dashboard access for those cases |
| **Analyst** | Cross-case, read-only view for pattern spotting — scoped to their own agency, no edit rights |
| **Admin** | Manage user accounts and view audit logs — scoped to their own agency |
| **Super Admin** | Everything Admin can do, across **every** agency |

The system's `User` entity (who logs into the software) is kept
architecturally and physically separate from the `Person` entity in the
criminal-network graph (who's a suspect in a case) — mixing the two would
be both a data-integrity bug and a serious privacy problem.

## API surface

All routes except `/health` and `/auth/login` require a bearer session
token (`api/auth.py`).

| Route | Purpose |
|---|---|
| `POST /auth/login`, `POST /auth/logout` | Session auth |
| `POST /cases/`, `GET /cases/` | Create/list cases, agency-scoped |
| `POST /ingest/{case_id}` | Ingest a document, extract entities, classify relations, persist |
| `GET /query/{case_id}` | Build and return that case's graph (nodes/edges/stats) |
| `GET /evidence/{entity_id}` | Evidence trail (source documents) behind a flagged entity |
| `GET /alerts/{case_id}` | Run anomaly detection against the case's real graph |
| `GET /reports/{case_id}`, `POST /reports/{case_id}` | Generate/retrieve Markdown or CSV case reports |
| `GET /settings/`, `PUT /settings/` | Per-user dashboard preferences |

## Testing

```bash
pytest tests/ -v
```

87 tests covering schema validation, the NLP pipeline (extraction ->
resolution -> relation classification), the graph pipeline (build ->
centrality -> anomaly detection), and full API integration tests (auth,
cases, ingestion -> query -> alerts end to end, reports, settings).

**Currently 2 known-failing tests** (`test_nlp_pipeline.py`), caused by a
spaCy model-version behavior difference on organization-entity detection —
not a regression from any application code, and not blocking use of the
pipeline. Tracked as follow-up work.

## Current implementation status

| Stage | Status |
|---|---|
| Entity extraction (spaCy) | Working |
| Entity resolution (RapidFuzz) | Working (thin — fuzzy string match only; multi-signal confidence scoring via scikit-learn not yet implemented) |
| Relation classification (zero-shot) | Working (confidence threshold tuned to 0.3 based on real score distributions — see `nlp/relation_classification.py`) |
| Graph construction & centrality | Working |
| Anomaly detection | Partial — the graph-structural (hub-and-spoke) check runs against real case data; the financial-structuring and communication-burst checks need structured document fields (amounts/timestamps) that real ingested documents don't carry yet, so they currently only fire against synthetic/demo data |
| Explainability / evidence trail | Store exists and is queryable (`graph/explainability.py`), but nothing in the pipeline calls `link_evidence` automatically yet — expect empty results until that's wired in |
| Entity/relationship persistence | Working — ingestion writes to the database; query and alerts read real, case-scoped data instead of a permanent placeholder response |
| Auth, roles, case scoping | Working, enforced at the API layer |
| Reports (Markdown/CSV) | Working. No PDF export (would need an added rendering dependency) |
| Dashboard | Sidebar-nav layout with live graph, evidence panel, ingestion form, alerts feed, and per-role pages, wired to the real API (falls back to bundled sample data only when a case has nothing ingested yet) |

## Known limitations

- Anomaly detection's financial/communication checks are effectively
  demo-only today (see table above) — they need a structured-fields layer
  on top of `SourceDocument.raw_text` to work against real data.
- No audit log yet for Admin/Super Admin actions, despite the role
  documentation referencing one — see [`SECURITY.md`](SECURITY.md).
- No rate limiting on `/auth/login`.
- Session/user data durability depends entirely on the configured
  database; no encryption-at-rest is configured.
- IndicNER / multilingual NER model licensing has not been finalized —
  verify before using any specific pretrained checkpoint in production
  (see `requirements.txt`'s notes on `nlp/extraction.py`'s optional
  HuggingFace pass).

## Security

This system is designed to handle real law-enforcement case data. See
[`SECURITY.md`](SECURITY.md) for the reporting process, current security
scope, and known limitations. **Never commit real case data, credentials,
or `.env` files** — `.gitignore` excludes `.env` by default; double-check
before pushing if you've been experimenting locally.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Chosen over MIT for its
explicit patent grant, given the plausible path to real ministry
deployment or a startup spinoff. Per official SIH rules, project IP stays
with the team; the sponsoring ministry retains free lifetime access. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the full
dependency license audit (Neo4j Community Edition is deliberately
excluded — GPLv3 conflicts with this permissive-licensed stack).
