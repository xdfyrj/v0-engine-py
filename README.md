# v0-engine-py

Rust monomorphized-function family grouping을 위한 v0 Python prototype이다.

이 프로젝트는 stripped binary에서 추출했다고 가정한 함수 간 호출 관계 JSON을 입력으로 받아, Call-Graph Weisfeiler-Lehman(CG-WL) color refinement를 실행하고, 별도 ground truth JSON과 비교해 pairwise Precision/Recall/F1 및 ARI를 계산한다.

현재 범위는 **rustc 기반 corpus compiler + Axis 1 relation-only grouping engine + scorer + radare2 기반 binary extractor 초안**이다. Axis 2/3/4 feature extraction, oracle/count-priority mode, std/library classifier는 아직 포함하지 않는다.

파이프라인 각 단계의 상세 설계 설명은 [`docs/document.md`](docs/document.md)를 참고한다.

## Requirements

Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

System tools:

- `rustc`: required only by `compile.py`; the checked-in corpus was built and validated with rustc 1.93.1
- `strip`: required only by `compile.py` and normally provided by GNU binutils
- `radare2`: required only by `binary_extractor.py` and by the Python `r2pipe` backend
- `nm`: required by `gt_extractor.py` and normally provided by GNU binutils

Dependency scope:

- `engine.py`, `scores.py`, and `run_case.py` over already generated JSON do not import `r2pipe` directly.
- `binary_extractor.py --help` and unit tests can import the module without `r2pipe`.
- actual binary extraction checks for the radare2 executable first, then imports the Python `r2pipe` package. Missing dependencies are reported as actionable CLI errors.

## Pipeline

```text
src/*.rs
  -> compile.py (rustc O3 / O3K)
  -> gt_bin/*.gt.bin           non-stripped symbol side
  -> bin/*.fixture.bin         stripped evaluation side (strip --strip-all)
  -> build_info/*.json         source/toolchain/binary-pair manifest

gt_bin/*.gt.bin
  -> gt_extractor.py
  -> ground_truth/*.gt.json
  -> users/*.users.json

bin/*.fixture.bin
  -> binary_extractor.py + users/*.users.json
  -> fixtures/*.fixture.json

fixtures/*.fixture.json
  -> loader.py
  -> engine.py CG-WL
  -> predicted clusters
  -> scores.py
  <- ground_truth/*.gt.json
  -> predicted clusters + symbols + TP / FP / FN + PR / RE / F1 / ARI
```

중요한 분리:

- `fixtures/`: engine 입력. 함수 ID, node type, scored 여부, call edge만 담는다. 정답 origin은 절대 넣지 않는다.
- `ground_truth/`: scorer 입력. origin partition과 출력용 demangled symbol을 담는다.
- `users/`: non-stripped symbol side에서 뽑은 user function raw address set. origin/group 정보는 담지 않는다.
- `engine.py`: ground truth를 보지 않는다.

## Files

```text
model.py              dataclass model: Call, Node, Case
loader.py             fixture JSON loader + validator
compile.py            Rust source -> non-stripped gt_bin + stripped bin
binary_extractor.py   radare2 call graph -> fixture JSON 초안
gt_extractor.py       non-stripped symbol table -> ground truth JSON
engine.py             Call-Graph Weisfeiler-Lehman color refinement engine
scores.py             ground truth loader + pairwise scorer + CLI
run_case.py           stem-based end-to-end pipeline runner
src/                  Rust example sources (corpus 원본)
bin/                  stripped evaluation binaries
gt_bin/               non-stripped ground-truth binaries
fixtures/             함수 관계 입력 JSON
ground_truth/         origin label 정답 JSON
users/                user function raw address JSON
test/test_compile.py  rust-loss flag parity and command assembly regression
test/test_engine.py   neighbor color multiset aggregation regression
test/test_binary_extractor.py startup, tail-call, user address regression
test/test_gt_extractor.py compiler symbol GT and user address regression
test/test_scores.py   fg01/fg02/fg03K/fg03 metric regression
```

## Binary Provenance

The example sources under `src/` and the build recipe originate from the
companion Rust artifact repository:

- source repository: https://github.com/xdfyrj/rust-loss
- source cases: `rust-loss/examples/family_graph_01.rs`,
  `family_graph_02.rs`, `family_graph_03.rs`, copied into `src/`
