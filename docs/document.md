# v0-engine

## 1. Overview

`v0-engine-py`는 Rust monomorphized function family regrouping 연구를 위한 v0 prototype이다. 목표는 완전한 Rust reverse engineering 도구를 만드는 것이 아니라, stripped Rust binary에서 관찰 가능한 **Axis 1 call relation**만으로 같은 generic origin에서 나온 함수 묶음을 어느 정도 복원할 수 있는지 측정하는 것이다.

`binary_extractor.py`는 stripped binary에서 direct call 및 tail-call-like jump를 추출하여 CG-WL이 사용할 fixture JSON을 만든다. 이 fixture에는 함수 ID, node type, scored 여부, call target, call count만 들어간다. generic origin label이나 type 정보는 포함하지 않는다.

`gt_extractor.py`는 non-stripped binary의 symbol 정보를 이용해 ground truth JSON을 만든다. 이 ground truth는 어떤 함수들이 같은 generic source definition에서 나온 instance인지 기록한다. 이 정보는 clustering 단계에서는 사용되지 않고, scoring 단계에서만 사용된다.

`engine.py`는 fixture JSON만 보고 Call-Graph Weisfeiler-Lehman(CG-WL)을 실행한다. CG-WL은 함수의 self-call count, non-self out-degree, caller/callee relation, call count를 반복적으로 반영하여 predicted cluster를 만든다. 즉 함수 body similarity가 아니라 call graph 안에서의 역할을 기준으로 grouping한다.

`scores.py`는 engine이 만든 predicted clusters와 ground truth를 비교한다. 평가는 함수 하나하나가 아니라 함수 쌍(pair) 기준으로 수행한다. 같은 origin이어야 하는 함수 쌍을 같은 cluster로 묶으면 TP, 다른 origin인데 같은 cluster로 묶으면 FP, 같은 origin인데 서로 다른 cluster로 갈라지면 FN으로 계산한다. 최종적으로 predicted clusters, symbols, TP/FP/FN, Precision, Recall, F1, ARI를 출력한다.

따라서 `v0-engine-py`는 다음을 자동화한다.

`stripped binary → call-relation fixture → CG-WL clustering → ground truth scoring`

다만 이 도구는 아직 user/library filtering, indirect call recovery, type recovery, inlining-aware similarity를 해결하지 않는다. 현재 목적은 relation-only baseline의 가능성과 한계를 재현 가능한 형태로 고정하는 것이다.

## 2. pipeline

```
stripped binary          non-stripped binary
      |                         |
binary_extractor.py      gt_extractor.py
      |                         |
fixture JSON             ground truth JSON
	  |                         |
  engine.py                     |
      |                         |
      +------> scores.py <------+
                   |
        P/R/F1/ARI + floor diagnosis
```

파이프 라인을 3가지 경로로 크게 구분 할 수 있다.

1. **Fixture Path**: 
	`stripped binary -> binary_extractor.py -> fixture JSON -> engine.py -> predicted clusters`

2. **Ground Truth Path**: 
	`non-stripped binary -> gt_extractor.py -> ground truth JSON`

3. **Scoring Path**: 
	`predicted cluster + ground truth JSON -> scores.py -> P/R/F1/ARI`

중요한 점은 fixture JSON에는 origin label이 들어가지 않는다는 것이다. 
engine은 stripped binary에서 관찰 가능한 call relation만 보고 predicted cluster를 만든다. 
ground truth는 scores.py에서만 사용된다. 
따라서 grouping 단계와 정답 label이 물리적으로 분리되어 label leakage를 줄인다.

## 3. Data Model

model은 전체 프로젝트의 내부 자료구조를 정의한다.

- **Call**: target, count
	- 한 함수가 다른 함수를 몇 번 정적으로 Call하는지.

- **Node**: id, types, scored, calls
	- id: `FUN_00113f00` 같은 함수 ID
	- types: user인지 anchor인지.
	- scored: 최종 점수에 반영이 되는 함수인지 아닌지.
	- calls: out-call edge 목록.

- **Case**: case, build, schema_version, nodes
	- fixture 하나의 전체.

## 4. Fixture Path
stripped binary -> predicted cluster

### 4.1 binary_extractor.py
stripped binary에서 Axis 1 fixture를 만드는 경로

입력: bin/~.bin
출력: fixtures/~.fixture.json

큰 흐름은 6단계로 나눌 수 있다.
```
1. radare2 세션 열기  
2. 함수 목록 수집  
3. main 찾기  
4. 함수별 call edge 추출  
5. root에서 reachable subgraph 선택  
6. fixture JSON 작성
```

