from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import r2pipe


SCHEMA_VERSION = 1
DEFAULT_ID_BIAS = 0x100000


@dataclass(frozen=True)
class R2Function:
    addr: int
    name: str
    size: int
    kind: str


def function_id(addr: int, *, id_bias: int = 0) -> str:
    return f"FUN_{addr + id_bias:08x}"


def parse_int(value: str) -> int:
    return int(value, 0)


def is_probably_import(func: R2Function) -> bool:
    return func.name.startswith("sym.imp.") or func.kind == "sym"


class BinaryExtractor:
    def __init__(
        self,
        binary_path: str,
        *,
        include_imports: bool = False,
        id_bias: int = DEFAULT_ID_BIAS,
    ) -> None:
        self.binary_path = binary_path
        self.include_imports = include_imports
        self.id_bias = id_bias
        self.r2 = r2pipe.open(binary_path, flags=["-2"])
        self.functions: list[R2Function] = []
        self.by_addr: dict[int, R2Function] = {}
        self._call_cache: dict[int, Counter[int]] = {}

    def close(self) -> None:
        self.r2.quit()

    def analyze(self) -> None:
        self.r2.cmd("aaa")
        self._refresh_functions()

    def _refresh_functions(self) -> None:
        raw_functions = self.r2.cmdj("aflj") or []

        functions: list[R2Function] = []
        for raw in raw_functions:
            addr = raw.get("offset")
            if not isinstance(addr, int):
                continue

            func = R2Function(
                addr=addr,
                name=str(raw.get("name") or self._function_id(addr)),
                size=int(raw.get("size") or 0),
                kind=str(raw.get("type") or ""),
            )
            if not self.include_imports and is_probably_import(func):
                continue
            functions.append(func)

        functions.sort(key=lambda f: f.addr)
        self.functions = functions
        self.by_addr = {f.addr: f for f in functions}
        self._call_cache.clear()

    def list_functions(self) -> None:
        for func in self.functions:
            print(f"{self._function_id(func.addr)}  raw={func.addr:#x}  {func.name}  size={func.size}")

    def resolve_root(self, root: str | None) -> R2Function:
        if root:
            resolved = self._resolve_function_spec(root)
            if resolved is None:
                raise ValueError(f"cannot resolve root function: {root}")
            return resolved

        for wanted in ("main", "sym.main"):
            resolved = self._resolve_function_spec(wanted)
            if resolved is not None:
                return resolved

        entry_root = self._root_from_libc_start_main()
        if entry_root is not None:
            return entry_root

        resolved = self._resolve_function_spec("entry0")
        if resolved is not None:
            return resolved

        raise ValueError(
            "cannot auto-detect main/root. Re-run with --list-functions, then pass --root."
        )

    def _resolve_function_spec(self, spec: str) -> R2Function | None:
        try:
            addr = parse_int(spec)
        except ValueError:
            addr = None

        if addr is not None:
            biased_addr = addr - self.id_bias
            return self.function_containing(addr) or self.function_containing(biased_addr)

        for func in self.functions:
            if spec in {self._function_id(func.addr), function_id(func.addr), func.name}:
                return func

        for func in self.functions:
            if func.name.endswith(spec):
                return func

        return None

    def _function_id(self, addr: int) -> str:
        return function_id(addr, id_bias=self.id_bias)

    def _root_from_libc_start_main(self) -> R2Function | None:
        entry = self._resolve_function_spec("entry0")
        if entry is None:
            return None

        wrapper_addr = self._libc_start_main_wrapper_addr(entry)
        if wrapper_addr is None:
            return None

        rust_main_addr = self._rust_main_from_start_wrapper(wrapper_addr)
        if rust_main_addr is not None:
            return self._ensure_function_at(rust_main_addr)

        return self.function_containing(wrapper_addr)

    def _libc_start_main_wrapper_addr(self, entry: R2Function) -> int | None:
        pdf = self.r2.cmdj(f"pdfj @ {entry.addr}") or {}
        last_rdi_ptr: int | None = None

        for op in pdf.get("ops") or []:
            opcode = str(op.get("opcode") or "")
            if opcode.startswith("lea rdi,") and isinstance(op.get("ptr"), int):
                last_rdi_ptr = op["ptr"]
                continue

            if "__libc_start_main" in self._op_text(op) and last_rdi_ptr is not None:
                return last_rdi_ptr

        return None

    def _rust_main_from_start_wrapper(self, wrapper_addr: int) -> int | None:
        ops = self.r2.cmdj(f"pdj 64 @ {wrapper_addr}") or []
        if isinstance(ops, dict):
            ops = ops.get("ops") or []

        pending_main_addr: int | None = None
        saw_main_pointer_store = False

        for op in ops:
            opcode = str(op.get("opcode") or "")
            op_type = str(op.get("type") or "")

            if opcode.startswith("lea rax,") and isinstance(op.get("ptr"), int):
                pending_main_addr = op["ptr"]
                saw_main_pointer_store = False
                continue

            if pending_main_addr is not None and self._stores_rax_as_lang_start_arg(op):
                saw_main_pointer_store = True
                continue

            if pending_main_addr is not None and self._is_call_op(op):
                text = self._op_text(op)
                if "lang_start_internal" in text or saw_main_pointer_store:
                    return pending_main_addr

            if op_type in {"ret", "trap"} or opcode.startswith(("ret", "hlt", "int3")):
                break

        return None

    @staticmethod
    def _stores_rax_as_lang_start_arg(op: dict[str, Any]) -> bool:
        opcode = str(op.get("opcode") or "")
        return opcode in {
            "mov qword [rsp], rax",
            "mov [rsp], rax",
        }

    @staticmethod
    def _op_text(op: dict[str, Any]) -> str:
        return f"{op.get('opcode') or ''} {op.get('disasm') or ''}"

    def _ensure_function_at(self, addr: int) -> R2Function | None:
        existing = self.by_addr.get(addr)
        if existing is not None:
            return existing

        self.r2.cmd(f"af @ {addr}")
        self._refresh_functions()

        return self.by_addr.get(addr) or self.function_containing(addr)

    def function_containing(self, addr: int) -> R2Function | None:
        if addr in self.by_addr:
            return self.by_addr[addr]

        for func in self.functions:
            if func.size <= 0:
                continue
            if func.addr <= addr < func.addr + func.size:
                return func

        return None

    def direct_calls(self, func: R2Function) -> Counter[int]:
        if func.addr in self._call_cache:
            return self._call_cache[func.addr].copy()

        counts: Counter[int] = Counter()
        pdf = self.r2.cmdj(f"pdfj @ {func.addr}") or {}

        for op in pdf.get("ops") or []:
            target_func = self._direct_call_target(func, op)
            if target_func is None:
                continue
            if not self.include_imports and is_probably_import(target_func):
                continue

            counts[target_func.addr] += 1

        self._call_cache[func.addr] = counts.copy()
        return counts

    @staticmethod
    def _is_call_op(op: dict[str, Any]) -> bool:
        op_type = str(op.get("type") or "")
        opcode = str(op.get("opcode") or "")
        return "call" in op_type or opcode.startswith("call ")

    def _direct_call_target(
        self,
        current_func: R2Function,
        op: dict[str, Any],
    ) -> R2Function | None:
        target = self._call_target(op)
        if target is None:
            return None

        if self._is_call_op(op):
            return self.function_containing(target)

        if self._is_tail_call_jump_op(op):
            # O3 often lowers `call f; ret` to `jmp f`.
            # Count it only when the jump target is exactly another function's
            # start address. This avoids ordinary in-function branches and most
            # switch/case labels that radare2 may expose as pseudo-functions.
            target_func = self.by_addr.get(target)
            if target_func is not None and target_func.addr != current_func.addr:
                return target_func

        return None

    @staticmethod
    def _is_tail_call_jump_op(op: dict[str, Any]) -> bool:
        op_type = str(op.get("type") or "")
        opcode = str(op.get("opcode") or "")
        return op_type in {"jmp", "ujmp"} or opcode.startswith("jmp ")

    @staticmethod
    def _call_target(op: dict[str, Any]) -> int | None:
        for key in ("jump", "ptr", "val"):
            value = op.get(key)
            if isinstance(value, int):
                return value
        return None

    def build_call_graph(self) -> dict[int, Counter[int]]:
        return {func.addr: self.direct_calls(func) for func in self.functions}


