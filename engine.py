# Call-Graph Weisfeiler-Lehman color refinement engine

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from model import Case, Node


NodeId = str
Color = str
CallCount = int

WeightedEdge = tuple[NodeId, CallCount]
WeightedNeighborColor = tuple[Color, CallCount]

RelationSignature = tuple[
    Color,
    tuple[WeightedNeighborColor, ...],  # OUT multiset
    tuple[WeightedNeighborColor, ...],  # IN multiset
]


@dataclass(frozen=True)
class RelationGraphView:
    """
    Call graph view used by Call-Graph Weisfeiler-Lehman.

    This view is derived only from Axis 1 call edges.
    Self-edges are lifted into self_call_count and excluded from
    outgoing/incoming multisets.
    """
    node_ids: list[NodeId]
    node_by_id: dict[NodeId, Node]

    self_call_count: dict[NodeId, int]

    # Non-self edges only.
    outgoing: dict[NodeId, list[WeightedEdge]]
    incoming: dict[NodeId, list[WeightedEdge]]

    # Number of distinct non-self callees.
    # This is intentionally not total outgoing call count.
    distinct_out_callee_count: dict[NodeId, int]


@dataclass(frozen=True)
class CGWLResult:
    """
    Result of Call-Graph Weisfeiler-Lehman.

    node_color contains colors for all nodes, including anchors.
    cluster_id_by_node and clusters are restricted to scored nodes.
    """
    node_color: dict[NodeId, Color]
    cluster_id_by_node: dict[NodeId, int]
    clusters: list[list[NodeId]]
    rounds: int


def run_cg_wl(case: Case) -> CGWLResult:
    """
    Run Call-Graph Weisfeiler-Lehman.

    v0 policy:
      - Axis 1 only.
      - Directed weighted call graph.
      - Individualized fixed anchors.
      - Seed(user) = (self_call_count, distinct_out_callee_count).
      - Refinement signature = previous color + OUT multiset + IN multiset.
      - OUT/IN multisets aggregate call counts by previous neighbor color.
      - No origin labels, no Axis 2/4, no oracle, no soft merge.
    """
    view = build_relation_graph_view(case)
    colors = make_initial_cg_wl_colors(case, view)

    max_rounds = len(view.node_ids)

    for round_index in range(1, max_rounds + 1):
        new_colors = refine_cg_wl_once(case, view, colors)

        if same_partition(view.node_ids, colors, new_colors):
            clusters = make_scored_clusters(case, new_colors)
            cluster_id_by_node = make_cluster_id_by_node(clusters)

            return CGWLResult(
                node_color=new_colors,
                cluster_id_by_node=cluster_id_by_node,
                clusters=clusters,
                rounds=round_index,
            )

        colors = new_colors

    raise RuntimeError("CG-WL did not reach a fixpoint")


def build_relation_graph_view(case: Case) -> RelationGraphView:
    node_ids = [node.id for node in case.nodes]
    node_by_id = {node.id: node for node in case.nodes}

    self_call_count: dict[NodeId, int] = {
        node.id: 0
        for node in case.nodes
    }
    outgoing: dict[NodeId, list[WeightedEdge]] = {
        node.id: []
        for node in case.nodes
    }
    incoming: dict[NodeId, list[WeightedEdge]] = {
        node.id: []
        for node in case.nodes
    }

    for node in case.nodes:
        src = node.id

        for call in node.calls:
            dst = call.target
            count = call.count

            if src == dst:
                self_call_count[src] += count
                continue

            outgoing[src].append((dst, count))
            incoming[dst].append((src, count))

    distinct_out_callee_count = {
        node_id: len({dst for dst, _count in outgoing[node_id]})
        for node_id in node_ids
    }

    return RelationGraphView(
        node_ids=node_ids,
        node_by_id=node_by_id,
        self_call_count=self_call_count,
        outgoing=outgoing,
        incoming=incoming,
        distinct_out_callee_count=distinct_out_callee_count,
    )