`binary_extractor.py`의 `extract_fixture()`가 전체 추출 파이프라인이다.

#### 1단계: Radare2 세션 열기
`BinaryExtractor` 객체가 만들어 지고, r2pipe로 바이너리를 연다.

```python
self.r2 = r2pipe.open(binary_path, flags=["-2"])
```
r2pipe를 연 후부터는 실제 분석은 radare2에게 계속 명령을 보내는 방식이다.

실제:
```
Python → r2pipe → radare2 → binary analysis result → Python
```

Python 구현이 외부 분석 도구와 계속 대화하도록 설계되어있다.

#### 2단계: 함수 목록 수집
핵심 함수:
```python
analyze()
_refresh_functions()
```

흐름은 `aaa -> aflj -> R2Function 목록 생성`이다.

`aaa`는 radare2의 자동 분석 명령이다. 함수, xref, call target 등을 최대한 찾아보게 한다.

`aflj`는 radare2가 찾은 함수 목록을 JSON으로 출력한다.

각 함수는 내부에서 아래와 같이 저장된다.
```python
@dataclass(frozen=True)
class R2Function:
    addr: int
    name: str
    size: int
    kind: str
```

`R2Function`은 radare2가 본 함수 하나다.

여기서 중요한 점은 **함수 경계는 직접 복원하는 게 아니라 radare2의 분석 결과에 의존한다**라는 점이다.
이건 extractor의 중요한 한계다.
#### 3단계: main 찾기
핵심 함수:
```python
resolve_root()
_root_from_libc_start_main()
_libc_start_main_wrapper_addr()
_rust_main_from_start_wrapper()
```

main 찾기를 요약하면 아래와 같다.

`entry0`에서 **`__libc_start_main`에 넘기는 `main` 주소**를 찾고,  
`main` 안에서 **`std::rt::lang_start_internal`에 넘기는 Rust user main 주소**를 찾는다.

`entry0`에서부터 BFS를 시작하면 Rust runtime 함수가 많이 섞이기에 이 과정은 아주 중요하다.

다만, root 자동 탐지는 Rust startup wrapper pattern에 기반한 heuristic이며, 실패할 경우 `--root`로 명시 지정한다.

#### 4단계: call edge 추출
핵심 함수:
```python
direct_calls()
_direct_call_target()
_is_call_op()
_is_tail_call_jump_op()
_call_target()
```

여기가 Axis 1 추출의 중심이다.
각 함수에 대해 radare2에게 disassembly JSON을 요청한다.
```
pdfj @ 함수주소
```
그다음 instruction을 하나씩 보면서 call edge를 찾습니다.
##### 4단계-1 direct call
예를 들어 instruction이 `call 0x115e70`일 경우, target 주소 `0x115e70`을 가져온다.
그리고 그 target이 어떤 함수 안에 들어가는지 찾는다.

```python
function_containing(target)
```
그러면 edge가 된다.

그리고 `Counter`로 개수를 센다.
`F -> G x 5` 이런 식이다.
##### 4단계-2 tail jmp
O3에서는 TCO(Tail Call Optimization)이 발생할 수 있다.
형식은 아래와 같다.
```
call f
ret
```
->
```
jmp f
```

따라서 `binary_extractor.py`는 unconditional `jmp`도 조건부로 call edge로 센다.

tail-call 최적화는 잡되, 일반 branch나 switch case를 call edge로 오탐하지 않기 위해서 조건을 아래와 같이 보수적으로 잡는다.
```
- op type이 jmp 또는 ujmp
- 또는 opcode가 "jmp "로 시작
- target이 다른 함수의 시작 주소
- 자기 함수 내부 jump는 제외
- conditional jump는 제외
```

#### 5단계: reachable 함수 선택
핵심 함수:
```python
select_reachable()
apply_exclude_filters()
```
`select_reachable()`는 root에서 BFS를 돈다.

`main -> callee -> callee의 callee`의 구조로 따라가며 reachable function set을 만든다.

`--max-depth`가 있으면 깊이를 제한한다.

```
--max-depth 2
```
->
```
root에서 2-hop 안에 있는 함수만 선택
```

`apply_exclude_filters()`는 `--exclude-regex`로 전달된 특정 함수를 제거한다.

```
--exclude-regex FUN_0014d6b3
```

`노드 제거 -> edge 제거 -> topology 변경 -> 결과 변경 가능`

