"""
graph/analytics.py

Deeper graph analytics, built on top of graph/build.py's core
centrality (compute_centrality). These extend the same graph object —
no separate analytics pipeline.

Scope note on detect_anomalies: the graph object alone (nodes/edges
from resolved entities and classified relations) doesn't carry raw
transaction amounts or call timestamps — that data lives in each
source document's `structured` field (see
data/generate_synthetic.py's SyntheticDocument), never embedded into
graph attributes by graph.build.build_graph. So detect_anomalies takes
the graph AND the original source documents: the graph-structural
check (hub-and-spoke degree) uses the graph alone; the financial-
structuring and communication-burst checks scan the raw documents
directly, independent of the graph.

Status: implemented, not yet tuned against any labelled/real dataset —
thresholds below are reasonable starting points, not validated cutoffs.
"""

from typing import Optional

import networkx as nx

from graph.build import compute_centrality


def compute_community_detection(graph: "nx.MultiDiGraph") -> dict:
    """Run Louvain community detection to surface clusters that may
    represent sub-networks (e.g. a trafficking recruitment cell) within
    a larger graph.

    Args:
        graph: a graph produced by graph.build.build_graph.

    Returns:
        dict mapping node_id -> community_id (an integer, stable only
        within this one call — re-running may assign different integers
        to the same community due to Louvain's randomized tie-breaking).
    """
    undirected = nx.Graph()
    undirected.add_nodes_from(graph.nodes())
    undirected.add_edges_from(graph.edges())

    communities = nx.algorithms.community.louvain_communities(undirected, seed=42)
    return {
        node_id: community_index
        for community_index, community in enumerate(communities)
        for node_id in community
    }


