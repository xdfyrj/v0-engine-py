# Measurement Evidence

This report contains observed values only: origin membership, anchor context, per-instance Axis-1 relations, CG-WL round partitions, family rows, predicted clusters, collisions, and pairwise scores. It intentionally omits diagnosis, conclusions, source-level census, and coverage.

## family_graph_01 / O3S / mode=full

### Inputs

```text
fixture: fixtures/family_graph_01.O3S.fixture.json
ground truth: ground_truth/family_graph_01.O3S.gt.json
```

### Origins

| case | build | origin | k_obs | members | symbols |
|---|---|---|---|---|---|
| family_graph_01 | O3S | shared_recursive | 3 | FUN_00113e20;FUN_00113f00;FUN_00113f80 | shared_recursive;shared_recursive;shared_recursive |
| family_graph_01 | O3S | process | 3 | FUN_00114460;FUN_00114640;FUN_00114880 | process;process;process |

### Anchors

| case | build | anchor | role | out | in |
|---|---|---|---|---|---|
| family_graph_01 | O3S | FUN_00114020 | anchor:root | FUN_00113e20(shared_recursive)*2; FUN_00113f00(shared_recursive)*2; FUN_00113f80(shared_recursive)*2; FUN_00114460(process)*2; FUN_00114640(process)*2; FUN_00114880(process)*2 | - |

### Instance Relations

| case | build | origin | member | symbol | self_call_count | distinct_out_callee_count | distinct_in_caller_count | out_edges | out_by_label | in_edges | in_by_label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_01 | O3S | shared_recursive | FUN_00113e20 | shared_recursive | 1 | 0 | 2 | - | - | FUN_00114020(anchor:root)*2; FUN_00114880(process)*5 | anchor:root*2; process*5 |
| family_graph_01 | O3S | shared_recursive | FUN_00113f00 | shared_recursive | 1 | 0 | 2 | - | - | FUN_00114020(anchor:root)*2; FUN_00114460(process)*5 | anchor:root*2; process*5 |
| family_graph_01 | O3S | shared_recursive | FUN_00113f80 | shared_recursive | 1 | 0 | 2 | - | - | FUN_00114020(anchor:root)*2; FUN_00114640(process)*5 | anchor:root*2; process*5 |
| family_graph_01 | O3S | process | FUN_00114460 | process | 0 | 1 | 1 | FUN_00113f00(shared_recursive)*5 | shared_recursive*5 | FUN_00114020(anchor:root)*2 | anchor:root*2 |
| family_graph_01 | O3S | process | FUN_00114640 | process | 0 | 1 | 1 | FUN_00113f80(shared_recursive)*5 | shared_recursive*5 | FUN_00114020(anchor:root)*2 | anchor:root*2 |
| family_graph_01 | O3S | process | FUN_00114880 | process | 0 | 1 | 1 | FUN_00113e20(shared_recursive)*5 | shared_recursive*5 | FUN_00114020(anchor:root)*2 | anchor:root*2 |

### Round Partitions

| case | build | mode | round | num_classes | classes | split_this_round |
|---|---|---|---|---|---|---|
| family_graph_01 | O3S | full | 0 | 2 | {shared_recursive*3} {process*3} | - |

### Round Signatures

| case | build | mode | from_round | member | origin | previous_class | out_color_multiset | in_color_multiset | used_signature | next_class | partition_changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_01 | O3S | full | 0 | FUN_00113e20 | shared_recursive | R0C1 | - | R0C2*5; anchor:root*2 | prev=R0C1; out=-; in=R0C2*5; anchor:root*2 | R1C1 | False |
| family_graph_01 | O3S | full | 0 | FUN_00113f00 | shared_recursive | R0C1 | - | R0C2*5; anchor:root*2 | prev=R0C1; out=-; in=R0C2*5; anchor:root*2 | R1C1 | False |
| family_graph_01 | O3S | full | 0 | FUN_00113f80 | shared_recursive | R0C1 | - | R0C2*5; anchor:root*2 | prev=R0C1; out=-; in=R0C2*5; anchor:root*2 | R1C1 | False |
| family_graph_01 | O3S | full | 0 | FUN_00114460 | process | R0C2 | R0C1*5 | anchor:root*2 | prev=R0C2; out=R0C1*5; in=anchor:root*2 | R1C2 | False |
| family_graph_01 | O3S | full | 0 | FUN_00114640 | process | R0C2 | R0C1*5 | anchor:root*2 | prev=R0C2; out=R0C1*5; in=anchor:root*2 | R1C2 | False |
| family_graph_01 | O3S | full | 0 | FUN_00114880 | process | R0C2 | R0C1*5 | anchor:root*2 | prev=R0C2; out=R0C1*5; in=anchor:root*2 | R1C2 | False |

### Family Rows

| case | build | mode | origin | k_obs | d_star | num_predicted_clusters | family_pair_recall | collision_with | observed_relation_patterns |
|---|---|---|---|---|---|---|---|---|---|
| family_graph_01 | O3S | full | shared_recursive | 3 | - | 1 | 3/3=1.00 | - | 3*[self=1; dout=0; din=2; out=-; in=anchor:root*2; process*5] |
| family_graph_01 | O3S | full | process | 3 | - | 1 | 3/3=1.00 | - | 3*[self=0; dout=1; din=1; out=shared_recursive*5; in=anchor:root*2] |

### Predicted Clusters

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_01 | O3S | full | C1 | FUN_00113e20;FUN_00113f00;FUN_00113f80 | shared_recursive;shared_recursive;shared_recursive | shared_recursive | 3*[self=1; dout=0; din=2; out=-; in=anchor:root*2; process*5] |
| family_graph_01 | O3S | full | C2 | FUN_00114460;FUN_00114640;FUN_00114880 | process;process;process | process | 3*[self=0; dout=1; din=1; out=shared_recursive*5; in=anchor:root*2] |

### Scores

| case | build | mode | engine_rounds | effective_rounds | TP | FP | FN | TN | precision | recall | F1 | ARI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_01 | O3S | full | 1 | 0 | 6 | 0 | 0 | 9 | 1.00 | 1.00 | 1.00 | 1.00 |

## family_graph_02 / O3S / mode=full

### Inputs

```text
fixture: fixtures/family_graph_02.O3S.fixture.json
ground truth: ground_truth/family_graph_02.O3S.gt.json
```

