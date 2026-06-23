# v0-engine-py

Rust monomorphized-function family grouping을 위한 v0 Python prototype이다.

이 프로젝트는 stripped binary에서 추출했다고 가정한 함수 간 호출 관계 JSON을 입력으로 받아, strict Rule R color refinement를 실행하고, 별도 ground truth JSON과 비교해 pairwise Precision/Recall/F1 및 ARI를 계산한다.

현재 범위는 **Axis 1 relation-only grouping engine + scorer + radare2 기반 binary extractor 초안**이다. Axis 2/3/4 feature extraction, oracle/count-priority policy, std/library classifier는 아직 포함하지 않는다.

## Pipeline

```text
fixtures/*.fixture.json
  -> loader.py
  -> engine.py strict Rule R
  -> predicted clusters
  -> scores.py
  <- ground_truth/*.gt.json
  -> P / R / F1 / ARI + floor diagnostics
```

중요한 분리:

- `fixtures/`: engine 입력. 함수 ID, node type, scored 여부, call edge만 담는다. 정답 origin은 절대 넣지 않는다.
- `ground_truth/`: scorer 입력. origin partition과 origin type만 담는다.
- `engine.py`: ground truth를 보지 않는다.

## Files

```text
model.py              dataclass model: Call, Node, Case
loader.py             fixture JSON loader + validator
binary_extractor.py   radare2 call graph -> fixture JSON 초안
engine.py             strict Rule R color refinement engine
scores.py             ground truth loader + pairwise scorer + CLI
run_case.py           one fixture -> rounds/clusters 출력
fixtures/             함수 관계 입력 JSON
ground_truth/         origin label 정답 JSON
test/test_engine.py   neighbor color multiset aggregation regression
test/test_scores.py   fg01/fg02/fg03K/fg03 metric regression
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
  "schema_version": 1,
  "origins": [
    {
      "origin": "shared_recursive",
      "type": "generic",
      "members": [
        "FUN_00113f00",
        "FUN_00113f80",
        "FUN_00113e20"
      ]
    }
  ]
}
```

Rules:

- origin object fields are exactly `origin`, `type`, `members`
- `type` is one of `generic`, `concrete`, `decoy`
- each scored fixture node must appear in exactly one origin
- ground truth universe must equal fixture nodes with `scored=true`
- `case` and `build` must match the fixture

## Strict Rule R

Implemented in `engine.py` as `run_strict_rule_r(case)`.

Used Axis 1 features:

```text
self_call_count[v]                  count(v -> v)
distinct_out_callee_count[v]         number of distinct non-self callees
outgoing[v]                          non-self outgoing weighted edges
incoming[v]                          non-self incoming weighted edges
```

v0 policy:

- directed weighted call graph
- individualized fixed anchor colors
- anchors participate as relation context but are not scored
- seed for user nodes: `(self_call_count, distinct_out_callee_count)`
- refinement signature:

