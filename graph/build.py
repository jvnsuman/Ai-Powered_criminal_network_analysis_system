"""
graph/build.py

Stage 4 of the pipeline: graph construction. Consumes
nlp.resolution.ResolvedEntity (canonical, deduplicated entities) and
nlp.relation_classification.ClassifiedRelation (relationships between
entities), and assembles them into one queryable graph. Everything
downstream (centrality/influencer detection, the investigator
dashboard) reads from the graph this module produces, not from either
upstream module's raw output directly.

Critical ID-mapping issue this module resolves (not optional plumbing
if extending it): ClassifiedRelation's entity_a_id/entity_b_id are raw
nlp.extraction.ExtractedEntity.id values — per-MENTION IDs, one per
occurrence in one document — NOT ResolvedEntity.id values (canonical,
deduplicated IDs). Building the graph straight from ClassifiedRelation
without translating IDs first would produce one graph node per raw
mention instead of per real-world entity (e.g. "Raju Kumar" and
"Raju S." would sit as two disconnected nodes even where resolution
correctly merged them). This module always translates through
nlp.resolution.build_mention_to_resolved_map before adding an edge —
see build_graph()'s implementation.

Library choice: NetworkX MultiDiGraph, not Graph or DiGraph. A plain
nx.Graph silently overwrites a second edge added between the same two
nodes (e.g. a "calls" edge between A and B, then a "transacts-with"
edge between the same A and B, leaves only the second — the first is
gone with no error). This project's entity schema allows exactly that:
two entities can have more than one relationship type between them. A
MultiDiGraph keeps every distinct edge. Direction matters too — "calls,"
"owns," and "transacts-with" aren't symmetric (A owns B doesn't imply B
owns A), so an undirected Graph would misrepresent the schema itself.

Status tags used throughout:
    [DONE]         - implemented and expected to work for the demo
    [IN PROGRESS]  - partially implemented, has a real body but needs work
    [TODO]         - stub only, raises NotImplementedError, future scope
"""

from __future__ import annotations

from typing import Optional

try:
    import networkx as nx
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "networkx is required for graph/build.py. Install with:\n"
        "    pip install networkx --break-system-packages\n"
        "(see requirements.txt — networkx>=3.3,<4.0. Neo4j is deliberately "
        "excluded — see requirements.txt's license-conflict note.)"
    ) from exc

from nlp.resolution import ResolvedEntity, build_mention_to_resolved_map
from nlp.relation_classification import ClassifiedRelation, RelationType


def build_graph(resolved_entities: list,
                 relations: list) -> "nx.MultiDiGraph":
    """Construct a NetworkX MultiDiGraph from resolved entities and
    classified relations.

    Node keys are ResolvedEntity.id (canonical IDs, never raw mention
    IDs). Every node carries the attributes the explainability layer
    needs to trace it back to source: entity_type, canonical_text,
    mention_ids, and source_doc_ids.

    Every edge is added via add_relation_edge (not inline here), which
    performs the mention-ID -> resolved-ID translation described in
    this module's docstring. RelationType.UNRELATED relations are
    skipped.

    Args:
        resolved_entities: output of nlp.resolution.resolve_entities.
        relations: output of
            nlp.relation_classification.classify_all_relations (or any
            list of ClassifiedRelation built the same way) — can span
            multiple documents, as long as every entity_a_id/
            entity_b_id it references is a mention_id present in
            resolved_entities' mention_ids.

    Returns:
        A populated nx.MultiDiGraph. Nodes for every resolved entity
        are always added, even ones with zero relations — an isolated
        entity is still a real finding worth surfacing, not something
        to silently drop.
    """
    graph = nx.MultiDiGraph()

    for entity in resolved_entities:
        graph.add_node(
            entity.id,
            entity_type=entity.entity_type.value,
            canonical_text=entity.canonical_text,
            mention_ids=list(entity.mention_ids),
            source_doc_ids=sorted(entity.source_doc_ids),
            is_low_confidence_cross_merge=entity.is_low_confidence_cross_merge,
        )

    mention_to_resolved = build_mention_to_resolved_map(resolved_entities)

    for relation in relations:
        add_relation_edge(graph, relation, mention_to_resolved)

    return graph


