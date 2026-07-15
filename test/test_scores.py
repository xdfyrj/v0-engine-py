# Exact V0 baseline regression for the four canonical builds.

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_manifest import load_and_verify_manifest, sha256_file
from paths import build_manifest_for, fixture_json_for, gt_json_for
from scores import (
    load_ground_truth,
    reports_to_dict,
    score_case,
    score_v0_baseline,
)


CASES = [
    {
        "case": "family_graph_01",
        "build": "O3S",
        "source_sha256": "09fb7950f565fb81ab9bb980270bc8b15ec39e538bca7d6d1ae7b704a9721a6c",
        "gt_sha256": "2e711d8d71a0b4a7289b0af3996ee66aa47d20908c7eed193ba728326df7ba36",
        "fixture_sha256": "a90ab8a65b2e826359060f1bd3306a8dff0e2a3a0a0f71f4e3babc53c61a1248",
        "origin_sizes": {"shared_recursive": 3, "process": 3},
        "rounds": 1,
        "counts": (6, 0, 0, 9),
        "metrics": (1.00, 1.00, 1.00, 1.00),
        "clusters": (
            ("FUN_00113e20", "FUN_00113f00", "FUN_00113f80"),
            ("FUN_00114460", "FUN_00114640", "FUN_00114880"),
        ),
        "origin_scores": {
            "shared_recursive": (3, 1, 3, 3, ()),
            "process": (3, 1, 3, 3, ()),
        },
    },
    {
        "case": "family_graph_02",
        "build": "O3S",
        "source_sha256": "ee46b32e80732e0226b3f443d3aac63d712bf1e19c625b155beb14098f7d60e6",
        "gt_sha256": "41f5d14d4f2901ddc2477ee721aef780cfbe575427ac994e2a1dc9cbea7830fe",
        "fixture_sha256": "5b0a52d43cf71abe089ef29cc1047dca705b1bfcc1921ee94648f444afac88e5",
        "origin_sizes": {
            "process_beta": 2,
            "recurse_beta": 2,
            "process_alpha": 2,
            "recurse_alpha": 2,
            "c_process_alpha_i32": 1,
            "c_recurse_alpha_i32": 1,
            "c_process_alpha_wide": 1,
            "c_recurse_alpha_wide": 1,
        },
        "rounds": 2,
        "counts": (4, 10, 0, 52),
        "metrics": (0.29, 1.00, 0.44, 0.39),
        "clusters": (
            ("FUN_00113fd0", "FUN_001140f0"),
            ("FUN_00114350", "FUN_001144d0"),
            ("FUN_00114590", "FUN_001147f0", "FUN_00114ac0", "FUN_00114c70"),
            ("FUN_00114910", "FUN_001149a0", "FUN_00114be0", "FUN_00114ee0"),
        ),
        "origin_scores": {
            "process_beta": (2, 1, 1, 1, ()),
            "recurse_beta": (2, 1, 1, 1, ()),
            "process_alpha": (
                2, 1, 1, 1,
                ("c_process_alpha_i32", "c_process_alpha_wide"),
            ),
            "recurse_alpha": (
                2, 1, 1, 1,
                ("c_recurse_alpha_i32", "c_recurse_alpha_wide"),
            ),
            "c_process_alpha_i32": (
                1, 1, 0, 0,
                ("c_process_alpha_wide", "process_alpha"),
            ),
            "c_recurse_alpha_i32": (
                1, 1, 0, 0,
                ("c_recurse_alpha_wide", "recurse_alpha"),
            ),
            "c_process_alpha_wide": (
                1, 1, 0, 0,
                ("c_process_alpha_i32", "process_alpha"),
            ),
            "c_recurse_alpha_wide": (
                1, 1, 0, 0,
                ("c_recurse_alpha_i32", "recurse_alpha"),
            ),
        },
    },
    {
        "case": "family_graph_03",
        "build": "O3S",
        "source_sha256": "f619cb2cf6b96756592c955895dcef822081333d42c018fc5b9c5f7e204a8d4e",
        "gt_sha256": "2060d5ff413141c149a0aae9cd1e509b66ff0475fc1fa2f422fac6eae8c876ed",
        "fixture_sha256": "b7dae1bd03e32904261af87f01fe6a0e0f09f37c5e050dd9db6be848b2be7d04",
        "origin_sizes": {
            "share": 3,
            "leaf_p": 2,
            "decoy_a": 1,
            "decoy_b": 1,
            "drive_x": 3,
            "drive_y": 3,
        },
        "rounds": 2,
        "counts": (4, 1, 6, 67),
        "metrics": (0.80, 0.40, 0.53, 0.49),
        "clusters": (
            ("FUN_00114690", "FUN_00114a10"),
            ("FUN_00114d70",),
            ("FUN_00115260", "FUN_001154d0"),
            ("FUN_001156e0", "FUN_001157e0"),
            ("FUN_00115960", "FUN_00115bb0"),
            ("FUN_00115e70",),
            ("FUN_00116000", "FUN_00116330"),
            ("FUN_00116590",),
        ),
        "origin_scores": {
            "share": (3, 2, 1, 3, ()),
            "leaf_p": (2, 1, 1, 1, ()),
            "decoy_a": (1, 1, 0, 0, ("decoy_b",)),
            "decoy_b": (1, 1, 0, 0, ("decoy_a",)),
            "drive_x": (3, 2, 1, 3, ()),
            "drive_y": (3, 2, 1, 3, ()),
        },
    },
    {
        "case": "family_graph_03",
        "build": "O3KS",
        "source_sha256": "f619cb2cf6b96756592c955895dcef822081333d42c018fc5b9c5f7e204a8d4e",
        "gt_sha256": "f4db880c136e319c8fa4f3368e94fd473be1c07c27cb881b45e2dd8ee030a8a0",
        "fixture_sha256": "eef1d556460cf8fe98d77348a113b152f8a70e7ccfeb49532d2662895a19dfd9",
        "origin_sizes": {
            "share": 3,
            "leaf_p": 3,
            "leaf_q": 3,
            "decoy_a": 1,
            "decoy_b": 1,
            "drive_x": 3,
            "drive_y": 3,
        },
        "rounds": 2,
        "counts": (15, 1, 0, 120),
        "metrics": (0.94, 1.00, 0.97, 0.96),
        "clusters": (
            ("FUN_00114720", "FUN_001148e0", "FUN_00114a30"),
            ("FUN_00114b20", "FUN_00114d90", "FUN_00114ef0"),
            ("FUN_00115100", "FUN_00115250", "FUN_00115440"),
            ("FUN_00115680", "FUN_00115780"),
            ("FUN_00115900", "FUN_00115b50", "FUN_00115e10"),
            ("FUN_00115fa0", "FUN_001162d0", "FUN_00116530"),
        ),
        "origin_scores": {
            "share": (3, 1, 3, 3, ()),
            "leaf_p": (3, 1, 3, 3, ()),
            "leaf_q": (3, 1, 3, 3, ()),
            "decoy_a": (1, 1, 0, 0, ("decoy_b",)),
            "decoy_b": (1, 1, 0, 0, ("decoy_a",)),
            "drive_x": (3, 1, 3, 3, ()),
            "drive_y": (3, 1, 3, 3, ()),
        },
    },
]