- original build scripts: `rust-loss/scripts/build_case.sh` and
  `rust-loss/scripts/lib_build.sh`

The corpus binaries are now built source-to-end inside this repository by
`compile.py`, which reproduces the `rust-loss` recipe exactly: direct `rustc`
invocation, not Cargo, so compiler flags and profiles stay explicit.
A single build manifest under `build_info/` records the source, compiler,
strip command, target, and hashes of both binaries. `run_case.py` verifies this
manifest before extracting any JSON.

Current build conditions:

```text
OS/kernel: Linux XDFYRJ 6.6.114.1-microsoft-standard-WSL2 x86_64
target/host: x86_64-unknown-linux-gnu
rustc: rustc 1.93.1 (01f6ddf75 2026-02-11)
LLVM: 21.1.8
cargo: 1.93.1 (not used for artifact builds)
binutils: GNU strip/objdump/nm 2.42
edition: 2024
crate-type: bin, crate-name = case
```

Build profiles relevant to this repository:

```text
O3:
  non-stripped optimized mapping / symbol source
  flags: -C opt-level=3 -C codegen-units=1 -C lto=off -C panic=unwind
         -C debuginfo=0 -C debug-assertions=off -C overflow-checks=off

O3S:
  stripped evaluation binary derived from O3 with strip --strip-all

O3K:
  non-stripped optimized control build with --cfg keep
  flags: O3 flags + --cfg keep

O3KS:
  stripped evaluation binary derived from O3K with strip --strip-all
```

In this repository, `gt_bin/*.gt.bin` is the non-stripped symbol-bearing side
used by `gt_extractor.py`, while `bin/*` is the stripped evaluation side
used by `binary_extractor.py`. The evaluation build label (`O3S`/`O3KS`) names
both files of a pair; the `gt_bin/` file itself is the non-stripped `O3`/`O3K`
binary that the stripped binary was derived from.

The checked-in canonical corpus consists of four builds generated from the
current `src/`: family_graph_01/O3S, family_graph_02/O3S,
family_graph_03/O3S, and family_graph_03/O3KS. The manifest for each build is
the authority for its source and binary hashes.

Canonical commands separate source case from build/profile:

```text
case  = family_graph_03
build = O3S | O3KS
```

Canonical generated files use `family_graph_03.O3KS.*`, while the Rust crate
symbol prefix remains `family_graph_03::`.

## Corpus Compiler

`compile.py`는 `src/*.rs` 하나에서 한 evaluation build의 바이너리 쌍을 만든다.

```text
src/<case>.rs
  -> rustc (O3 or O3K profile)
  -> gt_bin/<case>.<build>.gt.bin        non-stripped, gt_extractor.py 입력
  -> strip --strip-all
  -> bin/<case>.<build>.fixture.bin      stripped, binary_extractor.py 입력
  -> build_info/<case>.<build>.json      검증용 build manifest
```

Build-to-profile mapping:

- `--build O3S` compiles the `O3` profile and strips the copy
- `--build O3KS` compiles the `O3K` (`--cfg keep`) profile and strips the copy
- other builds are rejected; `O0`/`O3`/`O3K` alone have no stripped
  evaluation pair in this project

Compilation rules:

- flags are byte-identical to `rust-loss/scripts/lib_build.sh` `profile_flags()`;
  `test/test_compile.py` locks this parity
- `--crate-name` equals the case name, so the crate symbol prefix stays
  `<case>::` for `gt_extractor.py`
- `--edition 2024`, `--crate-type bin`
- `rust-loss` emits `llvm-ir,asm,link`; `compile.py` emits `link` only.
  Under the same rustc this produces a byte-identical binary, and the
  `.ll`/`.s` mapping aids are out of this repository's scope
- one JSON manifest records `rustc -vV`, tool paths and commands, flags,
  target, and SHA-256 hashes of the source and both binaries

Example:

```bash
python3 compile.py family_graph_03
python3 compile.py family_graph_03 --build O3KS
```

Equivalent explicit input/output form:

```bash
python3 compile.py src/family_graph_03.rs \
  --build O3KS \
  --gt-binary gt_bin/family_graph_03.O3KS.gt.bin \
  --fixture-binary bin/family_graph_03.O3KS.fixture.bin \
  --manifest build_info/family_graph_03.O3KS.json
```

## Fixture JSON