def make_initial_cg_wl_colors(
    case: Case,
    view: RelationGraphView,
) -> dict[NodeId, Color]:
    colors: dict[NodeId, Color] = {}

    for node in case.nodes:
        if node.type == "anchor":
            colors[node.id] = _anchor_color(node.id)
            continue

        self_count = view.self_call_count[node.id]
        out_count = view.distinct_out_callee_count[node.id]

        colors[node.id] = f"USER:self={self_count}:distinct_out={out_count}"

    return colors


def refine_cg_wl_once(
    case: Case,
    view: RelationGraphView,
    prev_colors: dict[NodeId, Color],
) -> dict[NodeId, Color]:
    signatures: dict[NodeId, RelationSignature] = {}

    for node in case.nodes:
        if node.type == "anchor":
            continue

        out_multiset = _neighbor_color_multiset(
            view.outgoing[node.id],
            prev_colors,
        )
        in_multiset = _neighbor_color_multiset(
            view.incoming[node.id],
            prev_colors,
        )

        signatures[node.id] = (
            prev_colors[node.id],
            out_multiset,
            in_multiset,
        )

    signature_to_color = _canonicalize_signatures(signatures)

    new_colors: dict[NodeId, Color] = {}

    for node in case.nodes:
        if node.type == "anchor":
            new_colors[node.id] = _anchor_color(node.id)
        else:
            new_colors[node.id] = signature_to_color[signatures[node.id]]

    return new_colors


def _neighbor_color_multiset(
    edges: list[WeightedEdge],
    prev_colors: dict[NodeId, Color],
) -> tuple[WeightedNeighborColor, ...]:
    # CG-WL compares neighbor groups, not raw neighbor identities:
    # key = previous neighbor color, value += static callsite count.
    count_by_color: dict[Color, int] = {}

    for node_id, count in edges:
        color = prev_colors[node_id]
        count_by_color[color] = count_by_color.get(color, 0) + count

    return tuple(sorted(count_by_color.items()))


def make_scored_clusters(
    case: Case,
    colors: dict[NodeId, Color],
) -> list[list[NodeId]]:
    by_color: dict[Color, list[NodeId]] = defaultdict(list)

    for node in case.nodes:
        if node.scored:
            by_color[colors[node.id]].append(node.id)

    clusters = [
        sorted(node_ids)
        for node_ids in by_color.values()
    ]

    clusters.sort(key=lambda cluster: (cluster[0], len(cluster)))
    return clusters


def make_cluster_id_by_node(
    clusters: list[list[NodeId]],
) -> dict[NodeId, int]:
    cluster_id_by_node: dict[NodeId, int] = {}

    for cluster_id, cluster in enumerate(clusters):
        for node_id in cluster:
            cluster_id_by_node[node_id] = cluster_id

    return cluster_id_by_node


def same_partition(
    node_ids: list[NodeId],
    colors_a: dict[NodeId, Color],
    colors_b: dict[NodeId, Color],
) -> bool:
    return canonical_partition(node_ids, colors_a) == canonical_partition(
        node_ids,
        colors_b,
    )


def canonical_partition(
    node_ids: list[NodeId],
    colors: dict[NodeId, Color],
) -> tuple[tuple[NodeId, ...], ...]:
    by_color: dict[Color, list[NodeId]] = defaultdict(list)

    for node_id in node_ids:
        by_color[colors[node_id]].append(node_id)

    groups = [
        tuple(sorted(group))
        for group in by_color.values()
    ]

    return tuple(sorted(groups))


def _canonicalize_signatures(
    signatures: dict[NodeId, RelationSignature],
) -> dict[RelationSignature, Color]:
    unique_signatures = sorted(set(signatures.values()))

    return {
        signature: f"C:{index}"
        for index, signature in enumerate(unique_signatures)
    }


def _anchor_color(node_id: NodeId) -> Color:
    return f"ANCHOR:{node_id}"
