# Minimal measurement evidence report generator.
#
# This is score-side code. It joins fixture, ground truth, and CG-WL output
# after the engine has run. It does not generate diagnosis or conclusions.
# The goal is to provide the objective values needed to write measurement notes.

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from engine import (
    CG_WL_MODES,
    DEFAULT_CG_WL_MODE,
    CGWLMode,
    build_relation_graph_view,
    make_initial_cg_wl_colors,
    refine_cg_wl_once,
    same_partition,
)
from loader import load_case
from model import Case
from paths import DEFAULT_BUILD, resolve_fixture_json, resolve_gt_json, split_case_build
from scores import GroundTruth, load_ground_truth, score_case


DEFAULT_JOBS: tuple[tuple[str, str], ...] = (
    ("family_graph_01", "O3S"),
    ("family_graph_02", "O3S"),
    ("family_graph_03", "O3S"),
    ("family_graph_03", "O3KS"),
)


ORIGIN_HEADERS = [
    "case",
    "build",
    "origin",
    "k_obs",
    "members",
    "symbols",
]

ANCHOR_HEADERS = [
    "case",
    "build",
    "anchor",
    "role",
    "out",
    "in",
]

INSTANCE_HEADERS = [
    "case",
    "build",
    "origin",
    "member",
    "symbol",
    "self_call_count",
    "distinct_out_callee_count",
    "distinct_in_caller_count",
    "out_edges",
    "out_by_label",
    "in_edges",
    "in_by_label",
]

ROUND_HEADERS = [
    "case",
    "build",
    "mode",
    "round",
    "num_classes",
    "classes",
    "split_this_round",
]

SIGNATURE_HEADERS = [
    "case",
    "build",
    "mode",
    "from_round",
    "member",
    "origin",
    "previous_class",
    "out_color_multiset",
    "in_color_multiset",
    "used_signature",
    "next_class",
    "partition_changed",
]

FAMILY_HEADERS = [
    "case",
    "build",
    "mode",
    "origin",
    "k_obs",
    "d_star",
    "num_predicted_clusters",
    "family_pair_recall",
    "collision_with",
    "observed_relation_patterns",
]

CLUSTER_HEADERS = [
    "case",
    "build",
    "mode",
    "cluster",
    "members",
    "symbols",
    "origins",
    "relation_patterns",
]

SCORE_HEADERS = [
    "case",
    "build",
    "mode",
    "engine_rounds",
    "effective_rounds",
    "TP",
    "FP",
    "FN",
    "TN",
    "precision",
    "recall",
    "F1",
    "ARI",
]

COLLISION_HEADERS = [
    "case",
    "build",
    "mode",
    "cluster",
    "members",
    "symbols",
    "origins",
    "relation_patterns",
]


def refinement_trace(case: Case, mode: CGWLMode):
    """Return view, effective color history, and refinement transitions.

    round 0 is the seed partition. The engine's public rounds value includes
    the final no-change confirmation; this report's effective round index does
    not. The transition list includes that final confirmation step so notes can
    quote the engine signature even when the seed is already a fixpoint.
    """
    view = build_relation_graph_view(case)
    colors = make_initial_cg_wl_colors(case, view, mode=mode)
    history = [colors]
    transitions = []

    for _round_index in range(len(view.node_ids)):
        new_colors = refine_cg_wl_once(case, view, colors, mode=mode)
        changed = not same_partition(view.node_ids, colors, new_colors)
        transitions.append((colors, new_colors, changed))
        if not changed:
            return view, history, transitions
        history.append(new_colors)
        colors = new_colors

    raise RuntimeError("CG-WL did not reach a fixpoint")


def display_symbol(gt: GroundTruth, symbol: str) -> str:
    prefix = f"{gt.case}::"
    if symbol.startswith(prefix):
        return symbol[len(prefix):]
    return symbol


def member_symbols(gt: GroundTruth, member_id: str) -> str:
    return " | ".join(display_symbol(gt, symbol) for symbol in gt.symbols[member_id])