`fixtures/*.fixture.json`는 함수 관계만 담는다.

```json
{
  "case": "fg01",
  "build": "O3S",
  "schema_version": 1,
  "nodes": [
    {
      "id": "FUN_00113f00",
      "type": "user",
      "scored": true,
      "calls": [
        { "target": "FUN_00113f00", "count": 1 }
      ]
    },
    {
      "id": "FUN_00114020",
      "type": "anchor",
      "scored": false,
      "calls": [
        { "target": "FUN_00113f00", "count": 2 }
      ]
    }
  ]
}
```

Rules:

- top-level required fields: `case`, `build`, `schema_version`, `nodes`
- optional top-level field: `note`
- `schema_version` is currently `1`
- node `type` is `user` or `anchor`
- only `user` nodes may have `scored=true`
- `anchor` nodes must have `scored=false`
- every call target must be present as a node
- call count must be a positive integer
- one source may contain at most one edge per target; aggregate count in JSON

## Ground Truth JSON

`ground_truth/*.gt.json`는 scorer 전용 정답이다.

```json
{
  "case": "fg01",
  "build": "O3S",
  "schema_version": 3,
  "origins": [
    {
      "origin": "shared_recursive",
      "members": [
        "FUN_00113f00",
        "FUN_00113f80",
        "FUN_00113e20"
      ]
    }
  ],
  "symbols": {
    "FUN_00113f00": [
      "family_graph_01::shared_recursive"
    ],
    "FUN_00113f80": [
      "family_graph_01::shared_recursive::<i32>"
    ],
    "FUN_00113e20": [
      "family_graph_01::shared_recursive::<u64>"
    ]
  }
}
```

Rules:

- origin object fields are exactly `origin`, `members`
- ground truth `schema_version` is currently `3`
- each scored fixture node must appear in exactly one origin
- top-level `symbols` maps each scored function id to one or more original demangled symbol names
- ground truth universe must equal fixture nodes with `scored=true`
- `case` and `build` must match the fixture

## Ground Truth Extractor Draft

`gt_extractor.py`는 non-stripped Rust binary의 demangled symbol table에서 두 파일을 생성한다.

```text
ground_truth/<case>.<build>.gt.json
users/<case>.<build>.users.json
```

Current extraction rules:

- symbol source is `nm -n -C`
- controlled builds are expected to use Rust legacy symbol mangling; v0-style demangled generic arguments like `::<i32>` are stripped defensively when present
- only text symbols whose demangled name starts with the target crate prefix are kept, e.g. `family_graph_01::`
- `main` is excluded because it is an anchor, not a scored function
- raw symbol address is converted to the fixture id format with `addr + 0x100000`, e.g. `0x13f00 -> FUN_00113f00`
- same demangled origin name becomes one ground truth origin group
- full demangled symbols are preserved in top-level `symbols`; if the binary was built with legacy Rust symbol mangling, generic type arguments may not be present in those symbols
- if duplicate symbols for the same origin resolve to the same address, the member is emitted once and the duplicate is recorded in top-level `note`
- if different origins resolve to the same address, GT generation fails instead of silently choosing one origin

Interpretation:

- family membership is compiler-derived from non-stripped symbol addresses and demangled source paths
- ground truth does not encode generic/concrete kind labels

Example:

```bash
python3 gt_extractor.py family_graph_01
```

Equivalent explicit input/output form:

```bash
python3 gt_extractor.py gt_bin/family_graph_01.gt.bin ground_truth/family_graph_01.O3S.gt.json \
  --build O3S \
  --users users/family_graph_01.O3S.users.json
```

For the O3KS control build, use the source case plus build:

```bash
python3 gt_extractor.py family_graph_03 --build O3KS
```

## User Address Sidecar

`users/*.users.json` is the bridge from non-stripped symbols to
stripped fixture extraction.

Example:

```json
{
  "case": "family_graph_03",
  "build": "O3S",
  "schema_version": 1,
  "source": "gt_bin/family_graph_03.gt.bin",
  "prefix": "family_graph_03::",
  "addresses": [
    "0x14080",
    "0x140e0"
  ]
}
```

Rules:

- addresses are raw `.text` addresses from the non-stripped binary
- the file contains no origin name or family/group label
- stripped and non-stripped artifacts are expected to preserve function start addresses
- `binary_extractor.py` uses this file as an allow-list:
  - listed user address -> `type=user`, `scored=true`
  - direct callee of a listed user function -> `type=anchor`, `scored=false`
  - root main -> `type=anchor`, `scored=false`
- root anchor keeps edges to listed user functions
- non-root anchors are terminal: their outgoing/self edges are not emitted
- library/runtime internals beyond those one-hop anchors are not chased

This keeps the normal family_graph pipeline free of case-specific depth limits
or regex-based function removal.

## Case/Build Convention

The convenient commands take a source case and an optional build/profile.
If `--build` is omitted, it defaults to `O3S`.

Naming rules:

- Rust source: `src/<case>.rs`
- stripped/fixture binary: `bin/<case>.<build>.fixture.bin`
- non-stripped GT binary: `gt_bin/<case>.<build>.gt.bin`
- build manifest: `build_info/<case>.<build>.json`
- generated fixture JSON: `fixtures/<case>.<build>.fixture.json`
- generated ground truth JSON: `ground_truth/<case>.<build>.gt.json`
- generated user address JSON: `users/<case>.<build>.users.json`

Example:

```text
family_graph_03 --build O3S
  -> bin/family_graph_03.O3S.fixture.bin
  -> gt_bin/family_graph_03.O3S.gt.bin
  -> build_info/family_graph_03.O3S.json
  -> fixtures/family_graph_03.O3S.fixture.json
  -> ground_truth/family_graph_03.O3S.gt.json
  -> users/family_graph_03.O3S.users.json

family_graph_03 --build O3KS
  -> bin/family_graph_03.O3KS.fixture.bin
  -> gt_bin/family_graph_03.O3KS.gt.bin
  -> build_info/family_graph_03.O3KS.json
  -> fixtures/family_graph_03.O3KS.fixture.json
  -> ground_truth/family_graph_03.O3KS.gt.json
  -> users/family_graph_03.O3KS.users.json
```

## Call-Graph Weisfeiler-Lehman

Implemented in `engine.py` as `run_cg_wl(case, mode="full")`.

CG-WL is a directed, weighted, anchor-aware 1-WL refinement over the call graph.

Used Axis 1 features:

```text
self_call_count[v]                  count(v -> v)
distinct_out_callee_count[v]         number of distinct non-self callees
distinct_in_caller_count[v]          number of distinct non-self callers
outgoing[v]                          non-self outgoing weighted edges
incoming[v]                          non-self incoming weighted edges
```

Common behavior:

- directed weighted call graph
- individualized fixed anchor colors
- anchors participate as relation context but are not scored
- neighbor multisets aggregate call counts by previous neighbor color

Relation modes:

- `full`: seed `(self_call_count, distinct_out_callee_count)`, refine with OUT + IN
- `out`: seed `(self_call_count, distinct_out_callee_count)`, refine with OUT only
- `in`: seed `(self_call_count, distinct_in_caller_count)`, refine with IN only
- `out-in`: seed `(self_call_count, distinct_out_callee_count)`, refine with OUT; if `distinct_out_callee_count == 0`, refine with OUT + IN

```text
full   : (previous_color[v], OUT multiset, IN multiset)
out    : (previous_color[v], OUT multiset)
in     : (previous_color[v], IN multiset)
out-in : non-leaf -> out; leaf -> full
```

Neighbor multiset rule:

```text
key = previous_color[neighbor]
value += static_callsite_count
```

So two same-color callees with counts 1 and 2 become:

```text
(color, 3)
```

not:

```text
(color, 1), (color, 2)
```

Deliberately excluded from v0 grouping:

- origin / ground truth labels
- arg count, sret, ABI shape, register class, width
- BB / CFG / instruction distribution
- total outgoing call count as a seed
- count-priority oracle
- soft merge

## Scoring

Implemented in `scores.py`.

The scorer compares predicted clusters against origin partition over the scored universe.

Metrics:

- predicted clusters over scored nodes
- `symbols:` block showing the demangled symbol for each predicted cluster member
- pairwise TP / FP / FN
- Precision (`PR`)
- Recall (`RE`)
- F1
- ARI, computed from pairwise counts

## Binary Extractor Draft

`binary_extractor.py`는 radare2/r2pipe로 분석된 함수와 direct call op를 읽어 `fixtures/*.fixture.json` 형식으로 저장한다.