### Origins

| case | build | origin | k_obs | members | symbols |
|---|---|---|---|---|---|
| family_graph_02 | O3S | process_beta | 2 | FUN_00113fd0;FUN_001140f0 | process_beta;process_beta |
| family_graph_02 | O3S | recurse_beta | 2 | FUN_00114350;FUN_001144d0 | recurse_beta;recurse_beta |
| family_graph_02 | O3S | process_alpha | 2 | FUN_00114590;FUN_001147f0 | process_alpha;process_alpha |
| family_graph_02 | O3S | recurse_alpha | 2 | FUN_00114910;FUN_001149a0 | recurse_alpha;recurse_alpha |
| family_graph_02 | O3S | c_process_alpha_i32 | 1 | FUN_00114ac0 | c_process_alpha_i32 |
| family_graph_02 | O3S | c_recurse_alpha_i32 | 1 | FUN_00114be0 | c_recurse_alpha_i32 |
| family_graph_02 | O3S | c_process_alpha_wide | 1 | FUN_00114c70 | c_process_alpha_wide |
| family_graph_02 | O3S | c_recurse_alpha_wide | 1 | FUN_00114ee0 | c_recurse_alpha_wide |

### Anchors

| case | build | anchor | role | out | in |
|---|---|---|---|---|---|
| family_graph_02 | O3S | FUN_00115000 | anchor:root | FUN_00113fd0(process_beta)*2; FUN_001140f0(process_beta)*2; FUN_00114590(process_alpha)*2; FUN_001147f0(process_alpha)*2; FUN_00114ac0(c_process_alpha_i32)*2; FUN_00114c70(c_process_alpha_wide)*2 | - |

### Instance Relations

| case | build | origin | member | symbol | self_call_count | distinct_out_callee_count | distinct_in_caller_count | out_edges | out_by_label | in_edges | in_by_label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_02 | O3S | process_beta | FUN_00113fd0 | process_beta | 0 | 1 | 1 | FUN_001144d0(recurse_beta)*5 | recurse_beta*5 | FUN_00115000(anchor:root)*2 | anchor:root*2 |
| family_graph_02 | O3S | process_beta | FUN_001140f0 | process_beta | 0 | 1 | 1 | FUN_00114350(recurse_beta)*5 | recurse_beta*5 | FUN_00115000(anchor:root)*2 | anchor:root*2 |
| family_graph_02 | O3S | recurse_beta | FUN_00114350 | recurse_beta | 2 | 0 | 1 | - | - | FUN_001140f0(process_beta)*5 | process_beta*5 |
| family_graph_02 | O3S | recurse_beta | FUN_001144d0 | recurse_beta | 2 | 0 | 1 | - | - | FUN_00113fd0(process_beta)*5 | process_beta*5 |
| family_graph_02 | O3S | process_alpha | FUN_00114590 | process_alpha | 0 | 1 | 1 | FUN_001149a0(recurse_alpha)*5 | recurse_alpha*5 | FUN_00115000(anchor:root)*2 | anchor:root*2 |
| family_graph_02 | O3S | process_alpha | FUN_001147f0 | process_alpha | 0 | 1 | 1 | FUN_00114910(recurse_alpha)*5 | recurse_alpha*5 | FUN_00115000(anchor:root)*2 | anchor:root*2 |
| family_graph_02 | O3S | recurse_alpha | FUN_00114910 | recurse_alpha | 1 | 0 | 1 | - | - | FUN_001147f0(process_alpha)*5 | process_alpha*5 |
| family_graph_02 | O3S | recurse_alpha | FUN_001149a0 | recurse_alpha | 1 | 0 | 1 | - | - | FUN_00114590(process_alpha)*5 | process_alpha*5 |
| family_graph_02 | O3S | c_process_alpha_i32 | FUN_00114ac0 | c_process_alpha_i32 | 0 | 1 | 1 | FUN_00114be0(c_recurse_alpha_i32)*5 | c_recurse_alpha_i32*5 | FUN_00115000(anchor:root)*2 | anchor:root*2 |
| family_graph_02 | O3S | c_recurse_alpha_i32 | FUN_00114be0 | c_recurse_alpha_i32 | 1 | 0 | 1 | - | - | FUN_00114ac0(c_process_alpha_i32)*5 | c_process_alpha_i32*5 |
| family_graph_02 | O3S | c_process_alpha_wide | FUN_00114c70 | c_process_alpha_wide | 0 | 1 | 1 | FUN_00114ee0(c_recurse_alpha_wide)*5 | c_recurse_alpha_wide*5 | FUN_00115000(anchor:root)*2 | anchor:root*2 |
| family_graph_02 | O3S | c_recurse_alpha_wide | FUN_00114ee0 | c_recurse_alpha_wide | 1 | 0 | 1 | - | - | FUN_00114c70(c_process_alpha_wide)*5 | c_process_alpha_wide*5 |

### Round Partitions

| case | build | mode | round | num_classes | classes | split_this_round |
|---|---|---|---|---|---|---|
| family_graph_02 | O3S | full | 0 | 3 | {c_process_alpha_i32, c_process_alpha_wide, process_alpha*2, process_beta*2} {recurse_beta*2} {c_recurse_alpha_i32, c_recurse_alpha_wide, recurse_alpha*2} | - |
| family_graph_02 | O3S | full | 1 | 4 | {process_beta*2} {recurse_beta*2} {c_process_alpha_i32, c_process_alpha_wide, process_alpha*2} {c_recurse_alpha_i32, c_recurse_alpha_wide, recurse_alpha*2} | - |

### Round Signatures

