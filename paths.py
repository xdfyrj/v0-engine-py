from __future__ import annotations

import re
from pathlib import Path


DEFAULT_BUILD = "O3S"


def normalize_build(build: str | None) -> str:
    return (build or DEFAULT_BUILD).upper()


def strip_known_suffix(value: str, suffixes: tuple[str, ...]) -> str:
    name = Path(value).name
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def split_case_build(
    value: str,
    build: str | None = None,
    *,
    suffixes: tuple[str, ...] = (
        ".fixture.bin",
        ".gt.bin",
        ".fixture.json",
        ".gt.json",
        ".users.json",
        ".bin",
        ".json",
        ".rs",
    ),
) -> tuple[str, str]:
    stem = strip_known_suffix(value, suffixes)

    # Compatibility for the old control-build stem. The canonical interface is
    # now `family_graph_03 --build O3KS`, not `family_graph_03K`.
    legacy_keep = re.fullmatch(r"(family_graph_\d+)K", stem)
    if build is None and legacy_keep:
        return legacy_keep.group(1), "O3KS"

    if build is None and "." in stem:
        maybe_case, maybe_build = stem.rsplit(".", 1)
        if re.fullmatch(r"O\d+[A-Z]*", maybe_build.upper()):
            return maybe_case, maybe_build.upper()

    return stem, normalize_build(build)


def output_stem(case: str, build: str) -> str:
    return f"{case}.{normalize_build(build)}"


def prefix_for_case(case: str) -> str:
    return f"{case}::"


def first_existing(options: list[str]) -> str:
    for path in options:
        if Path(path).exists():
            return path
    return options[0]


def _legacy_input_stems(case: str, build: str) -> list[str]:
    build = normalize_build(build)
    stems: list[str] = []

    if build == "O3S":
        stems.append(case)

    if build in {"O3K", "O3KS"}:
        stems.append(f"{case}K")

    return stems


def source_rs_for(case: str) -> str:
    return f"src/{case}.rs"


def fixture_binary_for(case: str, build: str) -> str:
    return f"bin/{output_stem(case, build)}.fixture.bin"


def gt_binary_for(case: str, build: str) -> str:
    return f"gt_bin/{output_stem(case, build)}.gt.bin"


def build_manifest_for(case: str, build: str) -> str:
    return f"build_info/{output_stem(case, build)}.json"


def resolve_fixture_binary(case: str, build: str) -> str:
    stem = output_stem(case, build)
    options = [
        f"bin/{stem}.fixture.bin",
        f"bin/{stem}.bin",
    ]
    for legacy_stem in _legacy_input_stems(case, build):
        options.extend([
            f"bin/{legacy_stem}.fixture.bin",
            f"bin/{legacy_stem}.bin",
        ])
    return first_existing(options)


def resolve_gt_binary(case: str, build: str) -> str:
    options = [gt_binary_for(case, build)]
    for legacy_stem in _legacy_input_stems(case, build):
        options.append(f"gt_bin/{legacy_stem}.gt.bin")
    return first_existing(options)


def fixture_json_for(case: str, build: str) -> str:
    return f"fixtures/{output_stem(case, build)}.fixture.json"


def gt_json_for(case: str, build: str) -> str:
    return f"ground_truth/{output_stem(case, build)}.gt.json"


def users_json_for(case: str, build: str) -> str:
    return f"users/{output_stem(case, build)}.users.json"


def resolve_fixture_json(case: str, build: str) -> str:
    options = [fixture_json_for(case, build)]
    for legacy_stem in _legacy_input_stems(case, build):
        options.append(f"fixtures/{legacy_stem}.fixture.json")
    return first_existing(options)


def resolve_gt_json(case: str, build: str) -> str:
    options = [gt_json_for(case, build)]
    for legacy_stem in _legacy_input_stems(case, build):
        options.append(f"ground_truth/{legacy_stem}.gt.json")
    return first_existing(options)


def resolve_users_json(case: str, build: str) -> str:
    return first_existing([users_json_for(case, build)])