def add_relation_edge(graph: "nx.MultiDiGraph", relation: ClassifiedRelation,
                       mention_to_resolved: dict) -> Optional[str]:
    """Add one ClassifiedRelation to graph as a directed edge between
    the RESOLVED entities its two mention IDs belong to.

    This is where the mention-ID -> resolved-ID translation described
    in this module's docstring actually happens.

    Skips (returns None, doesn't raise) in three cases — each expected/
    recoverable during real batch processing, not a reason to halt:
        1. relation.relation_type is UNRELATED — meaningful during
           development/debugging, but not a graph edge.
        2. Either entity ID isn't in mention_to_resolved — the relation
           references a mention resolution.py never saw (a real
           integration bug if it happens, but every other valid
           relation should still get added).
        3. The edge would be a self-loop (both mention IDs resolve to
           the same entity) — can legitimately happen when two mentions
           resolution merged together are also the pair a relation was
           classified between.

    Args:
        graph: the MultiDiGraph to mutate.
        relation: the ClassifiedRelation to add.
        mention_to_resolved: output of
            nlp.resolution.build_mention_to_resolved_map.

    Returns:
        The edge key (as assigned by nx.MultiDiGraph.add_edge) if an
        edge was added, or None if skipped for one of the reasons above.
    """
    if relation.relation_type == RelationType.UNRELATED:
        return None

    resolved_a = mention_to_resolved.get(relation.entity_a_id)
    resolved_b = mention_to_resolved.get(relation.entity_b_id)

    if resolved_a is None or resolved_b is None:
        return None

    if resolved_a == resolved_b:
        return None

    edge_key = graph.add_edge(
        resolved_a, resolved_b,
        relation_type=relation.relation_type.value,
        confidence=relation.confidence,
        source_doc_id=relation.source_doc_id,
        source_text=relation.source_text,
    )
    return edge_key


def get_evidence_trail(graph: "nx.MultiDiGraph", node_id: str) -> dict:
    """Retrieve everything needed to explain why a node/its edges
    exist, tracing back to source documents — the explainability
    requirement for this project ("can every flagged key influencer or
    suspicious pattern be traced back to source evidence?").

    A thin read-only query over attributes already stored on the graph
    at build time (mention_ids, source_doc_ids on nodes; source_doc_id,
    source_text on edges), rather than a separate evidence-tracking
    system — everything needed already lives on the graph by construction.

    Args:
        graph: a graph produced by build_graph.
        node_id: a ResolvedEntity.id present in graph.

    Returns:
        dict with keys:
            node_attributes: the full attribute dict stored on this
                node (entity_type, canonical_text, mention_ids,
                source_doc_ids, is_low_confidence_cross_merge).
            incoming_edges / outgoing_edges: lists of
                {neighbor_id, relation_type, confidence, source_doc_id,
                source_text} for every edge touching this node, split
                by direction since relation_type is directional.

    Raises:
        KeyError: if node_id is not present in graph.
    """
    if node_id not in graph:
        raise KeyError(f"Node {node_id!r} not found in graph")

    outgoing_edges = [
        {
            "neighbor_id": target,
            "relation_type": data["relation_type"],
            "confidence": data["confidence"],
            "source_doc_id": data["source_doc_id"],
            "source_text": data["source_text"],
        }
        for _, target, data in graph.out_edges(node_id, data=True)
    ]
    incoming_edges = [
        {
            "neighbor_id": source,
            "relation_type": data["relation_type"],
            "confidence": data["confidence"],
            "source_doc_id": data["source_doc_id"],
            "source_text": data["source_text"],
        }
        for source, _, data in graph.in_edges(node_id, data=True)
    ]

    return {
        "node_attributes": dict(graph.nodes[node_id]),
        "outgoing_edges": outgoing_edges,
        "incoming_edges": incoming_edges,
    }


# NetworkX's betweenness_centrality/pagerank don't accept a MultiDiGraph
# directly for every algorithm/version combination, and parallel edges
# (two distinct relation types between the same pair) would double-count
# a connection's structural importance if left in for centrality
# purposes specifically. Both functions below collapse to a plain
# DiGraph first — this only affects the centrality calculation, not the
# graph object itself, which keeps every parallel edge for evidence
# purposes (see get_evidence_trail above).
def _as_simple_digraph(graph: "nx.MultiDiGraph") -> "nx.DiGraph":
    """Collapse a MultiDiGraph to a plain DiGraph (parallel edges
    merged into one) for centrality algorithms that don't operate on
    multigraphs. Node/edge attributes are not preserved on the
    collapsed view — only used internally for structural centrality math.
    """
    simple = nx.DiGraph()
    simple.add_nodes_from(graph.nodes())
    simple.add_edges_from(graph.edges())
    return simple


def compute_centrality(graph: "nx.MultiDiGraph", method: str = "betweenness") -> dict:
    """Run a centrality algorithm over the graph.

    Args:
        graph: a graph produced by build_graph.
        method: "betweenness" or "pagerank".

    Returns:
        dict mapping node_id -> centrality score (float).

    Raises:
        ValueError: if method is not one of the supported options.
    """
    simple = _as_simple_digraph(graph)
    if method == "betweenness":
        return nx.betweenness_centrality(simple)
    if method == "pagerank":
        return nx.pagerank(simple)
    raise ValueError(f"Unknown centrality method: {method!r}. Use 'betweenness' or 'pagerank'.")