def anchor_roles(case: Case, view) -> dict[str, str]:
    scored = {node.id for node in case.nodes if node.scored}
    roles = {}

    for node in case.nodes:
        if node.type != "anchor":
            continue

        calls_users = any(dst in scored for dst, _count in view.outgoing[node.id])
        called_by_users = any(src in scored for src, _count in view.incoming[node.id])

        if calls_users and called_by_users:
            role = "anchor:both"
        elif calls_users:
            role = "anchor:root"
        elif called_by_users:
            role = "anchor:callee"
        else:
            role = "anchor"
        roles[node.id] = role

    return roles


def node_label(node_id: str, origin_of: dict[str, str], roles: dict[str, str]) -> str:
    return origin_of.get(node_id) or roles.get(node_id, "anchor")


def aggregate_edges(edges, origin_of: dict[str, str], roles: dict[str, str]):
    counts: dict[str, int] = {}
    for node_id, count in edges:
        label = node_label(node_id, origin_of, roles)
        counts[label] = counts.get(label, 0) + count
    return tuple(sorted(counts.items()))


def render_aggregate(agg) -> str:
    if not agg:
        return "-"
    return "; ".join(f"{label}*{count}" for label, count in agg)


def aggregate_color_edges(edges, colors: dict[str, str], color_labels: dict[str, str]):
    counts: dict[str, int] = {}
    for node_id, count in edges:
        label = color_labels[colors[node_id]]
        counts[label] = counts.get(label, 0) + count
    return tuple(sorted(counts.items()))


def render_edges(edges, origin_of: dict[str, str], roles: dict[str, str]) -> str:
    if not edges:
        return "-"
    parts = []
    for node_id, count in sorted(edges):
        parts.append(f"{node_id}({node_label(node_id, origin_of, roles)})*{count}")
    return "; ".join(parts)


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def as_markdown(rows: list[dict[str, Any]], headers: list[str]) -> str:
    if not rows:
        return "_empty_"
    out = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _header in headers) + "|",
    ]
    for row in rows:
        out.append("| " + " | ".join(md_cell(row[h]) for h in headers) + " |")
    return "\n".join(out)


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def origin_rows(case: Case, gt: GroundTruth) -> list[dict[str, Any]]:
    rows = []
    for group in gt.origins:
        rows.append({
            "case": case.case,
            "build": case.build,
            "origin": group.origin,
            "k_obs": len(group.members),
            "members": ";".join(group.members),
            "symbols": ";".join(member_symbols(gt, member) for member in group.members),
        })
    return rows


def anchor_rows(case: Case, view, roles: dict[str, str], origin_of: dict[str, str]):
    rows = []
    for node in case.nodes:
        if node.type != "anchor":
            continue
        rows.append({
            "case": case.case,
            "build": case.build,
            "anchor": node.id,
            "role": roles.get(node.id, "anchor"),
            "out": render_edges(view.outgoing[node.id], origin_of, roles),
            "in": render_edges(view.incoming[node.id], origin_of, roles),
        })
    return rows


def instance_relation_rows(
    case: Case,
    gt: GroundTruth,
    view,
    roles: dict[str, str],
) -> list[dict[str, Any]]:
    origin_of = gt.origin_of()
    rows = []

    for group in gt.origins:
        for member in group.members:
            out_agg = aggregate_edges(view.outgoing[member], origin_of, roles)
            in_agg = aggregate_edges(view.incoming[member], origin_of, roles)
            rows.append({
                "case": case.case,
                "build": case.build,
                "origin": group.origin,
                "member": member,
                "symbol": member_symbols(gt, member),
                "self_call_count": view.self_call_count[member],
                "distinct_out_callee_count": view.distinct_out_callee_count[member],
                "distinct_in_caller_count": view.distinct_in_caller_count[member],
                "out_edges": render_edges(view.outgoing[member], origin_of, roles),
                "out_by_label": render_aggregate(out_agg),
                "in_edges": render_edges(view.incoming[member], origin_of, roles),
                "in_by_label": render_aggregate(in_agg),
            })

    return rows