| case | build | mode | from_round | member | origin | previous_class | out_color_multiset | in_color_multiset | used_signature | next_class | partition_changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_02 | O3S | full | 0 | FUN_00113fd0 | process_beta | R0C1 | R0C2*5 | anchor:root*2 | prev=R0C1; out=R0C2*5; in=anchor:root*2 | R1C1 | True |
| family_graph_02 | O3S | full | 0 | FUN_001140f0 | process_beta | R0C1 | R0C2*5 | anchor:root*2 | prev=R0C1; out=R0C2*5; in=anchor:root*2 | R1C1 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114350 | recurse_beta | R0C2 | - | R0C1*5 | prev=R0C2; out=-; in=R0C1*5 | R1C2 | True |
| family_graph_02 | O3S | full | 0 | FUN_001144d0 | recurse_beta | R0C2 | - | R0C1*5 | prev=R0C2; out=-; in=R0C1*5 | R1C2 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114590 | process_alpha | R0C1 | R0C3*5 | anchor:root*2 | prev=R0C1; out=R0C3*5; in=anchor:root*2 | R1C3 | True |
| family_graph_02 | O3S | full | 0 | FUN_001147f0 | process_alpha | R0C1 | R0C3*5 | anchor:root*2 | prev=R0C1; out=R0C3*5; in=anchor:root*2 | R1C3 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114910 | recurse_alpha | R0C3 | - | R0C1*5 | prev=R0C3; out=-; in=R0C1*5 | R1C4 | True |
| family_graph_02 | O3S | full | 0 | FUN_001149a0 | recurse_alpha | R0C3 | - | R0C1*5 | prev=R0C3; out=-; in=R0C1*5 | R1C4 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114ac0 | c_process_alpha_i32 | R0C1 | R0C3*5 | anchor:root*2 | prev=R0C1; out=R0C3*5; in=anchor:root*2 | R1C3 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114be0 | c_recurse_alpha_i32 | R0C3 | - | R0C1*5 | prev=R0C3; out=-; in=R0C1*5 | R1C4 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114c70 | c_process_alpha_wide | R0C1 | R0C3*5 | anchor:root*2 | prev=R0C1; out=R0C3*5; in=anchor:root*2 | R1C3 | True |
| family_graph_02 | O3S | full | 0 | FUN_00114ee0 | c_recurse_alpha_wide | R0C3 | - | R0C1*5 | prev=R0C3; out=-; in=R0C1*5 | R1C4 | True |
| family_graph_02 | O3S | full | 1 | FUN_00113fd0 | process_beta | R1C1 | R1C2*5 | anchor:root*2 | prev=R1C1; out=R1C2*5; in=anchor:root*2 | R2C1 | False |
| family_graph_02 | O3S | full | 1 | FUN_001140f0 | process_beta | R1C1 | R1C2*5 | anchor:root*2 | prev=R1C1; out=R1C2*5; in=anchor:root*2 | R2C1 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114350 | recurse_beta | R1C2 | - | R1C1*5 | prev=R1C2; out=-; in=R1C1*5 | R2C2 | False |
| family_graph_02 | O3S | full | 1 | FUN_001144d0 | recurse_beta | R1C2 | - | R1C1*5 | prev=R1C2; out=-; in=R1C1*5 | R2C2 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114590 | process_alpha | R1C3 | R1C4*5 | anchor:root*2 | prev=R1C3; out=R1C4*5; in=anchor:root*2 | R2C3 | False |
| family_graph_02 | O3S | full | 1 | FUN_001147f0 | process_alpha | R1C3 | R1C4*5 | anchor:root*2 | prev=R1C3; out=R1C4*5; in=anchor:root*2 | R2C3 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114910 | recurse_alpha | R1C4 | - | R1C3*5 | prev=R1C4; out=-; in=R1C3*5 | R2C4 | False |
| family_graph_02 | O3S | full | 1 | FUN_001149a0 | recurse_alpha | R1C4 | - | R1C3*5 | prev=R1C4; out=-; in=R1C3*5 | R2C4 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114ac0 | c_process_alpha_i32 | R1C3 | R1C4*5 | anchor:root*2 | prev=R1C3; out=R1C4*5; in=anchor:root*2 | R2C3 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114be0 | c_recurse_alpha_i32 | R1C4 | - | R1C3*5 | prev=R1C4; out=-; in=R1C3*5 | R2C4 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114c70 | c_process_alpha_wide | R1C3 | R1C4*5 | anchor:root*2 | prev=R1C3; out=R1C4*5; in=anchor:root*2 | R2C3 | False |
| family_graph_02 | O3S | full | 1 | FUN_00114ee0 | c_recurse_alpha_wide | R1C4 | - | R1C3*5 | prev=R1C4; out=-; in=R1C3*5 | R2C4 | False |

### Family Rows