It is intentionally shallow:

- function boundary discovery is delegated to radare2
- user/library classification is not inferred from stripped code
- user functions are supplied as raw addresses from `users/*.users.json`
- in user-address mode, anchor context is intentionally one-hop:
  direct callees of listed user functions only
- root anchor keeps edges to listed user functions
- non-root anchors are terminal and do not emit outgoing/self edges
- Rust root auto-detection follows the known Rust/glibc startup pattern:
  `entry0 -> __libc_start_main(wrapper) -> wrapper -> lang_start_internal(real_main, ...)`
- edges to functions omitted from output are dropped
- root is emitted as `anchor/scored=false` by default
- with a user address file, only listed user nodes are `user/scored=true`
- direct non-user callees of listed user nodes are `anchor/scored=false`
- output IDs use `FUN_001...` style by default via `--id-bias 0x100000`
- direct `call` edges and tail-call-like unconditional `jmp` edges are counted

Tail-call rule:

- count direct `call` targets resolved by radare2
- also count an unconditional `jmp` only when its target is exactly another radare2 function's start address
- do not count conditional jumps
- do not count jumps to addresses inside the current function

Recommended workflow:

```bash
python3 gt_extractor.py family_graph_03
python3 binary_extractor.py family_graph_03
```

Equivalent explicit input/output form:

```bash
python3 binary_extractor.py bin/family_graph_03.O3S.fixture.bin fixtures/family_graph_03.O3S.fixture.json \
  --build O3S \
  --users users/family_graph_03.O3S.users.json
```

If auto-detection fails, inspect radare2 functions and pass `--root` manually:

```bash
python3 binary_extractor.py bin/family_graph_01.O3S.fixture.bin --list-functions
```

Notes:

- without `--root`, the extractor first tries `main`/`sym.main`, then the Rust startup wrapper pattern, then `entry0`
- for this corpus, the wrapper often is not a radare2 function; the extractor disassembles it linearly, recovers the main-pointer loaded for the `lang_start_internal` call, and defines the real Rust main with `af @ <addr>`
- this is an explicit Rust/glibc toolchain-pattern assumption for the controlled corpus, not general indirect-dispatch recovery
- `--root` accepts radare2 name, raw address, raw `FUN_000...` id, or biased `FUN_001...` id.
- if `users/<case>.<build>.users.json` exists, the shortcut loads it automatically.
- `--id-bias 0` emits raw radare2-style IDs.

## Commands

Compile one case into its binary pair:

```bash
python3 compile.py family_graph_03
python3 compile.py family_graph_03 --build O3KS
```

Run the engine on one fixture:

```bash
python3 engine.py fixtures/family_graph_03.O3S.fixture.json
```

Expected fg01 output:

```text
full
1
[['FUN_00113e20', 'FUN_00113f00', 'FUN_00113f80'], ['FUN_00114460', 'FUN_00114640', 'FUN_00114880']]
```

Case/build shortcut:

```bash
python3 engine.py family_graph_03
python3 engine.py family_graph_03 --build O3KS
python3 engine.py family_graph_03 --mode out-in
```

Run the full pipeline for one stem:

```bash
python3 run_case.py family_graph_03
python3 run_case.py family_graph_03 --build O3KS
python3 run_case.py family_graph_03 --all-modes
```

This executes:

```text
build_info manifest -> source/GT binary/fixture binary hash validation
gt_extractor.py     -> ground_truth/family_graph_03.O3S.gt.json
gt_extractor.py     -> users/family_graph_03.O3S.users.json
binary_extractor.py -> fixtures/family_graph_03.O3S.fixture.json
engine.py CG-WL     -> predicted clusters
scores.py           -> predicted clusters + symbols + TP/FP/FN + PR/RE/F1/ARI report
```

Regenerate the current family_graph stems source-to-end:

```bash
python3 compile.py family_graph_01 && python3 run_case.py family_graph_01
python3 compile.py family_graph_02 && python3 run_case.py family_graph_02
python3 compile.py family_graph_03 && python3 run_case.py family_graph_03
python3 compile.py family_graph_03 --build O3KS && python3 run_case.py family_graph_03 --build O3KS
```

Score one case:

```bash
python3 scores.py fixtures/family_graph_03.O3S.fixture.json ground_truth/family_graph_03.O3S.gt.json
```

