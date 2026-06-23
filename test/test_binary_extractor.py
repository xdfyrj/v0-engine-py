import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binary_extractor import BinaryExtractor, R2Function


class FakeR2:
    def __init__(self, responses):
        self.responses = responses

    def cmdj(self, command):
        return self.responses[command]


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


def main() -> int:
    if check_rust_startup_main_detection() != 0:
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