def relation_pattern_for_member(
    member: str,
    view,
    origin_of: dict[str, str],
    roles: dict[str, str],
) -> str:
    out_agg = aggregate_edges(view.outgoing[member], origin_of, roles)
    in_agg = aggregate_edges(view.incoming[member], origin_of, roles)
    return (
        f"self={view.self_call_count[member]}; "
        f"dout={view.distinct_out_callee_count[member]}; "
        f"din={view.distinct_in_caller_count[member]}; "
        f"out={render_aggregate(out_agg)}; "
        f"in={render_aggregate(in_agg)}"
    )


def origin_relation_patterns(
    members: list[str],
    view,
    origin_of: dict[str, str],
    roles: dict[str, str],
) -> str:
    buckets: dict[str, int] = {}
    for member in members:
        pattern = relation_pattern_for_member(member, view, origin_of, roles)
        buckets[pattern] = buckets.get(pattern, 0) + 1
    return " | ".join(
        f"{count}*[{pattern}]"
        for pattern, count in sorted(buckets.items(), key=lambda item: (-item[1], item[0]))
    )


def cluster_map(case: Case, colors: dict[str, str]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = defaultdict(list)
    for node in case.nodes:
        if node.scored:
            clusters[colors[node.id]].append(node.id)
    for members in clusters.values():
        members.sort()
    return dict(clusters)


def ordered_clusters(clusters: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    return sorted(clusters.items(), key=lambda item: (item[1][0], len(item[1])))


def cluster_names(clusters: dict[str, list[str]]) -> dict[str, str]:
    return {
        color: f"C{index + 1}"
        for index, (color, _members) in enumerate(ordered_clusters(clusters))
    }


def round_color_labels(
    case: Case,
    colors: dict[str, str],
    roles: dict[str, str],
    round_index: int,
) -> dict[str, str]:
    clusters = cluster_map(case, colors)
    labels: dict[str, str] = {}
    for index, (color, _members) in enumerate(ordered_clusters(clusters), start=1):
        labels[color] = f"R{round_index}C{index}"

    for node in case.nodes:
        if node.type == "anchor":
            labels[colors[node.id]] = roles.get(node.id, "anchor")

    return labels


def used_signature(
    mode: CGWLMode,
    previous_class: str,
    out_colors: str,
    in_colors: str,
) -> str:
    if mode == "full":
        return f"prev={previous_class}; out={out_colors}; in={in_colors}"
    if mode == "out":
        return f"prev={previous_class}; out={out_colors}"
    if mode == "in":
        return f"prev={previous_class}; in={in_colors}"
    if mode == "out-in":
        if out_colors == "-":
            return f"prev={previous_class}; out={out_colors}; in={in_colors}"
        return f"prev={previous_class}; out={out_colors}"
    raise ValueError(f"unknown mode: {mode}")


def round_rows(
    case: Case,
    gt: GroundTruth,
    mode: CGWLMode,
    history,
) -> list[dict[str, Any]]:
    origin_of = gt.origin_of()
    rows = []
    prev_color_count_by_origin: dict[str, int] = {}

    for round_index, colors in enumerate(history):
        clusters = cluster_map(case, colors)
        rendered_classes = []
        for _color, members in ordered_clusters(clusters):
            counts: dict[str, int] = {}
            for member in members:
                origin = origin_of[member]
                counts[origin] = counts.get(origin, 0) + 1
            rendered_classes.append("{" + ", ".join(
                f"{origin}*{count}" if count > 1 else origin
                for origin, count in sorted(counts.items())
            ) + "}")

        split_this_round = []
        for group in gt.origins:
            n_colors = len({colors[member] for member in group.members})
            if round_index > 0 and n_colors > prev_color_count_by_origin.get(group.origin, 1):
                split_this_round.append(group.origin)
            prev_color_count_by_origin[group.origin] = n_colors

        rows.append({
            "case": case.case,
            "build": case.build,
            "mode": mode,
            "round": round_index,
            "num_classes": len(clusters),
            "classes": " ".join(rendered_classes),
            "split_this_round": ";".join(split_this_round) if split_this_round else "-",
        })

    return rows


def signature_rows(
    case: Case,
    gt: GroundTruth,
    mode: CGWLMode,
    view,
    roles: dict[str, str],
    transitions,
) -> list[dict[str, Any]]:
    origin_of = gt.origin_of()
    rows = []

    for round_index, (prev_colors, next_colors, changed) in enumerate(transitions):
        prev_labels = round_color_labels(case, prev_colors, roles, round_index)
        next_labels = round_color_labels(case, next_colors, roles, round_index + 1)

        for group in gt.origins:
            for member in group.members:
                out_colors = render_aggregate(
                    aggregate_color_edges(view.outgoing[member], prev_colors, prev_labels)
                )
                in_colors = render_aggregate(
                    aggregate_color_edges(view.incoming[member], prev_colors, prev_labels)
                )
                previous_class = prev_labels[prev_colors[member]]
                rows.append({
                    "case": case.case,
                    "build": case.build,
                    "mode": mode,
                    "from_round": round_index,
                    "member": member,
                    "origin": origin_of[member],
                    "previous_class": previous_class,
                    "out_color_multiset": out_colors,
                    "in_color_multiset": in_colors,
                    "used_signature": used_signature(
                        mode,
                        previous_class,
                        out_colors,
                        in_colors,
                    ),
                    "next_class": next_labels[next_colors[member]],
                    "partition_changed": changed,
                })

    return rows


def family_rows(
    case: Case,
    gt: GroundTruth,
    mode: CGWLMode,
    history,
    view,
    roles: dict[str, str],
) -> list[dict[str, Any]]:
    origin_of = gt.origin_of()
    final_colors = history[-1]
    final_clusters = cluster_map(case, final_colors)
    origins_by_color = {
        color: sorted({origin_of[member] for member in members})
        for color, members in final_clusters.items()
    }

    rows = []
    for group in gt.origins:
        members = list(group.members)
        d_star: int | str = "-"
        if len(members) >= 2:
            for round_index, colors in enumerate(history):
                if len({colors[member] for member in members}) > 1:
                    d_star = round_index
                    break

        colors_for_origin = {final_colors[member] for member in members}
        total_pairs = len(members) * (len(members) - 1) // 2
        kept_pairs = sum(
            1
            for a, b in combinations(members, 2)
            if final_colors[a] == final_colors[b]
        )
        recall = "n/a" if total_pairs == 0 else f"{kept_pairs}/{total_pairs}={kept_pairs / total_pairs:.2f}"

        collision_partners = sorted({
            other
            for color in colors_for_origin
            for other in origins_by_color[color]
            if other != group.origin
        })

        rows.append({
            "case": case.case,
            "build": case.build,
            "mode": mode,
            "origin": group.origin,
            "k_obs": len(members),
            "d_star": d_star,
            "num_predicted_clusters": len(colors_for_origin),
            "family_pair_recall": recall,
            "collision_with": ";".join(collision_partners) if collision_partners else "-",
            "observed_relation_patterns": origin_relation_patterns(members, view, origin_of, roles),
        })

    return rows


def predicted_cluster_rows(
    case: Case,
    gt: GroundTruth,
    mode: CGWLMode,
    history,
    view,
    roles: dict[str, str],
) -> list[dict[str, Any]]:
    origin_of = gt.origin_of()
    final_colors = history[-1]
    clusters = cluster_map(case, final_colors)
    names = cluster_names(clusters)
    rows = []

    for color, members in ordered_clusters(clusters):
        origins = sorted({origin_of[member] for member in members})
        pattern_counts: dict[str, int] = {}
        for member in members:
            pattern = relation_pattern_for_member(member, view, origin_of, roles)
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        rows.append({
            "case": case.case,
            "build": case.build,
            "mode": mode,
            "cluster": names[color],
            "members": ";".join(members),
            "symbols": ";".join(member_symbols(gt, member) for member in members),
            "origins": ";".join(origins),
            "relation_patterns": " | ".join(
                f"{count}*[{pattern}]"
                for pattern, count in sorted(pattern_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
        })

    return rows


def collision_rows(cluster_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in cluster_rows:
        origins = str(row["origins"]).split(";")
        if len(origins) >= 2:
            rows.append({
                "case": row["case"],
                "build": row["build"],
                "mode": row["mode"],
                "cluster": row["cluster"],
                "members": row["members"],
                "symbols": row["symbols"],
                "origins": row["origins"],
                "relation_patterns": row["relation_patterns"],
            })
    return rows


def score_row(
    fixture_path: str,
    gt_path: str,
    mode: CGWLMode,
    effective_rounds: int,
) -> dict[str, Any]:
    report = score_case(fixture_path, gt_path, mode=mode)
    p = report.pairwise
    return {
        "case": report.case,
        "build": report.build,
        "mode": report.mode,
        "engine_rounds": report.rounds,
        "effective_rounds": effective_rounds,
        "TP": p.tp,
        "FP": p.fp,
        "FN": p.fn,
        "TN": p.tn,
        "precision": f"{p.precision:.2f}",
        "recall": f"{p.recall:.2f}",
        "F1": f"{p.f1:.2f}",
        "ARI": f"{p.ari:.2f}",
    }


def run_one(case_name: str, build: str, mode: CGWLMode):
    fixture_path = resolve_fixture_json(case_name, build)
    gt_path = resolve_gt_json(case_name, build)
    case = load_case(fixture_path)
    gt = load_ground_truth(gt_path)
    view, history, transitions = refinement_trace(case, mode)
    roles = anchor_roles(case, view)
    origin_of = gt.origin_of()
    clusters = predicted_cluster_rows(case, gt, mode, history, view, roles)

    return {
        "case": case,
        "fixture_path": fixture_path,
        "gt_path": gt_path,
        "mode": mode,
        "origin_rows": origin_rows(case, gt),
        "anchor_rows": anchor_rows(case, view, roles, origin_of),
        "instance_rows": instance_relation_rows(case, gt, view, roles),
        "round_rows": round_rows(case, gt, mode, history),
        "signature_rows": signature_rows(case, gt, mode, view, roles, transitions),
        "family_rows": family_rows(case, gt, mode, history, view, roles),
        "cluster_rows": clusters,
        "collision_rows": collision_rows(clusters),
        "score_row": score_row(fixture_path, gt_path, mode, len(history) - 1),
    }


def append_case_markdown(parts: list[str], result: dict[str, Any]) -> None:
    case: Case = result["case"]
    mode = result["mode"]
    parts.append(f"## {case.case} / {case.build} / mode={mode}\n")
    parts.append("### Inputs\n")
    parts.append(
        "```text\n"
        f"fixture: {result['fixture_path']}\n"
        f"ground truth: {result['gt_path']}\n"
        "```\n"
    )
    parts.append("### Origins\n")
    parts.append(as_markdown(result["origin_rows"], ORIGIN_HEADERS) + "\n")
    parts.append("### Anchors\n")
    parts.append(as_markdown(result["anchor_rows"], ANCHOR_HEADERS) + "\n")
    parts.append("### Instance Relations\n")
    parts.append(as_markdown(result["instance_rows"], INSTANCE_HEADERS) + "\n")
    parts.append("### Round Partitions\n")
    parts.append(as_markdown(result["round_rows"], ROUND_HEADERS) + "\n")
    parts.append("### Round Signatures\n")
    parts.append(as_markdown(result["signature_rows"], SIGNATURE_HEADERS) + "\n")
    parts.append("### Family Rows\n")
    parts.append(as_markdown(result["family_rows"], FAMILY_HEADERS) + "\n")
    parts.append("### Predicted Clusters\n")
    parts.append(as_markdown(result["cluster_rows"], CLUSTER_HEADERS) + "\n")
    if result["collision_rows"]:
        parts.append("### Collision Candidates\n")
        parts.append(as_markdown(result["collision_rows"], COLLISION_HEADERS) + "\n")
    parts.append("### Scores\n")
    parts.append(as_markdown([result["score_row"]], SCORE_HEADERS) + "\n")


def parse_jobs(stem: str | None, build: str | None) -> list[tuple[str, str]]:
    if stem is None:
        return list(DEFAULT_JOBS)
    case_name, resolved_build = split_case_build(stem, build)
    return [(case_name, resolved_build)]


def parse_modes(mode: CGWLMode, all_modes: bool) -> tuple[CGWLMode, ...]:
    if all_modes:
        return CG_WL_MODES
    return (mode,)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate minimal score-side evidence for measurement notes."
    )
    parser.add_argument(
        "stem",
        nargs="?",
        help="case stem such as family_graph_03 or family_graph_03.O3KS",
    )
    parser.add_argument("--build", default=None, help=f"default: {DEFAULT_BUILD}")
    parser.add_argument(
        "--mode",
        choices=CG_WL_MODES,
        default=DEFAULT_CG_WL_MODE,
        help=f"default: {DEFAULT_CG_WL_MODE}",
    )
    parser.add_argument(
        "--all-modes",
        action="store_true",
        help="report full, out, in, and out-in modes",
    )
    parser.add_argument("--out-dir", default="reports")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_origin_rows: list[dict[str, Any]] = []
    all_anchor_rows: list[dict[str, Any]] = []
    all_instance_rows: list[dict[str, Any]] = []
    all_round_rows: list[dict[str, Any]] = []
    all_signature_rows: list[dict[str, Any]] = []
    all_family_rows: list[dict[str, Any]] = []
    all_cluster_rows: list[dict[str, Any]] = []
    all_collision_rows: list[dict[str, Any]] = []
    all_score_rows: list[dict[str, Any]] = []

    markdown_parts = [
        "# Measurement Evidence\n",
        (
            "This report contains observed values only: origin membership, "
            "anchor context, per-instance Axis-1 relations, CG-WL round "
            "partitions, family rows, predicted clusters, collisions, and "
            "pairwise scores. It intentionally omits diagnosis, conclusions, "
            "source-level census, and coverage.\n"
        ),
    ]

    for case_name, build in parse_jobs(args.stem, args.build):
        for mode in parse_modes(args.mode, args.all_modes):
            result = run_one(case_name, build, mode)
            append_case_markdown(markdown_parts, result)
            all_origin_rows.extend(result["origin_rows"])
            all_anchor_rows.extend(result["anchor_rows"])
            all_instance_rows.extend(result["instance_rows"])
            all_round_rows.extend(result["round_rows"])
            all_signature_rows.extend(result["signature_rows"])
            all_family_rows.extend(result["family_rows"])
            all_cluster_rows.extend(result["cluster_rows"])
            all_collision_rows.extend(result["collision_rows"])
            all_score_rows.append(result["score_row"])

    report_path = out_dir / "measurement_evidence.md"
    report_path.write_text("\n".join(markdown_parts), encoding="utf-8")

    write_csv(out_dir / "origins.csv", all_origin_rows, ORIGIN_HEADERS)
    write_csv(out_dir / "anchors.csv", all_anchor_rows, ANCHOR_HEADERS)
    write_csv(out_dir / "instance_relations.csv", all_instance_rows, INSTANCE_HEADERS)
    write_csv(out_dir / "round_partitions.csv", all_round_rows, ROUND_HEADERS)
    write_csv(out_dir / "round_signatures.csv", all_signature_rows, SIGNATURE_HEADERS)
    write_csv(out_dir / "family_rows.csv", all_family_rows, FAMILY_HEADERS)
    write_csv(out_dir / "predicted_clusters.csv", all_cluster_rows, CLUSTER_HEADERS)
    write_csv(out_dir / "collision_candidates.csv", all_collision_rows, COLLISION_HEADERS)
    write_csv(out_dir / "scores.csv", all_score_rows, SCORE_HEADERS)

    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