```text
(
  previous_color[v],
  OUT multiset by previous neighbor color,
  IN multiset by previous neighbor color
)
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

- pairwise TP / FP / FN / TN
- Precision
- Recall
- F1
- ARI, computed from pairwise counts

Diagnostics:

- `concrete_mirror_floor`: false merge involving a concrete origin
- `decoy_floor`: false merge between decoy origins
- `relation_indistinguishable`: other false merge
- `fragmented_origins`: same origin split across multiple predicted clusters

## Binary Extractor Draft

`binary_extractor.py`는 radare2/r2pipe로 분석된 함수와 direct call op를 읽어 `fixtures/*.fixture.json` 형식으로 저장한다.

It is intentionally shallow:

- function boundary discovery is delegated to radare2
- std/runtime/library classification is not implemented in this project
- Rust root auto-detection follows the known Rust/glibc startup pattern:
  `entry0 -> __libc_start_main(wrapper) -> wrapper -> lang_start_internal(real_main, ...)`
- edges to functions omitted from output are dropped
- root is emitted as `anchor/scored=false` by default
- all other emitted reachable functions are `user/scored=true`
- output IDs use `FUN_001...` style by default via `--id-bias 0x100000`
- direct `call` edges and tail-call-like unconditional `jmp` edges are counted

Tail-call rule:

- count direct `call` targets resolved by radare2
- also count an unconditional `jmp` only when its target is exactly another radare2 function's start address
- do not count conditional jumps
- do not count jumps to addresses inside the current function

Recommended workflow:

```bash
python3 binary_extractor.py bin/family_graph_01.bin \
  --case fg01_auto \
  --build O3S \
  --max-depth 2 \
  -o fixtures/fg01_auto.fixture.json
```

If auto-detection fails, inspect radare2 functions and pass `--root` manually:

```bash
python3 binary_extractor.py bin/family_graph_01.bin --list-functions
```

Notes:

- without `--root`, the extractor first tries `main`/`sym.main`, then the Rust startup wrapper pattern, then `entry0`
- for this corpus, the wrapper often is not a radare2 function; the extractor disassembles it linearly, recovers the main-pointer loaded for the `lang_start_internal` call, and defines the real Rust main with `af @ <addr>`
- this is an explicit Rust/glibc toolchain-pattern assumption for the controlled corpus, not general indirect-dispatch recovery
- `--root` accepts radare2 name, raw address, raw `FUN_000...` id, or biased `FUN_001...` id.
- `--max-depth` controls BFS depth from root; omit it for full reachable closure.
- `--exclude-regex` may be passed multiple times to drop non-root functions by id/name/address.
- `--id-bias 0` emits raw radare2-style IDs.
- For primary evaluation, avoid case-specific `--exclude-regex` filtering unless it is explicitly documented as manual candidate selection.
- For this research, std/library separation is treated as an external preprocessing assumption, not as a core contribution of the grouping method. If a fixture depends on manual candidate selection, record that as a limitation instead of treating it as blind extraction.

## Commands

Run the engine on one fixture:

```bash
python3 run_case.py fixtures/fg01.fixture.json
```

Expected fg01 output:

```text
1
[['FUN_00113e20', 'FUN_00113f00', 'FUN_00113f80'], ['FUN_00114460', 'FUN_00114640', 'FUN_00114880']]
```

Score one case:

```bash
python3 scores.py fixtures/fg02.fixture.json ground_truth/fg02.gt.json
```

Run regression tests:

```bash
python3 test/test_engine.py
python3 test/test_binary_extractor.py
python3 test/test_scores.py
python3 -m py_compile binary_extractor.py model.py loader.py engine.py scores.py run_case.py test/test_engine.py test/test_binary_extractor.py test/test_scores.py
```

Current score regression targets:

```text
fg01 O3S   P=1.00 R=1.00 F1=1.00 ARI=1.00
fg02 O3S   P=0.29 R=1.00 F1=0.44 ARI=0.39
fg03 O3KS  P=0.94 R=1.00 F1=0.97 ARI=0.96
fg03 O3S   P=0.80 R=0.40 F1=0.53 ARI=0.49
```

## Current Data

```text
fixtures/fg01.fixture.json        ground_truth/fg01.gt.json
fixtures/fg02.fixture.json        ground_truth/fg02.gt.json
fixtures/fg03K.fixture.json       ground_truth/fg03K.gt.json
fixtures/fg03.fixture.json        ground_truth/fg03.gt.json
```

Naming:

- `fg03K` means the keep/out-of-line control build, stored as build `O3KS`
- `fg03` means natural O3 stripped build, stored as build `O3S`

## Research Notes

This implementation follows the current research decision:

- grouping is relation-only Axis 1
- Axis 2 is type memo/corroboration only
- Axis 3 is inlining/floor characterization
- Axis 4 is ablation only
- feature input and ground truth must remain physically separated

The prototype is intentionally narrow: it validates whether strict Rule R over hand-prepared function relation JSON reproduces the current fg01/fg02/fg03 claims.
