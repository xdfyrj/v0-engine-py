import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import _neighbor_color_multiset


def main() -> int:
    prev_colors = {
        "callee_a": "C:leaf",
        "callee_b": "C:leaf",
        "callee_c": "C:other",
    }
    edges = [
        ("callee_a", 1),
        ("callee_b", 2),
        ("callee_c", 4),
    ]

    expected = (
        ("C:leaf", 3),
        ("C:other", 4),
    )
    got = _neighbor_color_multiset(edges, prev_colors)

    if got != expected:
        print(f"FAIL expected {expected}, got {got}")
        return 1

    print("neighbor color multiset aggregation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
