from __future__ import annotations

import sys

from engine import run_cg_wl
from loader import load_case


DEFAULT_FIXTURE = "./fixtures/fg01.fixture.json"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    fixture_path = args[0] if args else DEFAULT_FIXTURE

    case = load_case(fixture_path)
    result = run_cg_wl(case)

    print(result.rounds)
    print(result.clusters)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