def select_reachable(
    graph: dict[int, Counter[int]],
    root_addr: int,
    *,
    max_depth: int | None,
) -> set[int]:
    selected: set[int] = {root_addr}
    queue: deque[tuple[int, int]] = deque([(root_addr, 0)])

    while queue:
        addr, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue

        for target in graph.get(addr, {}):
            if target in selected:
                continue
            selected.add(target)
            queue.append((target, depth + 1))

    return selected


def apply_exclude_filters(
    selected: set[int],
    functions: dict[int, R2Function],
    exclude_patterns: list[str],
    *,
    root_addr: int,
    id_bias: int,
) -> set[int]:
    if not exclude_patterns:
        return selected

    regexes = [re.compile(pattern) for pattern in exclude_patterns]
    kept: set[int] = set()

    for addr in selected:
        func = functions[addr]
        haystack = (
            f"{function_id(func.addr)} "
            f"{function_id(func.addr, id_bias=id_bias)} "
            f"{func.name} {func.addr:#x}"
        )
        if addr != root_addr and any(regex.search(haystack) for regex in regexes):
            continue
        kept.add(addr)

    return kept


def make_fixture_json(
    *,
    case: str,
    build: str,
    binary_path: str,
    root: R2Function,
    functions: dict[int, R2Function],
    graph: dict[int, Counter[int]],
    selected: set[int],
    score_root: bool,
    max_depth: int | None,
    exclude_patterns: list[str],
    id_bias: int,
) -> dict[str, Any]:
    nodes = []

    for addr in sorted(selected):
        func = functions[addr]
        calls = [
            {"target": function_id(target, id_bias=id_bias), "count": count}
            for target, count in sorted(graph.get(addr, {}).items())
            if target in selected and count > 0
        ]

        is_root = addr == root.addr
        node_type = "user" if score_root or not is_root else "anchor"
        scored = node_type == "user"

        nodes.append(
            {
                "id": function_id(func.addr, id_bias=id_bias),
                "type": node_type,
                "scored": scored,
                "calls": calls,
            }
        )

    note = (
        f"generated by binary_extractor.py from {binary_path}; "
        f"root={function_id(root.addr, id_bias=id_bias)}/{root.name}; "
        f"max_depth={'unbounded' if max_depth is None else max_depth}; "
        f"excluded={exclude_patterns or []}; "
        "std/runtime classification is out of this extractor's research scope; "
        "edges to non-emitted targets are omitted"
    )

    return {
        "case": case,
        "build": build,
        "schema_version": SCHEMA_VERSION,
        "note": note,
        "nodes": nodes,
    }