`select_reachable()`는 실제 Rust binary에서 root로부터 reachable한 함수가 너무 많기 때문에 library/user 구별이 불가한 현 구현으로써는 필요하다.
또, `apply_exclude_filters()`도 `--exclude-regex`를 통한 user/library filtering이 아직 완전 자동화되지 않은 v0에서 특정 runtime/helper 노드를 제거하기 위한 보조 장치이다.

하지만 이 두가지 경우는 관련 전달 option에 따라 graph topology가 변할 수 있다는 것을 의미하기에, 추후 개선이 필요하다.

#### 6단계: fixture JSON 작성
핵심 함수:
```python
make_fixture_json()
```
최종적으로 engine이 읽을 JSON을 만든다.

각 Node는 아래와 같이 된다:
```json
{
  "id": "FUN_00114020",
  "type": "user",
  "scored": true,
  "calls": [
    {"target": "FUN_00114500", "count": 3}
  ]
}
```

root 함수(main 함수라고 찾은 함수)는 기본적으로 anchor가 된다.
```json
{
  "id": "FUN_00113fe0",
  "type": "anchor",
  "scored": false,
  "calls": [...]
}
```

즉 root/main은 CG-WL refinement에는 영향을 줄 수 있지만, 최종 scoring에는 들어가지 않는다.

그리고, fixture JSON에는 ground truth origin이 없기에 label leakage를 막을 수 있다.

### 4.2 loader.py
fixture JSON to `Case`

fixture JSON은 `loader.py` 파일의 `load_case()`가 읽는다.

흐름:
- `load_case()` 
	- -> `validate_raw_fixture()` 
	- -> `_validate_top_level()` 
	- -> `_validate_nodes()`
	- -> `_validate_calls()`
	- -> `Case(...)` 

단순 `Case(Node(Call()))` 형식의 parsing이 주가 아니라, 세부적인 CG-WL engine이 해석할 수 있는 안전한 입력인지 검증하는 gatekeeper 역할이 핵심이다.

주요 검증 대상은 다음과 같다:
- top-level field가 올바른가  
- node id가 중복되지 않는가  
- node type과 scored 값이 규약에 맞는가  
- call target이 실제 nodes 안에 존재하는가  
- call count가 양수인가  
- 같은 source node 안에서 같은 target으로 중복 call edge가 없는가

이 검증을 통과한 fixture만 `engine.py`로 전달된다. 따라서 `loader.py`는 잘못된 fixture 때문에 CG-WL 결과가 왜곡되는 것을 막는 입력 검증 단계이다.

### 4.3 engine.py
Axis 1 call-graph color refinement engine

입력: `Case(Node(Call))`
출력: predicted clusters

`Case`:
- node id
- node type: user / anchor
- scored: 점수 산출 여부
- calls: target, count

`engine.py`는 fixture JSON으로 들어온 call graph를 받아서, 함수들을 호출 관계상 같은 role을 가진 그룹으로 나누는 CG-WL engine이다.

#### 1단계: RelationGraphView
관련 함수:
```python
build_relation_graph_view(case)
```
이 단계는 fixture의 call list를 CG-WL이 쓰기 좋은 형태로 바꾼다.

fixture에는 각 node마다 아래와 같이 들어있다.
```json
{
  "id": "A",
  "calls": [
    {"target": "B", "count": 5},
    {"target": "A", "count": 1}
  ]
}
```

`engine.py`는 이것을 세 가지로 나눈다.

```
self_call_count
outgoing
incoming
```

예:
```
A -> A ×1
A -> B ×5
```
->
```
self_call_count[A] = 1
outgoing[A] = [(B, 5)]
incoming[B] = [(A, 5)]
```

여기서 **self-edge는 일반 out/in-edge에서 제외**한다.
왜냐하면, self-call은 재귀성을 나타내는 강한 신호라서 일반 callee pattern과 섞기 보다 seed feature로 따로 쓰는 게 더 명확하기 때문이다.

또 중요한 값 `distinct_out_callee_count`가 있다.
이 값은 어떠한 함수가 호출하는 **피호출자의 종류의 수**이다.

#### 2단계: initial color
관련 함수:
```python
make_initial_cg_wl_colors(case, view)
```

각 함수에 초기 색(color)를 주는 작업을 수행한다.

user node의 초기 색은 아래와 같다.
$$
c_{0}(v) = (\mathrm{selfCallCount}(v), \mathrm{distinctOutCalleeCount}(v))
$$
하지만 **anchor는** scored 산출에는 안 들어가지만 caller pattern엔 영향을 줘야하므로, 각 함수마다 다른 **고유한 색**으로 설정한다.

user node는 self-call count와 out-callee 종류 수로 색을 설정.
anchor는 각 함수마다 고유한 색을 설정.

