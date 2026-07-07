# Family-level measurement report generator.
#
# This is not part of the grouping engine. It is a score-side measurement
# tool: it joins fixture, ground truth, and CG-WL output to produce
# origin/family-level diagnostic tables.

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable

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


# ------------------------------------------------------------ known jobs/census

DEFAULT_JOBS = (
    ("family_graph_01", "O3S"),
    ("family_graph_02", "O3S"),
    ("family_graph_03", "O3KS"),
    ("family_graph_03", "O3S"),
)


@dataclass(frozen=True)
class CensusEntry:
    k_ref: int
    census_source: str
    expected_instances: str = "-"


FG01_SOURCE_CENSUS = {
    "shared_recursive": CensusEntry(3, "source fg01.md", "i32 / u64 / f64"),
    "process": CensusEntry(3, "source fg01.md", "i32 / u64 / f64"),
    "summarize": CensusEntry(3, "source fg01.md", "i32 / u64 / f64"),
    "combine": CensusEntry(3, "source fg01.md", "i32 / u64 / f64"),
    "score": CensusEntry(3, "source fg01.md", "i32 / u64 / f64"),
}


# For fg03/O3S the current source-level census is approximated from O3KS.
# This is explicitly marked as temporary in the report.
GT_CENSUS_JOBS = {
    ("family_graph_03", "O3KS"): ("family_graph_03", "O3KS", "O3KS(self)"),
    ("family_graph_03", "O3S"): ("family_graph_03", "O3KS", "O3KS(temporary)"),
}


# -------------------------------------------------------------- table schemas

FAMILY_HEADERS = [
    "case",
    "build",
    "mode",
    "source_origin",
    "monomorphized_instances",
    "observed_symbols",
    "k_obs",
    "k_ref",
    "census_source",
    "expected_instances",
    "survival_status",
    "d_star",
    "num_predicted_clusters_for_origin",
    "family_pair_recall_conditional",
    "collision_with",
    "observed_relation_pattern",
    "measurement_label",
    "diagnosis",
]

CURVE_HEADERS = [
    "case",
    "build",
    "mode",
    "round",
    "clusters",
    "TP",
    "FP",
    "FN",
    "precision",
    "recall_conditional",
    "F1",
]

CATALOG_HEADERS = [
    "case",
    "build",
    "mode",
    "relation_pattern",
    "source_origins_involved",
    "injected_control",
    "collision_type",
    "interpretation",
]


# Researcher annotations. These are controlled-corpus notes, not automatic
# observations. Unknown collisions are emitted with TODO fields.
MANUAL_ANNOTATIONS = {
    (
        "family_graph_02",
        "O3S",
        ("c_process_alpha_i32", "c_process_alpha_wide", "process_alpha"),
    ): (
        "yes (concrete mirror, Axis-1 isomorphic by construction)",
        "different-origin same-relation (constructed)",
        "Relation-only feature limit stress case. This is a catalog item, not a frequency estimate.",
    ),
    (
        "family_graph_02",
        "O3S",
        ("c_recurse_alpha_i32", "c_recurse_alpha_wide", "recurse_alpha"),
    ): (
        "yes (concrete mirror, Axis-1 isomorphic by construction)",
        "different-origin same-relation (constructed)",
        "Relation-only feature limit stress case. This is a catalog item, not a frequency estimate.",
    ),
    ("family_graph_03", "O3KS", ("decoy_a", "decoy_b")): (
        "no (structural)",
        "low-information leaf signature",
        "out=0 and comparable caller context leaves origin undecided.",
    ),
    ("family_graph_03", "O3S", ("decoy_a", "decoy_b")): (
        "no (structural)",
        "low-information leaf signature",
        "out=0 and comparable caller context leaves origin undecided.",
    ),
}


# --------------------------------------------------------------- CG-WL history

def color_history(
    case: Case,
    *,
    mode: CGWLMode = DEFAULT_CG_WL_MODE,
):
    """Return view and color snapshots from seed to last changed partition.

    engine.run_cg_wl().rounds includes the final no-change confirmation round.
    This report uses effective refinement depth:

      round 0 = seed
      round t = t effective refinement steps
    """
    view = build_relation_graph_view(case)
    colors = make_initial_cg_wl_colors(case, view, mode=mode)
    history = [colors]

    for _round_index in range(len(view.node_ids)):
        new_colors = refine_cg_wl_once(case, view, colors, mode=mode)
        if same_partition(view.node_ids, colors, new_colors):
            return view, history
        history.append(new_colors)
        colors = new_colors

    raise RuntimeError("CG-WL did not reach a fixpoint")