def main() -> int:
    all_ok = True

    for expected in CASES:
        case = expected["case"]
        build = expected["build"]
        verified = load_and_verify_manifest(
            build_manifest_for(case, build),
            expected_case=case,
            expected_build=build,
        )
        report = score_case(fixture_json_for(case, build), gt_json_for(case, build))
        gt = load_ground_truth(gt_json_for(case, build))

        origin_sizes = {group.origin: len(group.members) for group in gt.origins}
        counts = (
            report.pairwise.tp,
            report.pairwise.fp,
            report.pairwise.fn,
            report.pairwise.tn,
        )
        metrics = tuple(round(value, 2) for value in (
            report.pairwise.precision,
            report.pairwise.recall,
            report.pairwise.f1,
            report.pairwise.ari,
        ))
        clusters = tuple(cluster.member_ids for cluster in report.clusters)
        origin_scores = {
            row.origin: (
                row.k_obs,
                row.predicted_cluster_count,
                row.recovered_pairs,
                row.total_pairs,
                row.colliding_origins,
            )
            for row in report.origins
        }

        checks = {
            "source hash": sha256_file(verified.source) == expected["source_sha256"],
            "GT binary hash": sha256_file(verified.non_stripped_binary) == expected["gt_sha256"],
            "fixture binary hash": sha256_file(verified.stripped_binary) == expected["fixture_sha256"],
            "origin census": origin_sizes == expected["origin_sizes"],
            "candidate count": report.candidate_count == sum(expected["origin_sizes"].values()),
            "rounds": report.rounds == expected["rounds"],
            "pair counts": counts == expected["counts"],
            "pair total": report.pair_count == sum(counts),
            "metrics": metrics == expected["metrics"],
            "clusters": clusters == expected["clusters"],
            "origin scores": origin_scores == expected["origin_scores"],
        }
        failed = [name for name, ok in checks.items() if not ok]
        ok = not failed
        all_ok = all_ok and ok
        tag = "PASS" if ok else f"FAIL ({', '.join(failed)})"
        print(
            f"{case}/{build}: n={report.candidate_count} TP={counts[0]} FP={counts[1]} "
            f"FN={counts[2]} TN={counts[3]} PR={metrics[0]:.2f} "
            f"RE={metrics[1]:.2f} F1={metrics[2]:.2f} ARI={metrics[3]:.2f} {tag}"
        )

    baseline_path = Path(__file__).resolve().parents[1] / "results" / "v0_baseline.json"
    stored_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    generated_baseline = reports_to_dict(score_v0_baseline())
    baseline_ok = stored_baseline == generated_baseline
    all_ok = all_ok and baseline_ok
    print(f"baseline score JSON: {'PASS' if baseline_ok else 'FAIL'}")
    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
