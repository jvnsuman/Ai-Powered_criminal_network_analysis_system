# Architecture — SIH26189

## 7-stage pipeline

1. **Data ingestion layer** — multi-source adapters (FIR text, CDR, financial, social, intel)
2. **NLP entity extraction** — people, phones, locations, orgs, vehicles
3. **Entity resolution** — merge aliases, scripts, partial matches (hardest problem)
4. **Graph construction** — NetworkX, typed nodes and edges
5. **Graph analytics** — centrality, community detection, anomaly detection
6. **Explainability layer** — every flag traces to source evidence
7. **Investigator dashboard** — interactive graph UI with drill-down

Cross-cutting: synthetic data generator (feeds stage 1), ethics guardrails
(feeds stage 5).

## Scope boundary

This is **network analysis of known/already-open cases**, not predictive
policing. The system flags network *positions* (high centrality, bridging
roles) within an already-opened investigation's known entity set — it does
not score individuals outside an active case. Every flag traces back to
source evidence; the investigator makes the final call, not the algorithm.

## Entity schema

- **Person** — central entity, links to Phone (calls), Location (present-at),
  Vehicle (owns)
- **Event** — timestamped call/meeting/transaction connecting multiple
  entities in time; links to Organization (associated-with)
- All entities and events trace back to raw source records (FIRs, CDRs,
  financial records, surveillance, social media, criminal history, intel
  reports) — this traceability is what makes explainability (stage 6)
  possible.

## Tech stack

| Layer | Stack |
|---|---|
| NLP/ML | spaCy, HuggingFace Transformers, IndicNER (verify model license before use) |
| Entity resolution | RapidFuzz (thin, name/alias fuzzy match) → scikit-learn (deepened, multi-signal confidence scoring) |
| Graph | NetworkX (preferred — see LICENSE notes on Neo4j GPLv3 conflict) |
| Backend/API | Flask or FastAPI, PostgreSQL/SQLite for evidence-trail records |
| Frontend | React, Cytoscape.js or D3.js, Tailwind CSS |

See `THIRD_PARTY_NOTICES.md` for the full dependency license audit.