#### 3단계: Relation refinement
관련 함수:
```python
refine_cg_wl_once(case, view, prev_colors)
```

engine의 핵심이다.

처음 색만 보면 self-call count와 out-call 종류로만 나누므로 너무 거칠다.
따라서 매 round마다 각 node의 signature를 새로 만든다.
$$
\mathrm{sig}_{t}(v) = (c_{t}(v), \mathrm{OutMuliset}_{t}(v), \mathrm{InMultiset}_{t}(v))
$$
$\mathrm{OutMultiset}_t$는 $t$ 시점의 {피호출 함수의 이전 색과 호출 횟수}의 집합, $\mathrm{InMultiset}_t$은 $t$ 시점의 {호출자 함수의 이전 색과 호출 횟수}의 집합이다.
$\mathrm{OutMultiset}$과 $\mathrm{InMultiset}$은 `_neighbor_color_multiset()`를 통해 수집된다.

Multiset의 원소들은 피호출 함수 혹은 호출자 함수의 이전 색이 수집되기 때문에, 만약 같은 색을 가진 두 개의 피호출 함수를 가지고 있다면 **그 호출 횟수는 합산**된다.

예:
```
함수 f의 색 = X
함수 g의 색 = X
함수 h의 색 = Y
```
라고 하고, A가 아래와 같이 호출할 때,
```
A -> f x2
A -> g x3
A -> h x1
```
그러면 raw address 기준으로는 함수가 3개지만, 이전 color 기준으로는 X, Y 두 가지이다.

따라서 함수 `f`와 `g`의 호출 횟수가 합산된다.
```
OUT(A) = {
	X: 5,
	Y: 1
}
```
이게 바로 `_neighbor_color_multiset()`의 역할이다.
호출자 함수도 고려하기에 같은 callee 구조라도, caller 구조가 다르면 갈라진다.

#### 4단계: Canonicalize signatures
관련 함수: 
```python
_canonicalize_signatures(signatures)
```

각 함수의 signature가 만들어지면, 같은 signature를 가진 함수는 같은 새 color를 받는다.

예:
```
sig(A) == sig(B)
sig(C) != sig(A)
```
->
```
A, B -> C:0
C    -> C:1 
```

색 이름 자체는 중요하지 않고, 색의 동일성만 중요하다.

#### 5단계: Fixpoint
관련 함수:
```python
run_cg_wl(case)
same_partition(...)
canonical_partition(...)
```

refinement를 진행할 때, 하위 callee가 먼저 갈라지고, 그 영향이 상위 caller로 전파될 수 있기 때문에, 한 번의 refinement로는 부족할 수 있다.

예:
```
share_i32
share_f64
share_Wide
```
중 `share_i32`만 leaf처럼 변하면 share layer가 먼저 갈라진다.
그다음 driver가 각각 다른 share color를 호출하게 되므로 driver layer도 갈라지게 된다.

따라서 이 결과를 반영하기 위해, partition이 refinement를 해도 변하지 않을 때까지 반복한다.
$$P_{t+1}= P_t$$
이면 종료이다.

코드에서는 색 문자열이 아닌 partition이 같은지를 본다.(전술한 색 이름이 중요하지 않다는 이유 때문에)
중요한 것은 색 이름이 아닌 같은 node가 같은 partition에 남아 있는지이다.

#### 6단계: print scored cluster
관련 함수: 
```python
make_scored_clusters(case, colors)
make_cluster_id_by_node(clusters)
```

최종 색이 정해지면 같은 색을 가진 node들을 cluster로 묶는다.

하지만 모든 node를 scoring 하진 않는다.
`scored=true`인 node만 cluster 출력에 포함한다.

그에 대한 예로 `anchor`를 들 수 있다. 
`anchor`는 색이 있어서 refinement에 영향을 줄 수 있지만, 최종 cluster 평가에서는 제외된다.

## 5. Ground Truth Path
non-stripped binary -> ground truth JSON
### 5.1 gt_extractor.py
non-stripped binary에서 symbol 정보를 읽어서 scoring에 사용할 ground truth JSON을 만든다.

입력: `gt_bin/~.gt.bin`
출력: `ground_truth/~.gt.json`

`gt_extractor.py`의 핵심 목적은 "어떤 함수들이 같은 source origin에서 나온 monomorphized instance인가"를 컴파일러가 남긴 symbol을 통해 복원하는 것이다.

여기서 중요한 점은 `gt_extractor.py`가 stripped binary를 보지 않는다는 것이다.
반대로 `binary_extractor.py`는 non-stripped symbol을 보지 않는다.