# ------------------------------------------------------------------ utilities

def anchor_roles(case: Case, view):
    """Classify anchors by their relation to scored user nodes."""
    scored = {node.id for node in case.nodes if node.scored}
    roles = {}

    for node in case.nodes:
        if node.type != "anchor":
            continue

        calls_users = any(dst in scored for dst, _count in view.outgoing[node.id])
        called_by_users = any(src in scored for src, _count in view.incoming[node.id])

        if called_by_users and not calls_users:
            roles[node.id] = "anchor:callee"
        elif calls_users and not called_by_users:
            roles[node.id] = "anchor:root"
        else:
            roles[node.id] = "anchor"

    return roles


def member_symbols(gt: GroundTruth, member_id: str) -> str:
    names = [display_symbol(gt, name) for name in gt.symbols[member_id]]
    return " | ".join(names)


def display_symbol(gt: GroundTruth, symbol: str) -> str:
    prefix = f"{gt.case}::"
    if symbol.startswith(prefix):
        return symbol[len(prefix):]
    return symbol


def neighbor_label(node_id: str, origin_of: dict[str, str], roles: dict[str, str]) -> str:
    return origin_of.get(node_id) or roles.get(node_id, "anchor")


def aggregate_by_label(edges, origin_of: dict[str, str], roles: dict[str, str]):
    agg: dict[str, int] = {}
    for node_id, count in edges:
        label = neighbor_label(node_id, origin_of, roles)
        agg[label] = agg.get(label, 0) + count
    return tuple(sorted(agg.items()))


def render_agg(agg) -> str:
    return ", ".join(f"{label}x{count}" for label, count in agg) if agg else "-"


def md_cell(value) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def as_markdown(rows, headers) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        out.append("| " + " | ".join(md_cell(row[h]) for h in headers) + " |")
    return "\n".join(out)


# ------------------------------------------------------ observed relation data