| case | build | mode | origin | k_obs | d_star | num_predicted_clusters | family_pair_recall | collision_with | observed_relation_patterns |
|---|---|---|---|---|---|---|---|---|---|
| family_graph_02 | O3S | full | process_beta | 2 | - | 1 | 1/1=1.00 | - | 2*[self=0; dout=1; din=1; out=recurse_beta*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | recurse_beta | 2 | - | 1 | 1/1=1.00 | - | 2*[self=2; dout=0; din=1; out=-; in=process_beta*5] |
| family_graph_02 | O3S | full | process_alpha | 2 | - | 1 | 1/1=1.00 | c_process_alpha_i32;c_process_alpha_wide | 2*[self=0; dout=1; din=1; out=recurse_alpha*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | recurse_alpha | 2 | - | 1 | 1/1=1.00 | c_recurse_alpha_i32;c_recurse_alpha_wide | 2*[self=1; dout=0; din=1; out=-; in=process_alpha*5] |
| family_graph_02 | O3S | full | c_process_alpha_i32 | 1 | - | 1 | n/a | c_process_alpha_wide;process_alpha | 1*[self=0; dout=1; din=1; out=c_recurse_alpha_i32*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | c_recurse_alpha_i32 | 1 | - | 1 | n/a | c_recurse_alpha_wide;recurse_alpha | 1*[self=1; dout=0; din=1; out=-; in=c_process_alpha_i32*5] |
| family_graph_02 | O3S | full | c_process_alpha_wide | 1 | - | 1 | n/a | c_process_alpha_i32;process_alpha | 1*[self=0; dout=1; din=1; out=c_recurse_alpha_wide*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | c_recurse_alpha_wide | 1 | - | 1 | n/a | c_recurse_alpha_i32;recurse_alpha | 1*[self=1; dout=0; din=1; out=-; in=c_process_alpha_wide*5] |

### Predicted Clusters

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_02 | O3S | full | C1 | FUN_00113fd0;FUN_001140f0 | process_beta;process_beta | process_beta | 2*[self=0; dout=1; din=1; out=recurse_beta*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | C2 | FUN_00114350;FUN_001144d0 | recurse_beta;recurse_beta | recurse_beta | 2*[self=2; dout=0; din=1; out=-; in=process_beta*5] |
| family_graph_02 | O3S | full | C3 | FUN_00114590;FUN_001147f0;FUN_00114ac0;FUN_00114c70 | process_alpha;process_alpha;c_process_alpha_i32;c_process_alpha_wide | c_process_alpha_i32;c_process_alpha_wide;process_alpha | 2*[self=0; dout=1; din=1; out=recurse_alpha*5; in=anchor:root*2] \| 1*[self=0; dout=1; din=1; out=c_recurse_alpha_i32*5; in=anchor:root*2] \| 1*[self=0; dout=1; din=1; out=c_recurse_alpha_wide*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | C4 | FUN_00114910;FUN_001149a0;FUN_00114be0;FUN_00114ee0 | recurse_alpha;recurse_alpha;c_recurse_alpha_i32;c_recurse_alpha_wide | c_recurse_alpha_i32;c_recurse_alpha_wide;recurse_alpha | 2*[self=1; dout=0; din=1; out=-; in=process_alpha*5] \| 1*[self=1; dout=0; din=1; out=-; in=c_process_alpha_i32*5] \| 1*[self=1; dout=0; din=1; out=-; in=c_process_alpha_wide*5] |

### Collision Candidates

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_02 | O3S | full | C3 | FUN_00114590;FUN_001147f0;FUN_00114ac0;FUN_00114c70 | process_alpha;process_alpha;c_process_alpha_i32;c_process_alpha_wide | c_process_alpha_i32;c_process_alpha_wide;process_alpha | 2*[self=0; dout=1; din=1; out=recurse_alpha*5; in=anchor:root*2] \| 1*[self=0; dout=1; din=1; out=c_recurse_alpha_i32*5; in=anchor:root*2] \| 1*[self=0; dout=1; din=1; out=c_recurse_alpha_wide*5; in=anchor:root*2] |
| family_graph_02 | O3S | full | C4 | FUN_00114910;FUN_001149a0;FUN_00114be0;FUN_00114ee0 | recurse_alpha;recurse_alpha;c_recurse_alpha_i32;c_recurse_alpha_wide | c_recurse_alpha_i32;c_recurse_alpha_wide;recurse_alpha | 2*[self=1; dout=0; din=1; out=-; in=process_alpha*5] \| 1*[self=1; dout=0; din=1; out=-; in=c_process_alpha_i32*5] \| 1*[self=1; dout=0; din=1; out=-; in=c_process_alpha_wide*5] |

### Scores

| case | build | mode | engine_rounds | effective_rounds | TP | FP | FN | TN | precision | recall | F1 | ARI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_02 | O3S | full | 2 | 1 | 4 | 10 | 0 | 52 | 0.29 | 1.00 | 0.44 | 0.39 |

## family_graph_03 / O3S / mode=full

### Inputs

```text
fixture: fixtures/family_graph_03.O3S.fixture.json
ground truth: ground_truth/family_graph_03.O3S.gt.json
```

### Origins

| case | build | origin | k_obs | members | symbols |
|---|---|---|---|---|---|
| family_graph_03 | O3S | share | 3 | FUN_00114690;FUN_00114a10;FUN_00114d70 | share;share;share |
| family_graph_03 | O3S | leaf_p | 2 | FUN_00115260;FUN_001154d0 | leaf_p;leaf_p |
| family_graph_03 | O3S | decoy_a | 1 | FUN_001156e0 | decoy_a |
| family_graph_03 | O3S | decoy_b | 1 | FUN_001157e0 | decoy_b |
| family_graph_03 | O3S | drive_x | 3 | FUN_00115960;FUN_00115bb0;FUN_00115e70 | drive_x;drive_x;drive_x |
| family_graph_03 | O3S | drive_y | 3 | FUN_00116000;FUN_00116330;FUN_00116590 | drive_y;drive_y;drive_y |

### Anchors

| case | build | anchor | role | out | in |
|---|---|---|---|---|---|
| family_graph_03 | O3S | FUN_00113fe0 | anchor:root | FUN_001156e0(decoy_a)*2; FUN_001157e0(decoy_b)*2; FUN_00115960(drive_x)*2; FUN_00115bb0(drive_x)*2; FUN_00115e70(drive_x)*2; FUN_00116000(drive_y)*2; FUN_00116330(drive_y)*2; FUN_00116590(drive_y)*2 | - |

### Instance Relations

| case | build | origin | member | symbol | self_call_count | distinct_out_callee_count | distinct_in_caller_count | out_edges | out_by_label | in_edges | in_by_label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3S | share | FUN_00114690 | share | 0 | 1 | 2 | FUN_00115260(leaf_p)*2 | leaf_p*2 | FUN_00115bb0(drive_x)*2; FUN_00116000(drive_y)*3 | drive_x*2; drive_y*3 |
| family_graph_03 | O3S | share | FUN_00114a10 | share | 0 | 1 | 2 | FUN_001154d0(leaf_p)*2 | leaf_p*2 | FUN_00115960(drive_x)*2; FUN_00116330(drive_y)*3 | drive_x*2; drive_y*3 |
| family_graph_03 | O3S | share | FUN_00114d70 | share | 0 | 0 | 2 | - | - | FUN_00115e70(drive_x)*2; FUN_00116590(drive_y)*3 | drive_x*2; drive_y*3 |
| family_graph_03 | O3S | leaf_p | FUN_00115260 | leaf_p | 0 | 0 | 1 | - | - | FUN_00114690(share)*2 | share*2 |
| family_graph_03 | O3S | leaf_p | FUN_001154d0 | leaf_p | 0 | 0 | 1 | - | - | FUN_00114a10(share)*2 | share*2 |
| family_graph_03 | O3S | decoy_a | FUN_001156e0 | decoy_a | 0 | 0 | 1 | - | - | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | decoy_b | FUN_001157e0 | decoy_b | 0 | 0 | 1 | - | - | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | drive_x | FUN_00115960 | drive_x | 0 | 1 | 1 | FUN_00114a10(share)*2 | share*2 | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | drive_x | FUN_00115bb0 | drive_x | 0 | 1 | 1 | FUN_00114690(share)*2 | share*2 | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | drive_x | FUN_00115e70 | drive_x | 0 | 1 | 1 | FUN_00114d70(share)*2 | share*2 | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | drive_y | FUN_00116000 | drive_y | 0 | 1 | 1 | FUN_00114690(share)*3 | share*3 | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | drive_y | FUN_00116330 | drive_y | 0 | 1 | 1 | FUN_00114a10(share)*3 | share*3 | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3S | drive_y | FUN_00116590 | drive_y | 0 | 1 | 1 | FUN_00114d70(share)*3 | share*3 | FUN_00113fe0(anchor:root)*2 | anchor:root*2 |

### Round Partitions

| case | build | mode | round | num_classes | classes | split_this_round |
|---|---|---|---|---|---|---|
| family_graph_03 | O3S | full | 0 | 2 | {drive_x*3, drive_y*3, share*2} {decoy_a, decoy_b, leaf_p*2, share} | - |
| family_graph_03 | O3S | full | 1 | 8 | {share*2} {share} {leaf_p*2} {decoy_a, decoy_b} {drive_x*2} {drive_x} {drive_y*2} {drive_y} | drive_x;drive_y |

### Round Signatures

| case | build | mode | from_round | member | origin | previous_class | out_color_multiset | in_color_multiset | used_signature | next_class | partition_changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3S | full | 0 | FUN_00114690 | share | R0C1 | R0C2*2 | R0C1*5 | prev=R0C1; out=R0C2*2; in=R0C1*5 | R1C1 | True |
| family_graph_03 | O3S | full | 0 | FUN_00114a10 | share | R0C1 | R0C2*2 | R0C1*5 | prev=R0C1; out=R0C2*2; in=R0C1*5 | R1C1 | True |
| family_graph_03 | O3S | full | 0 | FUN_00114d70 | share | R0C2 | - | R0C1*5 | prev=R0C2; out=-; in=R0C1*5 | R1C2 | True |
| family_graph_03 | O3S | full | 0 | FUN_00115260 | leaf_p | R0C2 | - | R0C1*2 | prev=R0C2; out=-; in=R0C1*2 | R1C3 | True |
| family_graph_03 | O3S | full | 0 | FUN_001154d0 | leaf_p | R0C2 | - | R0C1*2 | prev=R0C2; out=-; in=R0C1*2 | R1C3 | True |
| family_graph_03 | O3S | full | 0 | FUN_001156e0 | decoy_a | R0C2 | - | anchor:root*2 | prev=R0C2; out=-; in=anchor:root*2 | R1C4 | True |
| family_graph_03 | O3S | full | 0 | FUN_001157e0 | decoy_b | R0C2 | - | anchor:root*2 | prev=R0C2; out=-; in=anchor:root*2 | R1C4 | True |
| family_graph_03 | O3S | full | 0 | FUN_00115960 | drive_x | R0C1 | R0C1*2 | anchor:root*2 | prev=R0C1; out=R0C1*2; in=anchor:root*2 | R1C5 | True |
| family_graph_03 | O3S | full | 0 | FUN_00115bb0 | drive_x | R0C1 | R0C1*2 | anchor:root*2 | prev=R0C1; out=R0C1*2; in=anchor:root*2 | R1C5 | True |
| family_graph_03 | O3S | full | 0 | FUN_00115e70 | drive_x | R0C1 | R0C2*2 | anchor:root*2 | prev=R0C1; out=R0C2*2; in=anchor:root*2 | R1C6 | True |
| family_graph_03 | O3S | full | 0 | FUN_00116000 | drive_y | R0C1 | R0C1*3 | anchor:root*2 | prev=R0C1; out=R0C1*3; in=anchor:root*2 | R1C7 | True |
| family_graph_03 | O3S | full | 0 | FUN_00116330 | drive_y | R0C1 | R0C1*3 | anchor:root*2 | prev=R0C1; out=R0C1*3; in=anchor:root*2 | R1C7 | True |
| family_graph_03 | O3S | full | 0 | FUN_00116590 | drive_y | R0C1 | R0C2*3 | anchor:root*2 | prev=R0C1; out=R0C2*3; in=anchor:root*2 | R1C8 | True |
| family_graph_03 | O3S | full | 1 | FUN_00114690 | share | R1C1 | R1C3*2 | R1C5*2; R1C7*3 | prev=R1C1; out=R1C3*2; in=R1C5*2; R1C7*3 | R2C1 | False |
| family_graph_03 | O3S | full | 1 | FUN_00114a10 | share | R1C1 | R1C3*2 | R1C5*2; R1C7*3 | prev=R1C1; out=R1C3*2; in=R1C5*2; R1C7*3 | R2C1 | False |
| family_graph_03 | O3S | full | 1 | FUN_00114d70 | share | R1C2 | - | R1C6*2; R1C8*3 | prev=R1C2; out=-; in=R1C6*2; R1C8*3 | R2C2 | False |
| family_graph_03 | O3S | full | 1 | FUN_00115260 | leaf_p | R1C3 | - | R1C1*2 | prev=R1C3; out=-; in=R1C1*2 | R2C3 | False |
| family_graph_03 | O3S | full | 1 | FUN_001154d0 | leaf_p | R1C3 | - | R1C1*2 | prev=R1C3; out=-; in=R1C1*2 | R2C3 | False |
| family_graph_03 | O3S | full | 1 | FUN_001156e0 | decoy_a | R1C4 | - | anchor:root*2 | prev=R1C4; out=-; in=anchor:root*2 | R2C4 | False |
| family_graph_03 | O3S | full | 1 | FUN_001157e0 | decoy_b | R1C4 | - | anchor:root*2 | prev=R1C4; out=-; in=anchor:root*2 | R2C4 | False |
| family_graph_03 | O3S | full | 1 | FUN_00115960 | drive_x | R1C5 | R1C1*2 | anchor:root*2 | prev=R1C5; out=R1C1*2; in=anchor:root*2 | R2C5 | False |
| family_graph_03 | O3S | full | 1 | FUN_00115bb0 | drive_x | R1C5 | R1C1*2 | anchor:root*2 | prev=R1C5; out=R1C1*2; in=anchor:root*2 | R2C5 | False |
| family_graph_03 | O3S | full | 1 | FUN_00115e70 | drive_x | R1C6 | R1C2*2 | anchor:root*2 | prev=R1C6; out=R1C2*2; in=anchor:root*2 | R2C6 | False |
| family_graph_03 | O3S | full | 1 | FUN_00116000 | drive_y | R1C7 | R1C1*3 | anchor:root*2 | prev=R1C7; out=R1C1*3; in=anchor:root*2 | R2C7 | False |
| family_graph_03 | O3S | full | 1 | FUN_00116330 | drive_y | R1C7 | R1C1*3 | anchor:root*2 | prev=R1C7; out=R1C1*3; in=anchor:root*2 | R2C7 | False |
| family_graph_03 | O3S | full | 1 | FUN_00116590 | drive_y | R1C8 | R1C2*3 | anchor:root*2 | prev=R1C8; out=R1C2*3; in=anchor:root*2 | R2C8 | False |

### Family Rows

| case | build | mode | origin | k_obs | d_star | num_predicted_clusters | family_pair_recall | collision_with | observed_relation_patterns |
|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3S | full | share | 3 | 0 | 2 | 1/3=0.33 | - | 2*[self=0; dout=1; din=2; out=leaf_p*2; in=drive_x*2; drive_y*3] \| 1*[self=0; dout=0; din=2; out=-; in=drive_x*2; drive_y*3] |
| family_graph_03 | O3S | full | leaf_p | 2 | - | 1 | 1/1=1.00 | - | 2*[self=0; dout=0; din=1; out=-; in=share*2] |
| family_graph_03 | O3S | full | decoy_a | 1 | - | 1 | n/a | decoy_b | 1*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |
| family_graph_03 | O3S | full | decoy_b | 1 | - | 1 | n/a | decoy_a | 1*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |
| family_graph_03 | O3S | full | drive_x | 3 | 1 | 2 | 1/3=0.33 | - | 3*[self=0; dout=1; din=1; out=share*2; in=anchor:root*2] |
| family_graph_03 | O3S | full | drive_y | 3 | 1 | 2 | 1/3=0.33 | - | 3*[self=0; dout=1; din=1; out=share*3; in=anchor:root*2] |

### Predicted Clusters

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_03 | O3S | full | C1 | FUN_00114690;FUN_00114a10 | share;share | share | 2*[self=0; dout=1; din=2; out=leaf_p*2; in=drive_x*2; drive_y*3] |
| family_graph_03 | O3S | full | C2 | FUN_00114d70 | share | share | 1*[self=0; dout=0; din=2; out=-; in=drive_x*2; drive_y*3] |
| family_graph_03 | O3S | full | C3 | FUN_00115260;FUN_001154d0 | leaf_p;leaf_p | leaf_p | 2*[self=0; dout=0; din=1; out=-; in=share*2] |
| family_graph_03 | O3S | full | C4 | FUN_001156e0;FUN_001157e0 | decoy_a;decoy_b | decoy_a;decoy_b | 2*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |
| family_graph_03 | O3S | full | C5 | FUN_00115960;FUN_00115bb0 | drive_x;drive_x | drive_x | 2*[self=0; dout=1; din=1; out=share*2; in=anchor:root*2] |
| family_graph_03 | O3S | full | C6 | FUN_00115e70 | drive_x | drive_x | 1*[self=0; dout=1; din=1; out=share*2; in=anchor:root*2] |
| family_graph_03 | O3S | full | C7 | FUN_00116000;FUN_00116330 | drive_y;drive_y | drive_y | 2*[self=0; dout=1; din=1; out=share*3; in=anchor:root*2] |
| family_graph_03 | O3S | full | C8 | FUN_00116590 | drive_y | drive_y | 1*[self=0; dout=1; din=1; out=share*3; in=anchor:root*2] |

### Collision Candidates

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_03 | O3S | full | C4 | FUN_001156e0;FUN_001157e0 | decoy_a;decoy_b | decoy_a;decoy_b | 2*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |

### Scores

| case | build | mode | engine_rounds | effective_rounds | TP | FP | FN | TN | precision | recall | F1 | ARI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3S | full | 2 | 1 | 4 | 1 | 6 | 67 | 0.80 | 0.40 | 0.53 | 0.49 |

## family_graph_03 / O3KS / mode=full

### Inputs

```text
fixture: fixtures/family_graph_03.O3KS.fixture.json
ground truth: ground_truth/family_graph_03.O3KS.gt.json
```

### Origins

| case | build | origin | k_obs | members | symbols |
|---|---|---|---|---|---|
| family_graph_03 | O3KS | share | 3 | FUN_00114720;FUN_001148e0;FUN_00114a30 | share;share;share |
| family_graph_03 | O3KS | leaf_p | 3 | FUN_00114b20;FUN_00114d90;FUN_00114ef0 | leaf_p;leaf_p;leaf_p |
| family_graph_03 | O3KS | leaf_q | 3 | FUN_00115100;FUN_00115250;FUN_00115440 | leaf_q;leaf_q;leaf_q |
| family_graph_03 | O3KS | decoy_a | 1 | FUN_00115680 | decoy_a |
| family_graph_03 | O3KS | decoy_b | 1 | FUN_00115780 | decoy_b |
| family_graph_03 | O3KS | drive_x | 3 | FUN_00115900;FUN_00115b50;FUN_00115e10 | drive_x;drive_x;drive_x |
| family_graph_03 | O3KS | drive_y | 3 | FUN_00115fa0;FUN_001162d0;FUN_00116530 | drive_y;drive_y;drive_y |

### Anchors

| case | build | anchor | role | out | in |
|---|---|---|---|---|---|
| family_graph_03 | O3KS | FUN_00114070 | anchor:root | FUN_00115680(decoy_a)*2; FUN_00115780(decoy_b)*2; FUN_00115900(drive_x)*2; FUN_00115b50(drive_x)*2; FUN_00115e10(drive_x)*2; FUN_00115fa0(drive_y)*2; FUN_001162d0(drive_y)*2; FUN_00116530(drive_y)*2 | - |

### Instance Relations

| case | build | origin | member | symbol | self_call_count | distinct_out_callee_count | distinct_in_caller_count | out_edges | out_by_label | in_edges | in_by_label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | share | FUN_00114720 | share | 0 | 2 | 2 | FUN_00114b20(leaf_p)*2; FUN_00115250(leaf_q)*1 | leaf_p*2; leaf_q*1 | FUN_00115b50(drive_x)*2; FUN_00115fa0(drive_y)*3 | drive_x*2; drive_y*3 |
| family_graph_03 | O3KS | share | FUN_001148e0 | share | 0 | 2 | 2 | FUN_00114ef0(leaf_p)*2; FUN_00115440(leaf_q)*1 | leaf_p*2; leaf_q*1 | FUN_00115900(drive_x)*2; FUN_001162d0(drive_y)*3 | drive_x*2; drive_y*3 |
| family_graph_03 | O3KS | share | FUN_00114a30 | share | 0 | 2 | 2 | FUN_00114d90(leaf_p)*2; FUN_00115100(leaf_q)*1 | leaf_p*2; leaf_q*1 | FUN_00115e10(drive_x)*2; FUN_00116530(drive_y)*3 | drive_x*2; drive_y*3 |
| family_graph_03 | O3KS | leaf_p | FUN_00114b20 | leaf_p | 0 | 0 | 1 | - | - | FUN_00114720(share)*2 | share*2 |
| family_graph_03 | O3KS | leaf_p | FUN_00114d90 | leaf_p | 0 | 0 | 1 | - | - | FUN_00114a30(share)*2 | share*2 |
| family_graph_03 | O3KS | leaf_p | FUN_00114ef0 | leaf_p | 0 | 0 | 1 | - | - | FUN_001148e0(share)*2 | share*2 |
| family_graph_03 | O3KS | leaf_q | FUN_00115100 | leaf_q | 0 | 0 | 1 | - | - | FUN_00114a30(share)*1 | share*1 |
| family_graph_03 | O3KS | leaf_q | FUN_00115250 | leaf_q | 0 | 0 | 1 | - | - | FUN_00114720(share)*1 | share*1 |
| family_graph_03 | O3KS | leaf_q | FUN_00115440 | leaf_q | 0 | 0 | 1 | - | - | FUN_001148e0(share)*1 | share*1 |
| family_graph_03 | O3KS | decoy_a | FUN_00115680 | decoy_a | 0 | 0 | 1 | - | - | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | decoy_b | FUN_00115780 | decoy_b | 0 | 0 | 1 | - | - | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | drive_x | FUN_00115900 | drive_x | 0 | 1 | 1 | FUN_001148e0(share)*2 | share*2 | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | drive_x | FUN_00115b50 | drive_x | 0 | 1 | 1 | FUN_00114720(share)*2 | share*2 | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | drive_x | FUN_00115e10 | drive_x | 0 | 1 | 1 | FUN_00114a30(share)*2 | share*2 | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | drive_y | FUN_00115fa0 | drive_y | 0 | 1 | 1 | FUN_00114720(share)*3 | share*3 | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | drive_y | FUN_001162d0 | drive_y | 0 | 1 | 1 | FUN_001148e0(share)*3 | share*3 | FUN_00114070(anchor:root)*2 | anchor:root*2 |
| family_graph_03 | O3KS | drive_y | FUN_00116530 | drive_y | 0 | 1 | 1 | FUN_00114a30(share)*3 | share*3 | FUN_00114070(anchor:root)*2 | anchor:root*2 |

### Round Partitions

| case | build | mode | round | num_classes | classes | split_this_round |
|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | full | 0 | 3 | {share*3} {decoy_a, decoy_b, leaf_p*3, leaf_q*3} {drive_x*3, drive_y*3} | - |
| family_graph_03 | O3KS | full | 1 | 6 | {share*3} {leaf_p*3} {leaf_q*3} {decoy_a, decoy_b} {drive_x*3} {drive_y*3} | - |

### Round Signatures

| case | build | mode | from_round | member | origin | previous_class | out_color_multiset | in_color_multiset | used_signature | next_class | partition_changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | full | 0 | FUN_00114720 | share | R0C1 | R0C2*3 | R0C3*5 | prev=R0C1; out=R0C2*3; in=R0C3*5 | R1C1 | True |
| family_graph_03 | O3KS | full | 0 | FUN_001148e0 | share | R0C1 | R0C2*3 | R0C3*5 | prev=R0C1; out=R0C2*3; in=R0C3*5 | R1C1 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00114a30 | share | R0C1 | R0C2*3 | R0C3*5 | prev=R0C1; out=R0C2*3; in=R0C3*5 | R1C1 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00114b20 | leaf_p | R0C2 | - | R0C1*2 | prev=R0C2; out=-; in=R0C1*2 | R1C2 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00114d90 | leaf_p | R0C2 | - | R0C1*2 | prev=R0C2; out=-; in=R0C1*2 | R1C2 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00114ef0 | leaf_p | R0C2 | - | R0C1*2 | prev=R0C2; out=-; in=R0C1*2 | R1C2 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115100 | leaf_q | R0C2 | - | R0C1*1 | prev=R0C2; out=-; in=R0C1*1 | R1C3 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115250 | leaf_q | R0C2 | - | R0C1*1 | prev=R0C2; out=-; in=R0C1*1 | R1C3 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115440 | leaf_q | R0C2 | - | R0C1*1 | prev=R0C2; out=-; in=R0C1*1 | R1C3 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115680 | decoy_a | R0C2 | - | anchor:root*2 | prev=R0C2; out=-; in=anchor:root*2 | R1C4 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115780 | decoy_b | R0C2 | - | anchor:root*2 | prev=R0C2; out=-; in=anchor:root*2 | R1C4 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115900 | drive_x | R0C3 | R0C1*2 | anchor:root*2 | prev=R0C3; out=R0C1*2; in=anchor:root*2 | R1C5 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115b50 | drive_x | R0C3 | R0C1*2 | anchor:root*2 | prev=R0C3; out=R0C1*2; in=anchor:root*2 | R1C5 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115e10 | drive_x | R0C3 | R0C1*2 | anchor:root*2 | prev=R0C3; out=R0C1*2; in=anchor:root*2 | R1C5 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00115fa0 | drive_y | R0C3 | R0C1*3 | anchor:root*2 | prev=R0C3; out=R0C1*3; in=anchor:root*2 | R1C6 | True |
| family_graph_03 | O3KS | full | 0 | FUN_001162d0 | drive_y | R0C3 | R0C1*3 | anchor:root*2 | prev=R0C3; out=R0C1*3; in=anchor:root*2 | R1C6 | True |
| family_graph_03 | O3KS | full | 0 | FUN_00116530 | drive_y | R0C3 | R0C1*3 | anchor:root*2 | prev=R0C3; out=R0C1*3; in=anchor:root*2 | R1C6 | True |
| family_graph_03 | O3KS | full | 1 | FUN_00114720 | share | R1C1 | R1C2*2; R1C3*1 | R1C5*2; R1C6*3 | prev=R1C1; out=R1C2*2; R1C3*1; in=R1C5*2; R1C6*3 | R2C1 | False |
| family_graph_03 | O3KS | full | 1 | FUN_001148e0 | share | R1C1 | R1C2*2; R1C3*1 | R1C5*2; R1C6*3 | prev=R1C1; out=R1C2*2; R1C3*1; in=R1C5*2; R1C6*3 | R2C1 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00114a30 | share | R1C1 | R1C2*2; R1C3*1 | R1C5*2; R1C6*3 | prev=R1C1; out=R1C2*2; R1C3*1; in=R1C5*2; R1C6*3 | R2C1 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00114b20 | leaf_p | R1C2 | - | R1C1*2 | prev=R1C2; out=-; in=R1C1*2 | R2C2 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00114d90 | leaf_p | R1C2 | - | R1C1*2 | prev=R1C2; out=-; in=R1C1*2 | R2C2 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00114ef0 | leaf_p | R1C2 | - | R1C1*2 | prev=R1C2; out=-; in=R1C1*2 | R2C2 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115100 | leaf_q | R1C3 | - | R1C1*1 | prev=R1C3; out=-; in=R1C1*1 | R2C3 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115250 | leaf_q | R1C3 | - | R1C1*1 | prev=R1C3; out=-; in=R1C1*1 | R2C3 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115440 | leaf_q | R1C3 | - | R1C1*1 | prev=R1C3; out=-; in=R1C1*1 | R2C3 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115680 | decoy_a | R1C4 | - | anchor:root*2 | prev=R1C4; out=-; in=anchor:root*2 | R2C4 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115780 | decoy_b | R1C4 | - | anchor:root*2 | prev=R1C4; out=-; in=anchor:root*2 | R2C4 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115900 | drive_x | R1C5 | R1C1*2 | anchor:root*2 | prev=R1C5; out=R1C1*2; in=anchor:root*2 | R2C5 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115b50 | drive_x | R1C5 | R1C1*2 | anchor:root*2 | prev=R1C5; out=R1C1*2; in=anchor:root*2 | R2C5 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115e10 | drive_x | R1C5 | R1C1*2 | anchor:root*2 | prev=R1C5; out=R1C1*2; in=anchor:root*2 | R2C5 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00115fa0 | drive_y | R1C6 | R1C1*3 | anchor:root*2 | prev=R1C6; out=R1C1*3; in=anchor:root*2 | R2C6 | False |
| family_graph_03 | O3KS | full | 1 | FUN_001162d0 | drive_y | R1C6 | R1C1*3 | anchor:root*2 | prev=R1C6; out=R1C1*3; in=anchor:root*2 | R2C6 | False |
| family_graph_03 | O3KS | full | 1 | FUN_00116530 | drive_y | R1C6 | R1C1*3 | anchor:root*2 | prev=R1C6; out=R1C1*3; in=anchor:root*2 | R2C6 | False |

### Family Rows

| case | build | mode | origin | k_obs | d_star | num_predicted_clusters | family_pair_recall | collision_with | observed_relation_patterns |
|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | full | share | 3 | - | 1 | 3/3=1.00 | - | 3*[self=0; dout=2; din=2; out=leaf_p*2; leaf_q*1; in=drive_x*2; drive_y*3] |
| family_graph_03 | O3KS | full | leaf_p | 3 | - | 1 | 3/3=1.00 | - | 3*[self=0; dout=0; din=1; out=-; in=share*2] |
| family_graph_03 | O3KS | full | leaf_q | 3 | - | 1 | 3/3=1.00 | - | 3*[self=0; dout=0; din=1; out=-; in=share*1] |
| family_graph_03 | O3KS | full | decoy_a | 1 | - | 1 | n/a | decoy_b | 1*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |
| family_graph_03 | O3KS | full | decoy_b | 1 | - | 1 | n/a | decoy_a | 1*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |
| family_graph_03 | O3KS | full | drive_x | 3 | - | 1 | 3/3=1.00 | - | 3*[self=0; dout=1; din=1; out=share*2; in=anchor:root*2] |
| family_graph_03 | O3KS | full | drive_y | 3 | - | 1 | 3/3=1.00 | - | 3*[self=0; dout=1; din=1; out=share*3; in=anchor:root*2] |

### Predicted Clusters

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | full | C1 | FUN_00114720;FUN_001148e0;FUN_00114a30 | share;share;share | share | 3*[self=0; dout=2; din=2; out=leaf_p*2; leaf_q*1; in=drive_x*2; drive_y*3] |
| family_graph_03 | O3KS | full | C2 | FUN_00114b20;FUN_00114d90;FUN_00114ef0 | leaf_p;leaf_p;leaf_p | leaf_p | 3*[self=0; dout=0; din=1; out=-; in=share*2] |
| family_graph_03 | O3KS | full | C3 | FUN_00115100;FUN_00115250;FUN_00115440 | leaf_q;leaf_q;leaf_q | leaf_q | 3*[self=0; dout=0; din=1; out=-; in=share*1] |
| family_graph_03 | O3KS | full | C4 | FUN_00115680;FUN_00115780 | decoy_a;decoy_b | decoy_a;decoy_b | 2*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |
| family_graph_03 | O3KS | full | C5 | FUN_00115900;FUN_00115b50;FUN_00115e10 | drive_x;drive_x;drive_x | drive_x | 3*[self=0; dout=1; din=1; out=share*2; in=anchor:root*2] |
| family_graph_03 | O3KS | full | C6 | FUN_00115fa0;FUN_001162d0;FUN_00116530 | drive_y;drive_y;drive_y | drive_y | 3*[self=0; dout=1; din=1; out=share*3; in=anchor:root*2] |

### Collision Candidates

| case | build | mode | cluster | members | symbols | origins | relation_patterns |
|---|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | full | C4 | FUN_00115680;FUN_00115780 | decoy_a;decoy_b | decoy_a;decoy_b | 2*[self=0; dout=0; din=1; out=-; in=anchor:root*2] |

### Scores

| case | build | mode | engine_rounds | effective_rounds | TP | FP | FN | TN | precision | recall | F1 | ARI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| family_graph_03 | O3KS | full | 2 | 1 | 15 | 1 | 0 | 120 | 0.94 | 1.00 | 0.97 | 0.96 |