Case/build shortcut:

```bash
python3 scores.py family_graph_03
python3 scores.py family_graph_03 --build O3KS
python3 scores.py family_graph_03 --mode out
python3 scores.py family_graph_03 --all-modes
```

Generate family-level measurement source reports:

```bash
python3 family_report.py
python3 family_report.py family_graph_01
python3 family_report.py family_graph_03 --mode out
python3 family_report.py family_graph_03 --all-modes
python3 family_report.py family_graph_03.O3KS --out-dir reports/fg03_o3ks
```

This writes:

```text
reports/measurement_evidence.md
reports/origins.csv
reports/anchors.csv
reports/instance_relations.csv
reports/round_partitions.csv
reports/round_signatures.csv
reports/family_rows.csv
reports/predicted_clusters.csv
reports/collision_candidates.csv
reports/scores.csv
```

`family_report.py` is score-side measurement code. It annotates predicted
clusters with origin/family labels after CG-WL has run; the engine still never
reads ground truth. It is intended as a minimal evidence pack for writing
measurement notes, not as an automatic diagnosis generator. It reports observed
origin membership, anchor context, per-instance Axis-1 relations, round
partitions/signatures, family rows, predicted clusters, collision candidates,
and pairwise scores. It intentionally omits diagnosis, conclusions,
source-level census, and coverage. The default mode is `full`; use
`--all-modes` to report `full`, `out`, `in`, and `out-in`.

Extract compiler-derived ground truth:

```bash
python3 gt_extractor.py family_graph_03
```

Equivalent explicit input/output form:

```bash
python3 gt_extractor.py gt_bin/family_graph_03.gt.bin ground_truth/family_graph_03.O3S.gt.json \
  --build O3S \
  --users users/family_graph_03.O3S.users.json
```

Extract fixture JSON from stripped binary using the user address sidecar:

```bash
python3 binary_extractor.py family_graph_03
```

Run regression tests:

```bash
python3 test/test_compile.py
python3 test/test_engine.py
python3 test/test_binary_extractor.py
python3 test/test_gt_extractor.py
python3 test/test_scores.py
python3 -m py_compile compile.py binary_extractor.py gt_extractor.py model.py loader.py engine.py scores.py run_case.py family_report.py test/test_compile.py test/test_engine.py test/test_binary_extractor.py test/test_gt_extractor.py test/test_scores.py
```

Current score regression targets:

```text
family_graph_01 O3S   P=1.00 R=1.00 F1=1.00 ARI=1.00
family_graph_02 O3S   P=0.29 R=1.00 F1=0.44 ARI=0.39
family_graph_03 O3KS  P=0.94 R=1.00 F1=0.97 ARI=0.96
family_graph_03 O3S   P=0.80 R=0.40 F1=0.53 ARI=0.49
```

## Current Data

```text
fixtures/family_graph_01.O3S.fixture.json
fixtures/family_graph_02.O3S.fixture.json
fixtures/family_graph_03.O3KS.fixture.json
fixtures/family_graph_03.O3S.fixture.json

ground_truth/family_graph_01.O3S.gt.json
ground_truth/family_graph_02.O3S.gt.json
ground_truth/family_graph_03.O3KS.gt.json
ground_truth/family_graph_03.O3S.gt.json

users/family_graph_01.O3S.users.json
users/family_graph_02.O3S.users.json
users/family_graph_03.O3KS.users.json
users/family_graph_03.O3S.users.json
```

Regression scoring uses the compiler-derived `ground_truth/family_graph_*.<build>.gt.json`
files and the corresponding automatically extracted fixtures.
Legacy `fg*` fixtures and ground-truth files may remain in the repository for
comparison, but the active workflow uses `case + build`, e.g.
`family_graph_03 --build O3KS`.

Naming:

- `case=family_graph_03, build=O3KS` means the keep/out-of-line control build
- `case=family_graph_03, build=O3S` means the natural O3 stripped build

## Research Notes

This implementation follows the current research decision:

- grouping is relation-only Axis 1
- Axis 2 is type memo/corroboration only
- Axis 3 is inlining / recall-loss characterization
- Axis 4 is ablation only
- feature input and ground truth must remain physically separated

The prototype is intentionally narrow: it validates whether CG-WL over extracted family_graph function relation JSON reproduces the current fg01/fg02/fg03 claims.