즉 두 경로가 분리되어 있다.
```
stripped binary      -> fixture JSON
non-stripped binary  -> ground truth JSON
```

이 분리가 있어야 engine이 origin label을 몰래 보고 grouping하는 문제가 생기지 않는다.

큰 흐름은 6단계로 나눌 수 있다.
```
1. nm으로 symbol 목록 추출
2. text function symbol만 선택
3. family_graph_* prefix에 해당하는 user symbol만 선택
4. symbol name에서 origin 추출
5. 같은 origin끼리 member grouping
6. ground truth JSON 작성
```

#### 1단계: nm으로 symbol 목록 추출
핵심 함수:
```python
run_nm(binary_path, nm_tool)
```

실제 실행은 아래와 같다.
```python
nm -n -C <binary>
```

`-n`은 주소순 정렬이다.
`-C`는 Rust symbol을 demangle해서 사람이 읽을 수 있는 이름으로 바꾼다.

예를 들어 raw symbol이 복잡한 mangled name이라도, `nm -C`를 거치면 대략 아래와 같은 형태로 나온다.
```
0000000000013fe0 t family_graph_03::share
0000000000014040 t family_graph_03::drive_x
```

이 단계에서 아직 grouping은 하지 않는다.
그냥 non-stripped binary 안에 어떤 symbol이 있는지 텍스트 라인으로 받아오는 단계다.

#### 2단계: text function symbol만 선택
핵심 함수:
```python
parse_nm_lines(lines)
```

`parse_nm_lines()`는 `nm` 출력 라인을 읽어서 `Symbol` 객체 목록으로 바꾼다.

```python
@dataclass(frozen=True)
class Symbol:
    addr: int
    kind: str
    name: str
```

여기서 `kind`가 `t` 또는 `T`인 symbol만 남긴다.

- `t`: local text symbol
- `T`: global text symbol

즉 함수 코드 주소로 볼 수 있는 symbol만 ground truth 후보로 삼는다.
data symbol, section symbol, debug symbol은 제외한다.

#### 3단계: case / build / prefix 추론
관련 함수:
```python
infer_prefix(binary_path)
infer_case(binary_path)
infer_build(binary_path)
```

현재 corpus는 파일 이름에 case 정보가 들어있다.

예:
```
gt_bin/family_graph_01.O3S.gt.bin
gt_bin/family_graph_03.O3KS.gt.bin
```

따라서 별도 option을 주지 않아도 아래 값을 추론할 수 있다.

```
family_graph_01.O3S.gt.bin  -> case=family_graph_01, build=O3S,  prefix=family_graph_01::
family_graph_03.O3KS.gt.bin -> case=family_graph_03, build=O3KS, prefix=family_graph_03::
```

`prefix`가 중요한 이유는 user가 작성한 실험 함수만 골라야 하기 때문이다.
Rust binary에는 std, runtime, panic, allocator 관련 symbol이 같이 들어있을 수 있다.
하지만 ground truth는 `family_graph_01::` 같은 실험 crate symbol만 대상으로 한다.

#### 4단계: symbol name에서 origin 추출
핵심 함수:
```python
origin_from_symbol(demangled_name, prefix)
strip_rust_generic_args(name)
```

`origin_from_symbol()`은 demangled symbol name이 실험 prefix로 시작하는지 확인한다.

예:
```
family_graph_03::share
```

prefix인 `family_graph_03::`을 제거하면 origin은 아래처럼 된다.
```
share
```

이 origin이 ground truth의 grouping key가 된다.

즉 아래 세 함수가 non-stripped symbol에서 모두 `family_graph_03::share` origin으로 나오면,
이 세 함수는 같은 source definition에서 나온 instance로 간주된다.
```
share::<i32>
share::<f64>
share::<Wide>
```

현재 legacy Rust mangling에서는 type argument가 demangle 결과에 보이지 않는 경우가 많다.
그래도 v0 mangling처럼 `foo::<T>` 형태가 나올 수 있으므로, `strip_rust_generic_args()`가 `::<...>` 부분을 제거한다.

이 규칙의 의미는 다음과 같다.

```
source path는 같고 type argument만 다른 함수들
->
같은 generic origin
```

반대로 `main`은 ground truth member에서 제외한다.
`main`은 engine에서 anchor/root 역할을 할 수는 있지만, generic family scoring 대상은 아니기 때문이다.

#### 5단계: 같은 origin끼리 member grouping
핵심 함수:
```python
make_ground_truth(...)
function_id(addr, id_bias=0x100000)
```

