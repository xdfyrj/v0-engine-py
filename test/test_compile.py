import os
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compile import (
    COMPILED_PROFILE_BY_BUILD,
    PROFILE_FLAGS,
    RUSTC_EDITION,
    STRIP_FLAGS,
    build_info_path_for,
    compile_case,
    compiled_profile_for_build,
    derive_fixture_binary,
    rustc_command,
)


# Exact flag strings from rust-loss scripts/lib_build.sh profile_flags().
# The corpus provenance depends on these staying byte-identical.
RUST_LOSS_O3_FLAGS = (
    "-C opt-level=3 -C codegen-units=1 -C lto=off -C panic=unwind "
    "-C debuginfo=0 -C debug-assertions=off -C overflow-checks=off"
)
RUST_LOSS_O3K_FLAGS = RUST_LOSS_O3_FLAGS + " --cfg keep"


def main() -> int:
    if " ".join(PROFILE_FLAGS["O3"]) != RUST_LOSS_O3_FLAGS:
        print(
            f"FAIL O3 flags diverged from rust-loss: {' '.join(PROFILE_FLAGS['O3'])}"
        )
        return 1

    if " ".join(PROFILE_FLAGS["O3K"]) != RUST_LOSS_O3K_FLAGS:
        print(
            f"FAIL O3K flags diverged from rust-loss: {' '.join(PROFILE_FLAGS['O3K'])}"
        )
        return 1

    if RUSTC_EDITION != "2024":
        print(f"FAIL edition diverged from rust-loss: {RUSTC_EDITION}")
        return 1

    if STRIP_FLAGS != ["--strip-all"]:
        print(f"FAIL strip flags diverged from rust-loss: {STRIP_FLAGS}")
        return 1

    if COMPILED_PROFILE_BY_BUILD != {"O3S": "O3", "O3KS": "O3K"}:
        print(f"FAIL build->profile mapping: {COMPILED_PROFILE_BY_BUILD}")
        return 1

    for build, expected_profile in COMPILED_PROFILE_BY_BUILD.items():
        got = compiled_profile_for_build(build)
        if got != expected_profile:
            print(f"FAIL profile for {build}: expected {expected_profile}, got {got}")
            return 1

    try:
        compiled_profile_for_build("O0")
    except ValueError as exc:
        if "unsupported build" not in str(exc):
            print(f"FAIL unexpected unsupported-build error: {exc}")
            return 1
    else:
        print("FAIL O0 has no stripped evaluation pair and must be rejected")
        return 1

    command = rustc_command(
        source="src/family_graph_03.rs",
        case="family_graph_03",
        profile="O3K",
        output="gt_bin/family_graph_03.O3KS.gt.bin",
    )
    expected_command = [
        "rustc",
        "src/family_graph_03.rs",
        *PROFILE_FLAGS["O3K"],
        "--crate-type", "bin",
        "--crate-name", "family_graph_03",
        "--edition", "2024",
        "--emit=link",
        "-o", "gt_bin/family_graph_03.O3KS.gt.bin",
    ]
    if command != expected_command:
        print(f"FAIL expected rustc command {expected_command}, got {command}")
        return 1

    info_paths = {
        "gt_bin/family_graph_03.O3KS.gt.bin": (
            "gt_bin/family_graph_03.O3KS.gt.build_info.txt"
        ),
        "bin/family_graph_03.O3KS.fixture.bin": (
            "bin/family_graph_03.O3KS.fixture.build_info.txt"
        ),
    }
    for binary_path, expected_info in info_paths.items():
        got = build_info_path_for(binary_path)
        if got != expected_info:
            print(f"FAIL expected build info path {expected_info}, got {got}")
            return 1

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        gt_binary = root / "case.gt.bin"
        fixture_binary = root / "case.fixture.bin"
        source = root / "case.rs"
        source.write_text("fn main() {}\n", encoding="utf-8")
        gt_binary.write_bytes(b"symbol-bearing binary")
        gt_binary.chmod(0o755)
        fixture_binary.write_bytes(b"previous fixture")

        with patch("compile._run_tool", side_effect=RuntimeError("strip failed")):
            try:
                derive_fixture_binary(
                    gt_binary=str(gt_binary),
                    output=str(fixture_binary),
                    strip_tool="strip",
                )
            except RuntimeError:
                pass
            else:
                print("FAIL strip failure was not propagated")
                return 1

        if fixture_binary.read_bytes() != b"previous fixture":
            print("FAIL strip failure replaced the previous fixture")
            return 1

        with patch("compile._run_tool"):
            derive_fixture_binary(
                gt_binary=str(gt_binary),
                output=str(fixture_binary),
                strip_tool="strip",
            )

        if fixture_binary.read_bytes() != b"symbol-bearing binary":
            print("FAIL successful fixture derivation produced wrong contents")
            return 1
        if fixture_binary.stat().st_mode & 0o777 != 0o755:
            print("FAIL fixture derivation did not preserve executable mode")
            return 1

        fixture_binary.write_bytes(b"previous fixture")

        args = Namespace(
            source=str(source),
            case="case",
            build="O3S",
            gt_binary=str(gt_binary),
            fixture_binary=str(fixture_binary),
            rustc_tool=sys.executable,
            strip_tool="definitely-missing-strip-for-test",
        )
        try:
            compile_case(args)
        except RuntimeError as exc:
            if "definitely-missing-strip-for-test" not in str(exc):
                print(f"FAIL unexpected missing-tool error: {exc}")
                return 1
        else:
            print("FAIL missing strip tool was not rejected")
            return 1

        if gt_binary.read_bytes() != b"symbol-bearing binary":
            print("FAIL tool preflight modified the GT binary")
            return 1
        if fixture_binary.read_bytes() != b"previous fixture":
            print("FAIL tool preflight modified the fixture binary")
            return 1

    print("compile profile flags, command assembly, and failure safety PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
