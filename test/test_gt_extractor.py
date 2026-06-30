import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gt_extractor import (
    make_ground_truth,
    make_users_json,
    parse_nm_lines,
    user_addresses,
)


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
    )

    expected = {
        "case": "fg02",
        "build": "O3S",
        "schema_version": 2,
        "origins": [
            {
                "origin": "process_beta",
                "members": ["FUN_00114000", "FUN_00114120"],
            },
            {
                "origin": "c_process_alpha_i32",
                "members": ["FUN_00114af0"],
            },
            {
                "origin": "decoy_alpha",
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

    alias_symbols = parse_nm_lines([
        "0000000000014000 t family_graph_02::first_origin",
        "0000000000014000 t family_graph_02::second_origin",
    ])
    try:
        make_ground_truth(
            symbols=alias_symbols,
            case="fg02",
            build="O3S",
            prefix="family_graph_02::",
            id_bias=0x100000,
        )
    except ValueError as exc:
        if "cross-origin address alias" not in str(exc):
            print(f"FAIL unexpected cross-origin alias error: {exc}")
            return 1
    else:
        print("FAIL cross-origin address alias should stop GT generation")
        return 1

    addresses = user_addresses(symbols=symbols, prefix="family_graph_02::")
    expected_addresses = [0x14000, 0x14120, 0x14AF0, 0x14C10]
    if addresses != expected_addresses:
        print(f"FAIL expected user addresses {expected_addresses}, got {addresses}")
        return 1

    users_json = make_users_json(
        addresses=addresses,
        case="fg02",
        build="O3S",
        binary_path="gt_bin/family_graph_02.gt.bin",
        prefix="family_graph_02::",
    )
    expected_users_json = {
        "case": "fg02",
        "build": "O3S",
        "schema_version": 1,
        "source": "gt_bin/family_graph_02.gt.bin",
        "prefix": "family_graph_02::",
        "addresses": ["0x14000", "0x14120", "0x14af0", "0x14c10"],
    }
    if users_json != expected_users_json:
        print(f"FAIL expected users JSON {expected_users_json}, got {users_json}")
        return 1

    print("ground truth extractor symbol grouping PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