`make_ground_truth()`가 실제 ground truth JSON 내용을 만든다.

먼저 symbol 주소를 fixture에서 쓰는 함수 ID 형태로 바꾼다.
```python
FUN_00113fe0
```

이 변환은 아래 함수가 담당한다.
```python
function_id(addr, id_bias=0x100000)
```

즉 raw symbol address에 `0x100000` bias를 더해 Ghidra/radare2 fixture에서 쓰는 `FUN_...` 형식과 맞춘다.

그다음 같은 origin을 가진 member를 같은 group에 넣는다.

예:
```json
{
  "origin": "share",
  "members": [
    "FUN_00145a23",
    "FUN_00145a81",
    "FUN_0014e7a3"
  ]
}
```

ground truth origin group에는 source-level kind label을 넣지 않는다.
현재 scoring에 필요한 partition 정보는 "같은 origin인가"뿐이므로 `origin`과 `members`가 기준이다.
다만 최종 리포트에서 instance를 읽기 쉽게 확인하기 위해 top-level `symbols` map에 각 member id의 원본 demangled symbol을 보존한다.
generic/concrete/decoy 같은 해석 라벨은 compiler-derived partition 자체가 아니므로 GT schema에서 제거했다.

#### 6단계: address alias / duplicate 처리
관련 코드:
```python
owner_by_member
alias_notes
```

같은 주소에 여러 symbol이 붙는 경우가 있을 수 있다.
예를 들어 compiler/linker 최적화 때문에 두 symbol이 같은 함수 body 주소를 공유할 수 있다.

이때 ground truth member를 중복으로 넣으면 같은 함수 ID가 여러 origin에 들어갈 수 있다.
그러면 scoring universe가 깨진다.

따라서 `make_ground_truth()`는 두 경우를 나눈다.
같은 origin의 duplicate symbol이면 한 번만 유지하고 `note`에 기록한다.
하지만 서로 다른 origin이 같은 주소를 공유하면 GT 생성을 중단한다.
이 경우 어느 origin을 정답으로 남길지 자동 선택하면 정답지가 오염되기 때문이다.

예:
```json
{
  "note": "address aliases/duplicates: FUN_00114020: duplicate symbol for origin ..."
}
```

즉 현재 정책은 이렇다.

```
한 주소 = 한 member
same-origin duplicate = note에 기록
cross-origin alias = fail
```

#### 7단계: fixture universe 검증
핵심 함수:
```python
validate_against_fixture(gt, fixture_path)
```

`--fixture` option을 주면 생성한 ground truth의 member set과 fixture의 scored node set이 같은지 확인한다.

검사하는 것은 아래 둘의 일치다.

```
fixture에서 scored=true인 node id 전체
ground truth origins 안의 member id 전체
```

이 검증은 아주 중요하다.
왜냐하면 scoring은 두 universe가 같다는 전제에서만 의미가 있기 때문이다.

예를 들어 fixture에는 함수 10개가 scored인데, ground truth에는 9개만 있으면 pairwise 계산 자체가 다른 함수 집합 위에서 수행된다.
그러면 P/R/F1/ARI 값은 연구 결과로 쓸 수 없다.

다만 이 검증은 "주소 집합이 같은가"를 보는 것이지, "origin partition이 맞는가"를 증명하는 것은 아니다.
따라서 symbol mangling 방식이나 origin normalization 규칙은 별도로 고정해야 한다.

#### 8단계: JSON 작성과 CLI
핵심 함수:
```python
write_json(data, output_path)
main(argv)
```

기본 사용 형태는 아래와 같다.

```bash
python3 gt_extractor.py gt_bin/family_graph_01.gt.bin ground_truth/fg01_auto.gt.json
```

fixture universe까지 검증하려면 아래처럼 실행한다.

```bash
python3 gt_extractor.py \
  gt_bin/family_graph_01.gt.bin \
  ground_truth/fg01_auto.gt.json \
  --fixture fixtures/fg01_auto.fixture.json
```

정리하면 `gt_extractor.py`는 engine을 위한 입력을 만드는 파일이 아니다.
engine 결과를 나중에 채점하기 위한 정답 partition을 만드는 파일이다.

```
symbol address + demangled origin
->
ground truth origin partition
```

## 6. Scoring Path
predicted cluster + ground truth -> predicted clusters / TP/FP/FN / Precision/Recall/F1-score/ARI

### 6.1 scores.py
`scores.py`는 engine이 만든 predicted cluster와 ground truth origin partition을 비교해서 점수를 계산한다.