def highlight_influencer(graph: "nx.MultiDiGraph", method: str = "betweenness") -> Optional[dict]:
    """Identify the single highest-centrality node and attach a stated
    reason — this is what makes the flag explainable rather than a bare
    score with no justification.

    Args:
        graph: a graph produced by build_graph.
        method: which centrality method to rank by (see compute_centrality).

    Returns:
        dict with node_id, score, method, and a human-readable reason,
        or None if the graph has no nodes.
    """
    if graph.number_of_nodes() == 0:
        return None
    scores = compute_centrality(graph, method=method)
    top_node_id = max(scores, key=scores.get)
    return {
        "node_id": top_node_id,
        "score": scores[top_node_id],
        "method": method,
        "reason": f"Highest {method} centrality ({scores[top_node_id]:.3f}) among {graph.number_of_nodes()} entities in this graph.",
    }


def render_graph(graph: "nx.MultiDiGraph", output_path: str = "graph.png") -> str:
    """Render a static image of the graph for offline viewing/demo use.

    This is an interim, non-interactive visualization only. The full
    interactive experience (click/hover/zoom/pan/filter/expand-collapse)
    lives in dashboard/'s GraphCanvas component, not here — this
    function exists for quick local sanity-checking of a graph's shape,
    not as a dashboard substitute.

    Args:
        graph: a graph produced by build_graph.
        output_path: where to save the rendered PNG.

    Returns:
        The output_path, for convenience chaining.

    Raises:
        RuntimeError: if matplotlib is not installed.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        raise RuntimeError(
            "matplotlib is required for render_graph but is not installed. Run:\n"
            "    pip install matplotlib"
        )

    simple = _as_simple_digraph(graph)
    pos = nx.spring_layout(simple, seed=42)
    labels = {n: graph.nodes[n].get("canonical_text", n) for n in graph.nodes()}
    colors = [_ENTITY_TYPE_COLORS.get(graph.nodes[n].get("entity_type"), "#999999") for n in graph.nodes()]

    plt.figure(figsize=(12, 8))
    nx.draw(
        simple, pos, labels=labels, node_color=colors, with_labels=True,
        node_size=800, font_size=8, arrows=True,
    )
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


# Node fill colors by entity_type, for render_graph only.
_ENTITY_TYPE_COLORS = {
    "PERSON": "#4f8ef7",
    "LOCATION": "#f7b84f",
    "VEHICLE": "#8e6de6",
    "PHONE": "#4fd6c0",
    "ORGANIZATION": "#f76b6b",
}


if __name__ == "__main__":
    # Minimal smoke test for the Sep demo — not a substitute for tests/.
    # Chains all four pipeline stages built so far: extraction ->
    # resolution -> relation classification -> graph construction.
    # NOTE: this requires transformers + torch installed for the
    # relation-classification step (nlp.relation_classification) — see
    # that module's docstring. If torch is unavailable, this smoke test
    # cannot run past the classify_all_relations call.
    from nlp.extraction import load_synthetic_fir, extract_entities
    from nlp.resolution import resolve_entities

    doc_a = load_synthetic_fir(
        "Complainant stated that Raju Kumar was seen near MG Road, "
        "contacted from phone number 987-654-3210.",
        doc_id="fir-001",
    )
    doc_b = load_synthetic_fir(
        "A call from 987-654-3210 was traced to the same MG Road area.",
        doc_id="cdr-002",
    )

    all_entities = []
    for doc in (doc_a, doc_b):
        all_entities.extend(extract_entities(doc.raw_text, doc.doc_id))

    resolved = resolve_entities(all_entities)
    print("--- Resolved entities ---")
    for r in resolved:
        print(f"  {r.entity_type.value:12} {r.canonical_text!r:20} "
              f"docs={sorted(r.source_doc_ids)}")

    try:
        from nlp.relation_classification import classify_all_relations
        relations = []
        for doc, doc_entities in (
            (doc_a, [e for e in all_entities if e.source_doc_id == doc_a.doc_id]),
            (doc_b, [e for e in all_entities if e.source_doc_id == doc_b.doc_id]),
        ):
            relations.extend(classify_all_relations(doc_entities, doc.raw_text))

        graph = build_graph(resolved, relations)
        print(f"\n--- Graph: {graph.number_of_nodes()} nodes, "
              f"{graph.number_of_edges()} edges ---")
        for node_id, attrs in graph.nodes(data=True):
            print(f"  [{attrs['entity_type']}] {attrs['canonical_text']!r} "
                  f"(docs={attrs['source_doc_ids']})")
        for u, v, data in graph.edges(data=True):
            print(f"  {u} --[{data['relation_type']}]--> {v} "
                  f"(conf={data['confidence']:.2f})")

    except RuntimeError as e:
        print(f"\n(Skipping relation-classification/graph portion — "
              f"{e})")
        print("Building graph with entities only, no edges, to at least "
              "demonstrate node construction:")
        graph = build_graph(resolved, [])
        print(f"  {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