def extract_fixture(args: argparse.Namespace) -> dict[str, Any]:
    extractor = BinaryExtractor(
        args.binary,
        include_imports=args.include_imports,
        id_bias=args.id_bias,
    )
    try:
        extractor.analyze()

        if args.list_functions:
            extractor.list_functions()
            return {}

        root = extractor.resolve_root(args.root)
        graph = extractor.build_call_graph()
        selected = select_reachable(graph, root.addr, max_depth=args.max_depth)
        selected = apply_exclude_filters(
            selected,
            extractor.by_addr,
            args.exclude_regex,
            root_addr=root.addr,
            id_bias=args.id_bias,
        )

        return make_fixture_json(
            case=args.case,
            build=args.build,
            binary_path=args.binary,
            root=root,
            functions=extractor.by_addr,
            graph=graph,
            selected=selected,
            score_root=args.score_root,
            max_depth=args.max_depth,
            exclude_patterns=args.exclude_regex,
            id_bias=args.id_bias,
        )
    finally:
        extractor.close()


def write_fixture(fixture: dict[str, Any], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=2)
        f.write("\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a radare2-discovered call graph into this project's "
            "*.fixture.json format."
        )
    )
    parser.add_argument("binary", help="ELF/Rust binary to analyze")
    parser.add_argument("--case", help="fixture case name, e.g. fg01")
    parser.add_argument("--build", help="build label, e.g. O3S")
    parser.add_argument(
        "-o",
        "--output",
        help="output path, conventionally fixtures/<case>.fixture.json",
    )
    parser.add_argument(
        "--root",
        help=(
            "root function name/id/address. Use --list-functions to inspect "
            "radare2 function ids. If omitted, tries main/sym.main, Rust "
            "startup wrapper detection, then entry0."
        ),
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="maximum BFS depth from root. Omit for unbounded reachable closure.",
    )
    parser.add_argument(
        "--exclude-regex",
        action="append",
        default=[],
        help=(
            "drop reachable non-root functions whose id/name/address matches this "
            "regex. May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--score-root",
        action="store_true",
        help="emit the root as user/scored=true instead of anchor/scored=false",
    )
    parser.add_argument(
        "--include-imports",
        action="store_true",
        help="include radare2 import stubs when direct calls resolve to them",
    )
    parser.add_argument(
        "--id-bias",
        type=parse_int,
        default=DEFAULT_ID_BIAS,
        help=(
            "value added to radare2 raw addresses when formatting FUN_ ids. "
            "Default 0x100000 matches the current Ghidra-style fixture ids; "
            "use 0 for raw radare2 ids."
        ),
    )
    parser.add_argument(
        "--list-functions",
        action="store_true",
        help="print radare2 functions and exit without writing output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.list_functions:
        missing = [
            name
            for name in ("case", "build", "output")
            if getattr(args, name) is None
        ]
        if missing:
            parser.error(
                "--case, --build, and --output are required unless --list-functions is used"
            )

    try:
        fixture = extract_fixture(args)
        if args.list_functions:
            return 0
        write_fixture(fixture, args.output)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {args.output}")
    print(f"nodes={len(fixture.get('nodes', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