입력:
- fixture JSON
- ground truth JSON

출력:
- predicted clusters
- TP / FP / FN
- Precision / Recall / F1
- ARI

큰 흐름은 7단계이다.

```
1. fixture JSON 읽기
2. ground truth JSON 읽기
3. 두 universe가 같은지 검사
4. CG-WL engine 실행
5. 모든 scored 함수 쌍을 비교
6. P/R/F1/ARI 계산
7. predicted clusters와 score 출력
```

#### 1단계: ground truth model
관련 class:
```python
OriginGroup
GroundTruth
```

ground truth JSON의 한 origin group은 아래와 같다.

```json
{
  "origin": "share",
  "members": [
    "FUN_00145a23",
    "FUN_00145a81",
    "FUN_0014e7a3"
  ]
}
```

이것은 Python 내부에서 아래 dataclass로 바뀐다.

```python
@dataclass(frozen=True)
class OriginGroup:
    origin: str
    members: tuple[str, ...]
```

`GroundTruth`는 전체 origin 목록을 들고 있다.

```python
@dataclass(frozen=True)
class GroundTruth:
    case: str
    build: str
    schema_version: int
    origins: tuple[OriginGroup, ...]
    symbols: dict[str, tuple[str, ...]]
```

여기서 중요한 helper는 하나다.

```python
origin_of()
```

`origin_of()`는 member id에서 origin 이름을 찾기 위한 map을 만든다.

예:
```python
{
  "FUN_00145a23": "share",
  "FUN_00145a81": "share",
  "FUN_0014e7a3": "share",
}
```

#### 2단계: ground truth validation
핵심 함수:
```python
load_ground_truth(path)
_validate_ground_truth(data)
```

`load_ground_truth()`는 JSON을 읽고, `_validate_ground_truth()`를 통과한 뒤 `GroundTruth` 객체로 바꾼다.

검증 규칙은 다음과 같다.

- top-level field가 `case`, `build`, `schema_version`, `origins`, `symbols`를 갖는가
- `schema_version`이 3인가
- origin 이름이 중복되지 않는가
- members가 비어있지 않은가
- 같은 member id가 둘 이상의 origin에 들어가지 않는가
- `symbols` key가 ground truth member 전체와 정확히 같은가

이 단계는 scoring이 틀어진 ground truth 위에서 실행되는 것을 막는 gatekeeper이다.

#### 3단계: fixture와 ground truth join 검사
핵심 함수:
```python
_check_join(case, gt)
```

`scores.py`는 두 개의 독립 입력을 합친다.

```
fixture JSON       = engine 입력
ground truth JSON  = scoring 정답
```

따라서 두 파일이 같은 case/build인지 먼저 확인한다.

```
fixture.case == gt.case
fixture.build == gt.build
```

그 다음 scored universe를 확인한다.

```
fixture의 scored=true node id 집합
==
ground truth의 모든 member id 집합
```

이게 맞지 않으면 scoring을 중단한다.
같은 함수 집합 위에서 predicted partition과 true partition을 비교해야 하기 때문이다.

#### 4단계: CG-WL engine 실행
핵심 함수:
```python
score_case(fixture_path, ground_truth_path)
run_cg_wl(case)
```

`score_case()`가 scoring 전체의 중심 함수다.

처음에는 fixture와 ground truth를 읽는다.

```python
case = load_case(fixture_path)
gt = load_ground_truth(ground_truth_path)
```

그 다음 engine을 실행한다.

```python
result = run_cg_wl(case)
```

여기서 `scores.py`는 engine 내부 알고리즘을 다시 구현하지 않는다.
항상 `engine.py`의 `run_cg_wl()` 결과를 가져와서 채점한다.

engine 결과 중 scoring에 필요한 것은 아래 map이다.

```python
cluster_of = result.cluster_id_by_node
```

예:
```python
{
  "FUN_00145a23": 0,
  "FUN_00145a81": 0,
  "FUN_0014e7a3": 0,
  "FUN_00152e20": 1,
}
```

이 map은 predicted partition이다.
같은 cluster id를 가진 함수들은 CG-WL이 같은 묶음으로 본 것이다.

#### 5단계: 모든 scored 함수 쌍 비교
핵심 코드:
```python
for a, b in combinations(scored_ids, 2):
```

채점은 함수 하나 단위가 아니라 함수 쌍(pair) 단위로 한다.

각 pair에 대해 두 가지 질문을 한다.

```
1. CG-WL은 두 함수를 같은 cluster로 묶었는가?
2. ground truth는 두 함수를 같은 origin으로 보는가?
```

