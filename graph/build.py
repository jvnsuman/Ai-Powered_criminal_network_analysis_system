"""
graph/build.py

Graph construction from resolved entities and relationships.

Backend: NetworkX (preferred over Neo4j Community Edition — see LICENSE
and THIRD_PARTY_NOTICES.md for the GPLv3 conflict reasoning).

Status: [TODO]
"""

import networkx as nx

from schema.entities import Entity, Relationship


def build_graph(entities: list[Entity], relationships: list[Relationship]) -> nx.Graph:
    """[TODO] Construct a NetworkX graph — nodes from resolved entities,
    edges from relationships. Node/edge attributes should carry
    source_document_id so graph/explainability.py can trace back later.
    """
    raise NotImplementedError


def compute_centrality(graph: nx.Graph, method: str = "betweenness") -> dict:
    """[TODO] Run a centrality algorithm (betweenness or PageRank first —
    library calls via NetworkX, not novel engineering). Returns
    node_id -> centrality_score.
    """
    raise NotImplementedError


def highlight_influencer(graph: nx.Graph, node) -> dict:
    """[TODO] Mark the top-centrality node and attach a stated reason
    (e.g. "highest betweenness centrality") — this is what makes the
    flag explainable rather than a black-box score, per the dashboard
    mockup (project notes Section 12).
    """
    raise NotImplementedError


def render_graph(graph: nx.Graph):
    """[TODO] Basic visualization for the demo video. Interim: static
    render is fine for Sep. Full interactive version (click/hover/zoom/
    pan/filter/expand-collapse) lives in dashboard/, not here — see
    project notes Section 12's interactivity requirement.
    """
    raise NotImplementedError
