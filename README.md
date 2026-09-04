# AI-Powered Criminal Network Analysis System — SIH26189

**Problem Statement ID:** 26189 — AI-Powered Criminal Network Analysis System
**Organization:** Ministry of Home Affairs
**Department:** National Crime Records Bureau (NCRB), Women Safety Division
**Theme:** Blockchain & Cybersecurity | **Category:** Software

Developed for Smart India Hackathon 2026. See `SIH26189_Project_Notes.md`
(maintained in the team's Claude Project) for the full canonical planning
document — problem understanding, architecture, priority tiers, roadmap,
and decision log.

## Philosophy: build once, extend forward

This codebase is **not** rebuilt between rounds. What ships for the
September idea-submission demo is a real, thin slice of the same pipeline
that gets deepened for the December 36-hour final round. There is one
file structure, one schema, one growing dataset — no separate "Sep version"
and "Dec version" of anything.

Every function below carries a status tag directly in its docstring:
- `[TODO]` — not started
- `[IN PROGRESS]` — partially working
- `[DONE]` — complete and tested

Update the tag in the file itself as work lands, and mirror the change in
the project notes' roadmap table (Section 10) and Changelog.

## Structure

```
sih26189-criminal-network/
├── LICENSE                    # Apache License 2.0
├── THIRD_PARTY_NOTICES.md     # dependency license audit
├── requirements.txt
├── data/                      # synthetic FIRs, CDRs, financial records
├── schema/
│   ├── entities.py             # Person, Location, Vehicle, Phone, Organization, Event
│   └── user.py                 # User model — kept separate from Person entity
├── nlp/
│   ├── extraction.py          # NER pipeline
│   ├── resolution.py          # entity resolution / deduplication
│   └── confidence.py          # scoring & manual-review flags
├── graph/
│   ├── build.py                # graph construction (NetworkX)
│   ├── analytics.py            # centrality, community detection, anomalies
│   └── explainability.py       # evidence-trail linkage
├── api/
│   ├── main.py                 # Flask/FastAPI app
│   ├── auth.py                  # login/role authorization
│   └── routes/                  # ingestion, query, evidence endpoints
├── dashboard/                  # React app — Cytoscape.js graph UI
├── tests/
└── docs/
    └── ARCHITECTURE.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate       # or venv\Scripts\activate on Windows
pip install -r requirements.txt --break-system-packages
```

## Data

All FIR, CDR, financial, and criminal-history records in `data/` are
**entirely synthetic and fictional**. No real personal data, real case
data, or real individuals are represented.