코드에서는 아래처럼 계산한다.

```python
pred_same = cluster_of[a] == cluster_of[b]
true_same = origin_of[a] == origin_of[b]
```

이 두 boolean의 조합이 TP/FP/FN/TN이 된다.

```
pred_same=True,  true_same=True   -> TP
pred_same=True,  true_same=False  -> FP
pred_same=False, true_same=True   -> FN
pred_same=False, true_same=False  -> TN
```

의미는 다음과 같다.

- **TP**: 같은 origin인 두 함수를 같은 cluster로 묶었다.
- **FP**: 다른 origin인 두 함수를 같은 cluster로 잘못 묶었다.
- **FN**: 같은 origin인 두 함수를 서로 다른 cluster로 갈라버렸다.
- **TN**: 다른 origin인 두 함수를 서로 다른 cluster로 두었다.

이 연구에서 FP는 precision 문제다.
다른 origin을 잘못 합쳤다는 뜻이다.

FN은 recall 문제다.
같은 origin이 inlining, relation 차이, propagation 차이 때문에 쪼개졌다는 뜻이다.

#### 6단계: Precision / Recall / F1
핵심 함수:
```python
_pairwise_score(tp, fp, fn, tn)
```

Precision은 "묶었다고 주장한 pair 중에서 진짜 같은 origin인 비율"이다.

$$
\mathrm{Precision} = \frac{TP}{TP+FP}
$$

Recall은 "진짜 같은 origin pair 중에서 실제로 묶어낸 비율"이다.

$$
\mathrm{Recall} = \frac{TP}{TP+FN}
$$

F1은 precision과 recall의 조화평균이다.

$$
F1 = \frac{2PR}{P+R}
$$

코드에서는 분모가 0일 때를 방어한다.

```python
precision = tp / (tp + fp) if (tp + fp) else 1.0
recall = tp / (tp + fn) if (tp + fn) else 1.0
```

여기서 `1.0` 처리는 "비교할 positive pair가 없는 trivial case"를 위한 방어값이다.
현재 fg01/02/03에서는 실제 pair가 있으므로 보통 이 예외가 핵심은 아니다.

#### 7단계: ARI
핵심 함수:
```python
_adjusted_rand_index(tp, fp, fn, tn)
```

ARI는 전체 partition이 얼마나 비슷한지 보는 지표다.
Precision/Recall/F1은 positive pair에 집중하지만, ARI는 전체 pair 구조를 chance-adjusted 방식으로 본다.

코드에서는 pairwise count로 ARI를 계산한다.

```python
index = tp
same_cluster = tp + fp
same_origin = tp + fn
total = tp + fp + fn + tn
```

각 값의 의미는 다음과 같다.

```
index        = predicted도 same, truth도 same인 pair 수 = TP
same_cluster = predicted가 same이라고 본 pair 수 = TP + FP
same_origin  = truth가 same이라고 본 pair 수 = TP + FN
total        = 전체 pair 수 = TP + FP + FN + TN
```

expected는 우연히 같은 partition agreement가 나올 기대값이다.

```python
expected = same_cluster * same_origin / total
```

maximum은 두 partition이 만들 수 있는 최대 agreement의 기준값이다.

```python
maximum = 0.5 * (same_cluster + same_origin)
```

최종 ARI는 아래와 같다.

$$
ARI = \frac{index - expected}{maximum - expected}
$$

따라서 ARI는 단순히 TP가 많다고 높아지는 값이 아니다.
predicted cluster 크기와 true origin 크기까지 같이 반영한다.

#### 8단계: report 출력
핵심 함수:
```python
format_report(r)
main(argv)
```

CLI 사용은 아래와 같다.

```bash
python3 scores.py fixtures/fg03_auto.fixture.json ground_truth/fg03_auto.gt.json
```

출력은 대략 아래 형태다.

```text
case : fg03 / O3S
predicted clusters:
  C1 = ['FUN_00145a83', 'FUN_00145ae1']
  C2 = ['FUN_0014e803']
symbols:
  C1 = ['share::<i32>', 'share::<u64>']
  C2 = ['decoy_a']
TP=4 FP=1 FN=6
PR=0.80 RE=0.40 F1=0.53 ARI=0.49
```

정리하면 `scores.py`는 아래 연결을 담당한다.

```
engine.py predicted cluster
ground_truth/*.gt.json true origin partition
->
pairwise P/R/F1/ARI
```

그리고 이 파일의 핵심 원칙은 하나다.

```
engine은 origin을 모른다.
scorer만 origin을 본다.
```
