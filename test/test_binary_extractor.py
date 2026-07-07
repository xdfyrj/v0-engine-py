import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import binary_extractor as binary_extractor_module
from binary_extractor import (
    BinaryExtractor,
    R2Function,
    make_fixture_json,
    select_user_context,
)


class FakeR2:
    def __init__(self, responses):
        self.responses = responses

    def cmdj(self, command):
        return self.responses[command]


def check_missing_radare2_error() -> int:
    original_which = binary_extractor_module.shutil.which
    binary_extractor_module.shutil.which = lambda _name: None

    try:
        try:
            binary_extractor_module.ensure_radare2_available()
        except RuntimeError as exc:
            message = str(exc)
            if "radare2" not in message or "binary_extractor.py" not in message:
                print(f"FAIL missing radare2 message is not actionable: {message}")
                return 1
            return 0

        print("FAIL missing radare2 executable was not rejected")
        return 1
    finally:
        binary_extractor_module.shutil.which = original_which


def check_rust_startup_main_detection() -> int:
    extractor = BinaryExtractor.__new__(BinaryExtractor)
    extractor.r2 = FakeR2(
        {
            "pdfj @ 4096": {
                "ops": [
                    {
                        "opcode": "lea rdi, [rip + 0xe81]",
                        "disasm": "lea rdi, [0x00014bd0]",
                        "ptr": 0x14BD0,
                    },
                    {
                        "opcode": "call qword [rip + 0x4175b]",
                        "disasm": "call qword [reloc.__libc_start_main]",
                    },
                ]
            },
            "pdj 64 @ 84944": [
                {"opcode": "push rax", "type": "rpush"},
                {
                    "opcode": "lea rax, [rip - 0xbbe]",
                    "disasm": "lea rax, [rip - 0xbbe]",
                    "ptr": 0x14020,
                },
                {"opcode": "mov qword [rsp], rax", "type": "mov"},
                {"opcode": "call qword [rip + 0x4091b]", "type": "ircall"},
                {"opcode": "ret", "type": "ret"},
            ],
        }
    )

    entry = R2Function(addr=0x1000, name="entry0", size=0x40, kind="fcn")

    wrapper_addr = extractor._libc_start_main_wrapper_addr(entry)
    if wrapper_addr != 0x14BD0:
        print("FAIL: __libc_start_main first argument wrapper was not detected")
        return 1

    rust_main_addr = extractor._rust_main_from_start_wrapper(wrapper_addr)
    if rust_main_addr != 0x14020:
        print("FAIL: Rust startup wrapper first main argument was not detected")
        return 1

    return 0


def check_user_address_mode() -> int:
    functions = {
        0x1000: R2Function(addr=0x1000, name="real_main", size=0x40, kind="fcn"),
        0x2000: R2Function(addr=0x2000, name="user_fn", size=0x20, kind="fcn"),
        0x3000: R2Function(addr=0x3000, name="library_fn", size=0x20, kind="fcn"),
        0x4000: R2Function(addr=0x4000, name="library_internal", size=0x20, kind="fcn"),
    }
    graph = {
        0x1000: Counter({0x2000: 1, 0x3000: 1}),
        0x2000: Counter({0x3000: 2}),
        0x3000: Counter({0x4000: 1}),
        0x4000: Counter(),
    }
    selected = select_user_context(
        graph,
        root_addr=0x1000,
        user_addrs={0x2000},
        allowed_addrs=set(functions),
        score_root=False,
    )
    if selected != {0x1000, 0x2000, 0x3000}:
        print(
            "FAIL user context should include root, users, and direct "
            f"user callees only, got {sorted(selected)}"
        )
        return 1

    fixture = make_fixture_json(
        case="fg-test",
        build="O3S",
        binary_path="bin/test.bin",
        root=functions[0x1000],
        functions=functions,
        graph=graph,
        selected=selected,
        score_root=False,
        user_addrs={0x2000},
        users_path="users/test.users.json",
        id_bias=0x100000,
    )

    nodes = {node["id"]: node for node in fixture["nodes"]}
    expected_types = {
        "FUN_00101000": ("anchor", False),
        "FUN_00102000": ("user", True),
        "FUN_00103000": ("anchor", False),
    }
    actual_types = {
        node_id: (node["type"], node["scored"])
        for node_id, node in nodes.items()
    }
    if actual_types != expected_types:
        print(f"FAIL expected user mode {expected_types}, got {actual_types}")
        return 1

    expected_user_calls = [{"target": "FUN_00103000", "count": 2}]
    if nodes["FUN_00102000"]["calls"] != expected_user_calls:
        print(
            "FAIL listed user node should retain edges to emitted "
            f"anchors, got {nodes['FUN_00102000']['calls']}"
        )
        return 1
    if nodes["FUN_00103000"]["calls"] != []:
        print(
            "FAIL one-hop library anchor should not retain edges to transitive "
            f"library internals, got {nodes['FUN_00103000']['calls']}"
        )
        return 1

    return 0


def main() -> int:
    if check_missing_radare2_error() != 0:
        return 1

    if check_rust_startup_main_detection() != 0:
        return 1

    if check_user_address_mode() != 0:
        return 1

    extractor = BinaryExtractor.__new__(BinaryExtractor)
    extractor.include_imports = False
    extractor.by_addr = {
        0x1000: R2Function(addr=0x1000, name="caller", size=0x40, kind="fcn"),
        0x2000: R2Function(addr=0x2000, name="callee", size=0x20, kind="fcn"),
    }

    caller = extractor.by_addr[0x1000]

    tail = extractor._direct_call_target(
        caller,
        {"type": "jmp", "opcode": "jmp 0x2000", "jump": 0x2000},
    )
    if tail != extractor.by_addr[0x2000]:
        print("FAIL: unconditional jmp to another function start must count as tail call")
        return 1

    internal_branch = extractor._direct_call_target(
        caller,
        {"type": "jmp", "opcode": "jmp 0x1010", "jump": 0x1010},
    )
    if internal_branch is not None:
        print("FAIL: jmp inside current function must not count as call edge")
        return 1

    conditional_branch = extractor._direct_call_target(
        caller,
        {"type": "cjmp", "opcode": "jne 0x2000", "jump": 0x2000},
    )
    if conditional_branch is not None:
        print("FAIL: conditional jump must not count as tail call")
        return 1

    print("binary extractor startup/tail-call handling PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