def compute_full_centrality_suite(graph: "nx.MultiDiGraph") -> dict:
    """Compute betweenness, PageRank, and eigenvector centrality
    together, for callers that want the full picture rather than one
    method at a time via graph.build.compute_centrality.

    Args:
        graph: a graph produced by graph.build.build_graph.

    Returns:
        dict mapping node_id -> {"betweenness": float, "pagerank": float,
        "eigenvector": float}. Eigenvector centrality is 0.0 for every
        node if the algorithm fails to converge (e.g. on a
        disconnected or very small graph) — this is a documented
        NetworkX behavior, not a bug, so it's caught and defaulted
        rather than raising.
    """
    betweenness = compute_centrality(graph, method="betweenness")
    pagerank = compute_centrality(graph, method="pagerank")

    simple = nx.DiGraph()
    simple.add_nodes_from(graph.nodes())
    simple.add_edges_from(graph.edges())
    try:
        eigenvector = nx.eigenvector_centrality(simple, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        eigenvector = {node_id: 0.0 for node_id in graph.nodes()}

    return {
        node_id: {
            "betweenness": betweenness.get(node_id, 0.0),
            "pagerank": pagerank.get(node_id, 0.0),
            "eigenvector": eigenvector.get(node_id, 0.0),
        }
        for node_id in graph.nodes()
    }


# Hub-and-spoke detection: a node whose degree exceeds the graph's
# average by this many standard deviations is flagged as a potential
# recruitment/coordination hub. Not tuned against any labelled data.
_HUB_DEGREE_STDEV_THRESHOLD = 2.0
_MIN_NODES_FOR_HUB_DETECTION = 4

# Financial structuring: transactions repeatedly falling within this
# fraction of a threshold are flagged (mirrors
# data/generate_synthetic.py's generate_synthetic_financial_record
# structuring_pattern shape, detected independently rather than
# trusting that flag).
_STRUCTURING_THRESHOLD = 50_000
_STRUCTURING_LOWER_BOUND_FRACTION = 0.8
_STRUCTURING_MIN_COUNT = 3

# Communication burst: this many-or-more calls between the same pair
# within this window are flagged (mirrors generate_synthetic_cdr's
# burst=True shape).
_BURST_WINDOW_MINUTES = 15
_BURST_MIN_CALLS = 3


def _detect_hub_and_spoke(graph: "nx.MultiDiGraph") -> list[dict]:
    """Graph-structural check: nodes with unusually high degree
    relative to the rest of the graph.
    """
    if graph.number_of_nodes() < _MIN_NODES_FOR_HUB_DETECTION:
        return []

    degrees = dict(graph.degree())
    values = list(degrees.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    stdev = variance ** 0.5
    if stdev == 0:
        return []

    threshold = mean + _HUB_DEGREE_STDEV_THRESHOLD * stdev
    return [
        {
            "type": "hub_and_spoke",
            "node_id": node_id,
            "degree": degree,
            "graph_mean_degree": round(mean, 2),
            "detail": f"Degree {degree} is {_HUB_DEGREE_STDEV_THRESHOLD}+ standard deviations above the graph average ({mean:.2f}).",
        }
        for node_id, degree in degrees.items()
        if degree > threshold
    ]


def _detect_financial_structuring(documents: list) -> list[dict]:
    """Scan raw financial-record documents for several transactions
    clustered just under _STRUCTURING_THRESHOLD.
    """
    findings = []
    for doc in documents:
        transactions = getattr(doc, "structured", {}).get("transactions")
        if not transactions:
            continue

        lower_bound = _STRUCTURING_THRESHOLD * _STRUCTURING_LOWER_BOUND_FRACTION
        suspicious = [
            t for t in transactions
            if lower_bound <= t.get("amount", 0) < _STRUCTURING_THRESHOLD
        ]
        if len(suspicious) >= _STRUCTURING_MIN_COUNT:
            findings.append({
                "type": "financial_structuring",
                "doc_id": getattr(doc, "doc_id", None),
                "matching_transaction_count": len(suspicious),
                "detail": (
                    f"{len(suspicious)} transactions between "
                    f"{lower_bound:.0f} and {_STRUCTURING_THRESHOLD} "
                    f"(just under the reporting threshold)."
                ),
            })
    return findings


def _detect_communication_bursts(documents: list) -> list[dict]:
    """Scan raw CDR documents for calls between the same pair
    clustered within _BURST_WINDOW_MINUTES.
    """
    from datetime import datetime, timedelta

    findings = []
    for doc in documents:
        calls = getattr(doc, "structured", {}).get("calls")
        if not calls or len(calls) < _BURST_MIN_CALLS:
            continue

        timestamps = sorted(datetime.fromisoformat(c["timestamp"]) for c in calls)
        window = timedelta(minutes=_BURST_WINDOW_MINUTES)
        if timestamps[-1] - timestamps[0] <= window and len(timestamps) >= _BURST_MIN_CALLS:
            findings.append({
                "type": "communication_burst",
                "doc_id": getattr(doc, "doc_id", None),
                "call_count": len(timestamps),
                "detail": (
                    f"{len(timestamps)} calls within "
                    f"{(timestamps[-1] - timestamps[0]).total_seconds() / 60:.1f} minutes."
                ),
            })
    return findings


def detect_anomalies(graph: "nx.MultiDiGraph", documents: Optional[list] = None) -> list[dict]:
    """Flag suspicious patterns: hub-and-spoke structural outliers
    (from the graph), plus financial-flow structuring and
    communication-burst detection (from the raw source documents, if
    provided — see module docstring for why these can't be detected
    from the graph object alone).

    Args:
        graph: a graph produced by graph.build.build_graph.
        documents: optional list of source documents (e.g.
            data/generate_synthetic.py's SyntheticDocument, or anything
            duck-typed the same way: .doc_id and .structured). If
            omitted, only the graph-structural check runs.

    Returns:
        A list of finding dicts, each with at least a "type" and
        "detail" key. Empty list if nothing was flagged.
    """
    findings = _detect_hub_and_spoke(graph)
    if documents:
        findings.extend(_detect_financial_structuring(documents))
        findings.extend(_detect_communication_bursts(documents))
    return findings
