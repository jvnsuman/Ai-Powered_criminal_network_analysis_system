# AI-Powered Criminal Network Analysis System — SIH26189

**Problem Statement ID:** 26189 — AI-Powered Criminal Network Analysis System
**Organization:** Ministry of Home Affairs
**Department:** National Crime Records Bureau (NCRB), Women Safety Division
**Theme:** Blockchain & Cybersecurity | **Category:** Software

## Structure

```
sih26189-criminal-network/
├── LICENSE                    # Apache License 2.0
├── THIRD_PARTY_NOTICES.md     # dependency license audit
├── SECURITY.md
├── requirements.txt
├── config.py                  # settings (env-driven)
├── .env.example
├── data/                      # synthetic FIRs, CDRs, financial records
├── schema/
│   ├── entities.py            # Person, Location, Vehicle, Phone, Organization, Event
│   ├── user.py                # User/Role/Agency — kept separate from Person entity
│   └── case.py                # Case model
├── db/
│   ├── connection.py          # SQLAlchemy engine/session (SQLite by default, Postgres-ready)
│   ├── models.py              # ORM models
│   └── repository.py          # domain-dataclass <-> ORM adapter
├── nlp/
│   ├── extraction.py               # NER pipeline (spaCy, real & working)
│   ├── resolution.py               # entity resolution / deduplication
│   ├── relation_classification.py  # relation + risk classification (HuggingFace, optional)
│   └── confidence.py               # scoring & manual-review flags
├── graph/
│   ├── build.py                 # graph construction (NetworkX)
│   ├── analytics.py              # centrality, community detection, anomalies
│   └── explainability.py         # evidence-trail linkage
├── api/
│   ├── main.py                 # FastAPI app
│   ├── auth.py                 # login/role authorization
│   └── routes/                 # cases, ingestion, query, evidence endpoints
├── dashboard/                  # React app — Cytoscape.js graph UI
├── scripts/
│   └── seed_data.py            # demo agencies/users/case
├── tests/
└── docs/
    └── ARCHITECTURE.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate       # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # required for nlp/extraction.py
cp .env.example .env
python -m scripts.seed_data     # creates demo agencies/users/case
uvicorn api.main:app --reload   # http://localhost:8000
```

Optional — relation classification and risk flagging
(`nlp/relation_classification.py`) additionally needs `transformers`
and `torch`, commented out in `requirements.txt` by default since
they're a heavy install:

```bash
pip install transformers torch
```

In a second terminal:

```bash
cd dashboard
npm install
npm run dev                     # http://localhost:5173
```

Demo logins (printed by `seed_data.py`): investigator / analyst /
admin / super_admin, each with their own badge ID and password.

## Tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker compose up --build
```

Runs the API on port 8000 and the dashboard on port 4173.

## Data

All FIR, CDR, financial, and criminal-history records in `data/` are
**entirely synthetic and fictional**. No real personal data, real case
data, or real individuals are represented.