def origin_pattern_summary(case: Case, gt: GroundTruth, view, roles):
    """Summarize raw relation patterns per source origin.

    The labels are attached only in this measurement layer. The engine still
    receives fixture IDs and anchor colors, never origin labels.
    """
    origin_of = gt.origin_of()
    summary = {}

    for group in gt.origins:
        buckets = {}
        for member in group.members:
            key = (
                view.self_call_count[member],
                aggregate_by_label(view.outgoing[member], origin_of, roles),
                aggregate_by_label(view.incoming[member], origin_of, roles),
            )
            buckets.setdefault(key, []).append(member)

        parts = []
        for (self_count, out_agg, in_agg), members in sorted(
            buckets.items(),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            parts.append(
                f"{len(members)}x[self={self_count}; "
                f"out={render_agg(out_agg)}; in={render_agg(in_agg)}]"
            )
        summary[group.origin] = " ; ".join(parts)

    return summary


def case_origin_rows(case: Case, gt: GroundTruth, view, roles, census):
    rows = []
    gt_origins = {group.origin for group in gt.origins}
    anchors = [node.id for node in case.nodes if node.type == "anchor"]

    for group in gt.origins:
        rows.append({
            "kind": "origin",
            "name": group.origin,
            "k_obs": len(group.members),
            "k_ref": census.get(group.origin, CensusEntry(len(group.members), "-")).k_ref,
            "members": "; ".join(group.members),
            "symbols": "; ".join(member_symbols(gt, member) for member in group.members),
        })

    for origin, entry in sorted(census.items()):
        if origin not in gt_origins:
            rows.append({
                "kind": "origin(vanished)",
                "name": origin,
                "k_obs": 0,
                "k_ref": entry.k_ref,
                "members": "-",
                "symbols": entry.expected_instances,
            })

    for anchor in anchors:
        rows.append({
            "kind": roles.get(anchor, "anchor"),
            "name": anchor,
            "k_obs": "-",
            "k_ref": "-",
            "members": anchor,
            "symbols": "-",
        })

    return rows


CASE_ORIGIN_HEADERS = ["kind", "name", "k_obs", "k_ref", "members", "symbols"]


# --------------------------------------------------------------- family table

def family_rows(
    case: Case,
    gt: GroundTruth,
    mode: CGWLMode,
    history,
    patterns,
    census: dict[str, CensusEntry],
):
    final_colors = history[-1]
    origin_of = gt.origin_of()

    cluster_members: dict[str, list[str]] = {}
    for node in case.nodes:
        if node.scored:
            cluster_members.setdefault(final_colors[node.id], []).append(node.id)

    origins_in_cluster = {
        color: sorted({origin_of[member] for member in members})
        for color, members in cluster_members.items()
    }

    rows = []
    seen = set()

    def one_row(origin: str, members: list[str]) -> None:
        seen.add(origin)
        entry = census.get(origin)
        k_obs = len(members)
        k_ref = entry.k_ref if entry else None

        if entry is None:
            survival = "unverified(no census)"
            k_ref_text = "-"
            census_source = "-"
            expected_instances = "-"
        elif k_obs == 0:
            survival = "vanished"
            k_ref_text = str(k_ref)
            census_source = entry.census_source
            expected_instances = entry.expected_instances
        elif k_obs < entry.k_ref:
            survival = f"partial({k_obs}/{entry.k_ref})"
            k_ref_text = str(k_ref)
            census_source = entry.census_source
            expected_instances = entry.expected_instances
        else:
            survival = "full"
            k_ref_text = str(k_ref)
            census_source = entry.census_source
            expected_instances = entry.expected_instances

        d_star = None
        if k_obs >= 2:
            for round_index, colors in enumerate(history):
                if len({colors[member] for member in members}) > 1:
                    d_star = round_index
                    break

        family_colors = {final_colors[member] for member in members}
        num_clusters = len(family_colors)

        total_pairs = k_obs * (k_obs - 1) // 2
        tp_pairs = sum(
            1
            for a, b in combinations(members, 2)
            if final_colors[a] == final_colors[b]
        )
        recall_cond = f"{tp_pairs / total_pairs:.2f}" if total_pairs else "n/a"

        partners = sorted({
            other
            for color in family_colors
            for other in origins_in_cluster[color]
            if other != origin
        })

        if k_obs == 0:
            label = "missing-in-build"
        elif k_obs == 1:
            label = "singleton(no within-family pair)"
        elif d_star is None:
            label = "consistent"
        elif d_star == 0:
            label = "seed-split"
        else:
            label = f"propagated-split(round {d_star})"
        if partners:
            label += "+collision"

        if k_obs == 0:
            diagnosis = "likely fully inlined in controlled build; census should be kept explicit"
        elif entry is not None and k_obs < entry.k_ref:
            diagnosis = "only part of the source-level family survived out-of-line"
        elif d_star == 0:
            diagnosis = "local relation shape differs at seed"
        elif d_star is not None:
            diagnosis = f"split likely propagated through relation context at round {d_star}"
        elif partners:
            diagnosis = "relation signature is not origin-determining; see collision catalog"
        else:
            diagnosis = "-"

        rows.append({
            "case": case.case,
            "build": case.build,
            "mode": mode,
            "source_origin": origin,
            "monomorphized_instances": ";".join(members) if members else "-",
            "observed_symbols": ";".join(member_symbols(gt, member) for member in members) if members else "-",
            "k_obs": k_obs,
            "k_ref": k_ref_text,
            "census_source": census_source,
            "expected_instances": expected_instances,
            "survival_status": survival,
            "d_star": "-" if d_star is None else d_star,
            "num_predicted_clusters_for_origin": num_clusters,
            "family_pair_recall_conditional": recall_cond,
            "collision_with": ";".join(partners) if partners else "-",
            "observed_relation_pattern": patterns.get(origin, "-"),
            "measurement_label": label,
            "diagnosis": diagnosis,
        })

    for group in gt.origins:
        one_row(group.origin, list(group.members))

    for origin in sorted(census):
        if origin not in seen:
            one_row(origin, [])

    return rows


# -------------------------------------------------------------- depth metrics

def pairwise_counts(cluster_of, origin_of, scored_ids):
    tp = fp = fn = tn = 0
    for a, b in combinations(sorted(scored_ids), 2):
        pred_same = cluster_of[a] == cluster_of[b]
        true_same = origin_of[a] == origin_of[b]
        if pred_same and true_same:
            tp += 1
        elif pred_same:
            fp += 1
        elif true_same:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def prf(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return precision, recall, f1


def depth_curve(case: Case, gt: GroundTruth, mode: CGWLMode, history):
    origin_of = gt.origin_of()
    scored_ids = [node.id for node in case.nodes if node.scored]
    rows = []

    for round_index, colors in enumerate(history):
        cluster_of = {node_id: colors[node_id] for node_id in scored_ids}
        tp, fp, fn, _tn = pairwise_counts(cluster_of, origin_of, scored_ids)
        precision, recall, f1 = prf(tp, fp, fn)
        rows.append({
            "case": case.case,
            "build": case.build,
            "mode": mode,
            "round": round_index,
            "clusters": len(set(cluster_of.values())),
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "precision": f"{precision:.2f}",
            "recall_conditional": f"{recall:.2f}",
            "F1": f"{f1:.2f}",
        })

    return rows


# ------------------------------------------------------------ collision table

def cluster_names(final_colors, cluster_members):
    ordered = sorted(
        cluster_members.items(),
        key=lambda item: (sorted(item[1])[0], len(item[1])),
    )
    return {color: f"C{index + 1}" for index, (color, _members) in enumerate(ordered)}


def fixpoint_signature(member, final_colors, view, roles, cluster_name_of_color):
    def label(node_id):
        if node_id in roles:
            return roles[node_id]
        color = final_colors[node_id]
        return cluster_name_of_color.get(color, "C?")

    out_agg = {}
    in_agg = {}

    for dst, count in view.outgoing[member]:
        out_agg[label(dst)] = out_agg.get(label(dst), 0) + count
    for src, count in view.incoming[member]:
        in_agg[label(src)] = in_agg.get(label(src), 0) + count

    return (
        f"self={view.self_call_count[member]}; "
        f"out={render_agg(tuple(sorted(out_agg.items())))}; "
        f"in={render_agg(tuple(sorted(in_agg.items())))}"
    )


def collision_catalog(case: Case, gt: GroundTruth, mode: CGWLMode, history, view, roles):
    final_colors = history[-1]
    origin_of = gt.origin_of()

    cluster_members: dict[str, list[str]] = {}
    for node in case.nodes:
        if node.scored:
            cluster_members.setdefault(final_colors[node.id], []).append(node.id)

    names = cluster_names(final_colors, cluster_members)
    rows = []

    for color, members in sorted(
        cluster_members.items(),
        key=lambda item: (sorted(item[1])[0], len(item[1])),
    ):
        origins = tuple(sorted({origin_of[member] for member in members}))
        if len(origins) < 2:
            continue

        injected, collision_type, interpretation = MANUAL_ANNOTATIONS.get(
            (case.case, case.build, origins),
            (
                "TODO(researcher annotation)",
                "different-origin same-relation",
                "TODO(researcher annotation)",
            ),
        )
        rows.append({
            "case": case.case,
            "build": case.build,
            "mode": mode,
            "relation_pattern": fixpoint_signature(
                members[0],
                final_colors,
                view,
                roles,
                names,
            ),
            "source_origins_involved": ";".join(origins),
            "injected_control": injected,
            "collision_type": collision_type,
            "interpretation": interpretation,
        })

    return rows


# -------------------------------------------------------------- text sections

def round_partitions(case: Case, gt: GroundTruth, history):
    origin_of = gt.origin_of()
    lines = []
    prev_split = {}

    for round_index, colors in enumerate(history):
        groups = {}
        for node in case.nodes:
            if node.scored:
                groups.setdefault(colors[node.id], []).append(origin_of[node.id])

        rendered = []
        for members in sorted(groups.values(), key=lambda group: (-len(group), sorted(group))):
            counts = {}
            for origin in members:
                counts[origin] = counts.get(origin, 0) + 1
            rendered.append("{" + ", ".join(
                f"{origin}x{count}" if count > 1 else origin
                for origin, count in sorted(counts.items())
            ) + "}")

        split_now = []
        for group in gt.origins:
            n_colors = len({colors[member] for member in group.members})
            if n_colors > prev_split.get(group.origin, 1):
                split_now.append(group.origin)
            prev_split[group.origin] = n_colors

        note = ""
        if round_index > 0 and split_now:
            note = "   <- split this round: " + ", ".join(split_now)
        lines.append(
            f"round {round_index}: {len(groups)} classes  "
            + "  ".join(rendered)
            + note
        )

    return lines


def case_summary(case: Case, gt: GroundTruth, mode: CGWLMode, history, census):
    origin_of = gt.origin_of()
    scored_ids = [node.id for node in case.nodes if node.scored]
    final_colors = history[-1]
    tp, fp, fn, _tn = pairwise_counts(
        {node_id: final_colors[node_id] for node_id in scored_ids},
        origin_of,
        scored_ids,
    )
    precision, recall, f1 = prf(tp, fp, fn)

    lines = [
        f"mode={mode}",
        f"conditional grouping recall (surviving instances): TP={tp} FN={fn} -> {recall:.2f}",
        f"pairwise precision: TP={tp} FP={fp} -> {precision:.2f} (F1={f1:.2f})",
    ]

    if census:
        expected_pairs = sum(
            entry.k_ref * (entry.k_ref - 1) // 2
            for entry in census.values()
        )
        coverage = tp / expected_pairs if expected_pairs else float("nan")
        sources = sorted({entry.census_source for entry in census.values()})
        lines.append(
            "source-level family coverage "
            f"(census={'; '.join(sources)}): TP={tp} / expected_pairs={expected_pairs} -> {coverage:.2f}"
        )
        lines.append(
            "coverage combines compile-time survival and grouping; it is not pure grouping recall."
        )
    else:
        lines.append("source-level family coverage: unavailable (no census)")

    return lines


def case_intro(case: Case, gt: GroundTruth, view, roles, census):
    rows = case_origin_rows(case, gt, view, roles, census)
    return [
        "### step 0 - expansion",
        "",
        f"- case/build: `{case.case}`/{case.build}",
        f"- scored user functions: {sum(1 for node in case.nodes if node.scored)}",
        f"- anchors: {sum(1 for node in case.nodes if node.type == 'anchor')}",
        "",
        "#### origins and anchors",
        "",
        as_markdown(rows, CASE_ORIGIN_HEADERS),
        "",
    ]


# -------------------------------------------------------------------- census

def census_for_case(case_name: str, build: str) -> dict[str, CensusEntry]:
    if (case_name, build) == ("family_graph_01", "O3S"):
        return dict(FG01_SOURCE_CENSUS)

    ref = GT_CENSUS_JOBS.get((case_name, build))
    if ref is None:
        return {}

    ref_case, ref_build, source = ref
    ref_gt = load_ground_truth(resolve_gt_json(ref_case, ref_build))
    return {
        group.origin: CensusEntry(len(group.members), source)
        for group in ref_gt.origins
    }


# ---------------------------------------------------------------- case runner

@dataclass(frozen=True)
class CaseMeasurement:
    case: Case
    gt: GroundTruth
    mode: CGWLMode
    family_rows: list[dict[str, object]]
    depth_rows: list[dict[str, object]]
    catalog_rows: list[dict[str, object]]
    round_lines: list[str]
    summary_lines: list[str]


def run_case_mode(stem: str, build: str, mode: CGWLMode) -> CaseMeasurement:
    case_name, build = split_case_build(stem, build)
    case = load_case(resolve_fixture_json(case_name, build))
    gt = load_ground_truth(resolve_gt_json(case_name, build))
    census = census_for_case(case.case, case.build)

    view, history = color_history(case, mode=mode)
    roles = anchor_roles(case, view)
    patterns = origin_pattern_summary(case, gt, view, roles)

    fam = family_rows(case, gt, mode, history, patterns, census)
    curve = depth_curve(case, gt, mode, history)
    catalog = collision_catalog(case, gt, mode, history, view, roles)
    rounds = round_partitions(case, gt, history)
    summary = case_summary(case, gt, mode, history, census)

    report = score_case(resolve_fixture_json(case_name, build), resolve_gt_json(case_name, build), mode=mode)
    scored_ids = [node.id for node in case.nodes if node.scored]
    tp, fp, fn, _tn = pairwise_counts(
        {node_id: history[-1][node_id] for node_id in scored_ids},
        gt.origin_of(),
        scored_ids,
    )
    assert (tp, fp, fn) == (
        report.pairwise.tp,
        report.pairwise.fp,
        report.pairwise.fn,
    )

    return CaseMeasurement(case, gt, mode, fam, curve, catalog, rounds, summary)


def run_case_all_modes(stem: str, build: str, modes: Iterable[CGWLMode]):
    case_name, build = split_case_build(stem, build)
    base_case = load_case(resolve_fixture_json(case_name, build))
    base_gt = load_ground_truth(resolve_gt_json(case_name, build))
    base_view = build_relation_graph_view(base_case)
    roles = anchor_roles(base_case, base_view)
    census = census_for_case(base_case.case, base_case.build)

    sections = case_intro(base_case, base_gt, base_view, roles, census)
    measurements = []

    for mode in modes:
        result = run_case_mode(stem, build, mode)
        measurements.append(result)
        sections.extend([
            f"### step 1 - refinement ({mode})",
            "",
            "#### round partitions",
            "",
            "```text",
            *result.round_lines,
            "```",
            "",
            "#### family consistency table",
            "",
            as_markdown(result.family_rows, FAMILY_HEADERS),
            "",
            "#### refinement depth diagnostic",
            "",
            as_markdown(result.depth_rows, CURVE_HEADERS),
            "",
        ])
        if result.catalog_rows:
            sections.extend([
                "#### collision catalog",
                "",
                as_markdown(result.catalog_rows, CATALOG_HEADERS),
                "",
            ])
        sections.extend([
            "### step 2 - interpretation",
            "",
            "```text",
            *result.summary_lines,
            "```",
            "",
        ])

    return base_case, "\n".join(sections), measurements


# ----------------------------------------------------------------------- CLI

def parse_job(value: str) -> tuple[str, str]:
    return split_case_build(value, None)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate family/origin-level measurement reports."
    )
    parser.add_argument(
        "jobs",
        nargs="*",
        help="case stem, optionally with .BUILD suffix. Default: current family_graph cases.",
    )
    parser.add_argument(
        "--build",
        default=None,
        help=f"build for positional jobs without suffix. Default: {DEFAULT_BUILD}",
    )
    parser.add_argument(
        "--mode",
        choices=CG_WL_MODES,
        action="append",
        help="mode to include. May be repeated. Default: all modes.",
    )
    parser.add_argument(
        "--out-dir",
        default="reports",
        help="output directory. Default: reports",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="also print the Markdown report to stdout",
    )
    return parser


def requested_jobs(args) -> list[tuple[str, str]]:
    if not args.jobs:
        return list(DEFAULT_JOBS)

    jobs = []
    for value in args.jobs:
        case, build = split_case_build(value, args.build)
        jobs.append((case, build))
    return jobs


def write_csv(path: Path, rows: list[dict[str, object]], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    modes = tuple(args.mode or CG_WL_MODES)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_family_rows = []
    all_depth_rows = []
    all_catalog_rows = []
    markdown = [
        "# Family-level measurement",
        "",
        "This report follows the expansion -> refinement -> interpretation shape.",
        "Origin annotations are score-side measurement labels; the CG-WL engine never reads them.",
        "",
    ]

    for stem, build in requested_jobs(args):
        case, body, measurements = run_case_all_modes(stem, build, modes)
        markdown.extend([
            f"## {case.case} / {case.build}",
            "",
            body,
            "",
        ])
        for measurement in measurements:
            all_family_rows.extend(measurement.family_rows)
            all_depth_rows.extend(measurement.depth_rows)
            all_catalog_rows.extend(measurement.catalog_rows)

    text = "\n".join(markdown)
    report_path = out_dir / "family_measurement.md"
    report_path.write_text(text, encoding="utf-8")

    write_csv(out_dir / "family_consistency.csv", all_family_rows, FAMILY_HEADERS)
    write_csv(out_dir / "depth_curve.csv", all_depth_rows, CURVE_HEADERS)
    write_csv(out_dir / "collision_catalog.csv", all_catalog_rows, CATALOG_HEADERS)

    if args.print:
        print(text)
    else:
        print(f"wrote {report_path}")
        print(f"wrote {out_dir / 'family_consistency.csv'}")
        print(f"wrote {out_dir / 'depth_curve.csv'}")
        print(f"wrote {out_dir / 'collision_catalog.csv'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
