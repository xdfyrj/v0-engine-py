import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gt_extractor import make_ground_truth, parse_nm_lines


def main() -> int:
    symbols = parse_nm_lines([
        "0000000000014000 t family_graph_02::process_beta",
        "0000000000014120 t family_graph_02::process_beta::<i32>",
        "0000000000014af0 t family_graph_02::c_process_alpha_i32",
        "0000000000014af0 t family_graph_02::c_process_alpha_i32::<u64>",
        "0000000000014c10 t family_graph_02::decoy_alpha",
        "0000000000015030 t family_graph_02::main",
        "0000000000099999 t core::fmt::something",
    ])

    gt = make_ground_truth(
        symbols=symbols,
        case="fg02",
        build="O3S",
        prefix="family_graph_02::",
        id_bias=0x100000,
        concrete_regex=r"^(c_|decoy_)",
    )

    expected = {
        "case": "fg02",
        "build": "O3S",
        "schema_version": 1,
        "origins": [
            {
                "origin": "process_beta",
                "type": "generic",
                "members": ["FUN_00114000", "FUN_00114120"],
            },
            {
                "origin": "c_process_alpha_i32",
                "type": "concrete",
                "members": ["FUN_00114af0"],
            },
            {
                "origin": "decoy_alpha",
                "type": "concrete",
                "members": ["FUN_00114c10"],
            },
        ],
        "note": (
            "address aliases/duplicates: FUN_00114af0: duplicate symbol "
            "for origin 'c_process_alpha_i32' kept once "
            "(family_graph_02::c_process_alpha_i32::<u64>)"
        ),
    }

    if gt != expected:
        print(f"FAIL expected {expected}, got {gt}")
        return 1

    print("ground truth extractor symbol grouping PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
