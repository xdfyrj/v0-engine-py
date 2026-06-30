# test/test_scores.py
#
# baseline 회귀: 네 사례의 (P, R, F1, ARI)가 compiler-derived auto-GT
# 기준으로 고정되는지 확인한다.
# 기준값:
#   family_graph_01 O3S   P=1.00 R=1.00 F1=1.00 ARI=1.00
#   family_graph_02 O3S   P=0.29 R=1.00 F1=0.44 ARI=0.39
#   family_graph_03 O3KS  P=0.94 R=1.00 F1=0.97 ARI=0.96
#   family_graph_03 O3S   P=0.80 R=0.40 F1=0.53 ARI=0.49

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scores import score_case

CASES = [
    ("fixtures/family_graph_01.O3S.fixture.json",  "ground_truth/family_graph_01.O3S.gt.json",  (1.00, 1.00, 1.00, 1.00)),
    ("fixtures/family_graph_02.O3S.fixture.json",  "ground_truth/family_graph_02.O3S.gt.json",  (0.29, 1.00, 0.44, 0.39)),
    ("fixtures/family_graph_03.O3KS.fixture.json", "ground_truth/family_graph_03.O3KS.gt.json", (0.94, 1.00, 0.97, 0.96)),
    ("fixtures/family_graph_03.O3S.fixture.json",  "ground_truth/family_graph_03.O3S.gt.json",  (0.80, 0.40, 0.53, 0.49)),
]


def main() -> int:
    all_ok = True
    for fixture, gt, expected in CASES:
        p = score_case(fixture, gt).pairwise
        got = (round(p.precision, 2), round(p.recall, 2),
               round(p.f1, 2), round(p.ari, 2))
        ok = got == expected
        all_ok = all_ok and ok
        tag = "PASS" if ok else f"FAIL (expected {expected})"
        print(f"{fixture:28s} P={got[0]:.2f} R={got[1]:.2f} "
              f"F1={got[2]:.2f} ARI={got[3]:.2f}  {tag}")
    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
