// family_graph_02.rs  (v2 — looper survival fix)
//
// 이전 버전 문제: looper 를 타입당 1회만 호출 + 본체가 얇아 인라인되어 사라졌다.
// 수정: looper 를 (1) 루프+여러 재귀 호출로 키우고 (2) main 에서 타입당 2회 호출한다.
//       (fg01 의 process 가 살아남은 조건과 동일.)  타입은 2개로 줄여 크기를 통제한다.
//
// 시험 장치
//  (1) precision: recurse_alpha(자기 호출 1회) vs recurse_beta(자기 호출 2회)
//      => 자기 호출 횟수라는 호출 관계 특징으로 갈려야 한다.
//      또한 process_alpha(alpha 그룹 호출) vs process_beta(beta 그룹 호출)도 갈려야 한다.
//  (2) relation-only 대조: c_recurse_alpha_* / c_process_alpha_* 는 generic alpha
//      서브그래프를 그대로 옮긴 별개 origin. Axis-1 구조가 동일하므로 CG-WL은
//      generic alpha와 분리하지 못해야 한다.
//  (3) arg-shape: Wide(24바이트)는 값 전달이 메모리/sret 로 내려가 같은 family 안에서도
//      인자/반환 ABI 가 i32 와 갈린다. "인자는 부드러운 조건" 조항을 시험한다.
//
// 의도한 정답 origin (자연 O3 생존분에 한함):
//   G_ra = { recurse_alpha::<i32>, recurse_alpha::<Wide> }
//   G_rb = { recurse_beta::<i32>, recurse_beta::<Wide> }
//   G_pa = { process_alpha::<i32>, process_alpha::<Wide> }
//   G_pb = { process_beta::<i32>, process_beta::<Wide> }
//   c_recurse_alpha_i32, c_recurse_alpha_wide,
//   c_process_alpha_i32, c_process_alpha_wide는 각각 별도 singleton origin이다.
//
// CG-WL 예상 결과:
//   - G_rb와 G_pb는 각각 두 instance가 묶인다.
//   - G_ra와 대응하는 concrete singleton 두 개가 한 cluster로 합쳐진다.
//   - G_pa와 대응하는 concrete singleton 두 개가 한 cluster로 합쳐진다.
//
// 생존 게이트(먼저 확인): O3/O3S 빌드 후 process_alpha/process_beta/c_process_alpha 가
//   독립 함수로 남았는지 확인. 여전히 인라인되면 main 호출을 타입당 3회로 늘리거나
//   루프 밖 재귀 호출을 한두 개 더 추가한다. 재귀 함수는 거의 확실히 생존한다.
//   generic 과 concrete alpha 가 ICF 로 접히면 concrete 상수 하나만 바꾼다.

#![allow(unexpected_cfgs)]

use std::hint::black_box;

#[repr(C)]
#[derive(Copy, Clone)]
struct Wide {
    a: u64,
    b: u64,
    c: u64,
}

trait Scalar: Copy {
    fn tweak(x: Self, salt: u64) -> Self;
    fn mix(a: Self, b: Self) -> Self;
}

impl Scalar for i32 {
    fn tweak(x: Self, salt: u64) -> Self {
        x.wrapping_mul(3).wrapping_add((salt as i32).wrapping_mul(17))
    }
    fn mix(a: Self, b: Self) -> Self {
        a.wrapping_mul(5).wrapping_add(b.wrapping_mul(7))
    }
}

impl Scalar for Wide {
    fn tweak(x: Self, salt: u64) -> Self {
        let k = salt.wrapping_mul(17);
        Wide {
            a: x.a.wrapping_mul(3).wrapping_add(k),
            b: x.b.rotate_left((salt & 31) as u32).wrapping_add(k ^ x.a),
            c: x.c.wrapping_add(x.a ^ x.b).wrapping_add(k.rotate_left(7)),
        }
    }
    fn mix(a: Self, b: Self) -> Self {
        Wide {
            a: a.a.wrapping_mul(5).wrapping_add(b.a.wrapping_mul(7)),
            b: a.b.wrapping_add(b.b.rotate_left(11)),
            c: a.c ^ b.c ^ a.a.wrapping_add(b.b),
        }
    }
}

// ============ Generic recursive family: alpha (self-call x1) ============
#[cfg_attr(keep, inline(never))]
fn recurse_alpha<T: Scalar>(value: T, salt: u64, depth: u64) -> T {
    let salt = black_box(salt);
    let depth = black_box(depth);
    let mixed = black_box(T::tweak(value, salt ^ 0xa1a1_a1a1));
    if depth == 0 {
        mixed
    } else {
        let next_salt = salt.rotate_left(7).wrapping_add(depth.wrapping_mul(0x9e37_79b9));
        let next_value = T::mix(mixed, value);
        let child = recurse_alpha(next_value, next_salt, depth - 1); // self x1
        black_box(T::mix(mixed, child))
    }
}

// ============ Generic recursive family: beta (self-call x2) ============
#[cfg_attr(keep, inline(never))]
fn recurse_beta<T: Scalar>(value: T, salt: u64, depth: u64) -> T {
    let salt = black_box(salt);
    let depth = black_box(depth);
    let mixed = black_box(T::tweak(value, salt ^ 0xb2b2_b2b2));
    if depth == 0 {
        mixed
    } else {
        let s_l = salt.rotate_left(11).wrapping_add(depth.wrapping_mul(0x7f4a_7c15));
        let s_r = salt.rotate_left(5).wrapping_add(depth.wrapping_mul(0x6a09_e667));
        let left = recurse_beta(T::mix(mixed, value), s_l, depth - 1);  // self #1
        let right = recurse_beta(T::mix(value, mixed), s_r, depth - 1); // self #2
        black_box(T::mix(left, right))
    }
}

// ============ Generic looper: process_alpha (loop + 5 calls -> recurse_alpha) ============
// fg01 의 process 와 같은 "복잡하게 많이 부르는" 함수. 자연 O3 생존을 노린다.
#[cfg_attr(keep, inline(never))]
fn process_alpha<T: Scalar>(items: &[T], seed: T) -> T {
    let items = black_box(items); // 길이 불투명 -> 루프 보존
    let mut acc = recurse_alpha(seed, 0xa0a0, 1);
    let mut i = 0usize;
    while i < items.len() {
        let x = black_box(items[i]);
        acc = recurse_alpha(T::mix(acc, x), (i as u64).wrapping_mul(17).wrapping_add(3), 1);
        i += 1;
    }
    let mid = black_box(items[items.len() / 2]);
    let s2 = recurse_alpha(T::mix(acc, mid), 0xa2a2, 2);
    let s3 = recurse_alpha(T::mix(s2, seed), 0xa3a3, 1);
    black_box(recurse_alpha(T::mix(s2, s3), 0xa4a4, 1))
}

// ============ Generic looper: process_beta (loop + 5 calls -> recurse_beta) ============
#[cfg_attr(keep, inline(never))]
fn process_beta<T: Scalar>(items: &[T], seed: T) -> T {
    let items = black_box(items);
    let mut acc = recurse_beta(seed, 0xb0b0, 1);
    let mut i = 0usize;
    while i < items.len() {
        let x = black_box(items[i]);
        acc = recurse_beta(T::mix(acc, x), (i as u64).wrapping_mul(19).wrapping_add(5), 1);
        i += 1;
    }
    let mid = black_box(items[items.len() / 2]);
    let s2 = recurse_beta(T::mix(acc, mid), 0xb2b2, 2);
    let s3 = recurse_beta(T::mix(s2, seed), 0xb3b3, 1);
    black_box(recurse_beta(T::mix(s2, s3), 0xb4b4, 1))
}

// ============================================================
// Axis-1-isomorphic counterpart of the alpha subgraph
// (process_alpha + recurse_alpha). It is a separate origin with the same
// relation structure, so relation-only grouping cannot distinguish it.
// ============================================================

// ---- i32 ----
fn tweak_i32(x: i32, salt: u64) -> i32 {
    x.wrapping_mul(3).wrapping_add((salt as i32).wrapping_mul(17))
}
fn mix_i32(a: i32, b: i32) -> i32 {
    a.wrapping_mul(5).wrapping_add(b.wrapping_mul(7))
}
#[cfg_attr(keep, inline(never))]
fn c_recurse_alpha_i32(value: i32, salt: u64, depth: u64) -> i32 {
    let salt = black_box(salt);
    let depth = black_box(depth);
    let mixed = black_box(tweak_i32(value, salt ^ 0xa1a1_a1a1));
    if depth == 0 {
        mixed
    } else {
        let next_salt = salt.rotate_left(7).wrapping_add(depth.wrapping_mul(0x9e37_79b9));
        let next_value = mix_i32(mixed, value);
        let child = c_recurse_alpha_i32(next_value, next_salt, depth - 1);
        black_box(mix_i32(mixed, child))
    }
}
#[cfg_attr(keep, inline(never))]
fn c_process_alpha_i32(items: &[i32], seed: i32) -> i32 {
    let items = black_box(items);
    let mut acc = c_recurse_alpha_i32(seed, 0xa0a0, 1);
    let mut i = 0usize;
    while i < items.len() {
        let x = black_box(items[i]);
        acc = c_recurse_alpha_i32(mix_i32(acc, x), (i as u64).wrapping_mul(17).wrapping_add(3), 1);
        i += 1;
    }
    let mid = black_box(items[items.len() / 2]);
    let s2 = c_recurse_alpha_i32(mix_i32(acc, mid), 0xa2a2, 2);
    let s3 = c_recurse_alpha_i32(mix_i32(s2, seed), 0xa3a3, 1);
    black_box(c_recurse_alpha_i32(mix_i32(s2, s3), 0xa4a4, 1))
}

// ---- Wide ----
fn tweak_wide(x: Wide, salt: u64) -> Wide {
    let k = salt.wrapping_mul(17);
    Wide {
        a: x.a.wrapping_mul(3).wrapping_add(k),
        b: x.b.rotate_left((salt & 31) as u32).wrapping_add(k ^ x.a),
        c: x.c.wrapping_add(x.a ^ x.b).wrapping_add(k.rotate_left(7)),
    }
}
fn mix_wide(a: Wide, b: Wide) -> Wide {
    Wide {
        a: a.a.wrapping_mul(5).wrapping_add(b.a.wrapping_mul(7)),
        b: a.b.wrapping_add(b.b.rotate_left(11)),
        c: a.c ^ b.c ^ a.a.wrapping_add(b.b),
    }
}
#[cfg_attr(keep, inline(never))]
fn c_recurse_alpha_wide(value: Wide, salt: u64, depth: u64) -> Wide {
    let salt = black_box(salt);
    let depth = black_box(depth);
    let mixed = black_box(tweak_wide(value, salt ^ 0xa1a1_a1a1));
    if depth == 0 {
        mixed
    } else {
        let next_salt = salt.rotate_left(7).wrapping_add(depth.wrapping_mul(0x9e37_79b9));
        let next_value = mix_wide(mixed, value);
        let child = c_recurse_alpha_wide(next_value, next_salt, depth - 1);
        black_box(mix_wide(mixed, child))
    }
}
#[cfg_attr(keep, inline(never))]
fn c_process_alpha_wide(items: &[Wide], seed: Wide) -> Wide {
    let items = black_box(items);
    let mut acc = c_recurse_alpha_wide(seed, 0xa0a0, 1);
    let mut i = 0usize;
    while i < items.len() {
        let x = black_box(items[i]);
        acc = c_recurse_alpha_wide(mix_wide(acc, x), (i as u64).wrapping_mul(17).wrapping_add(3), 1);
        i += 1;
    }
    let mid = black_box(items[items.len() / 2]);
    let s2 = c_recurse_alpha_wide(mix_wide(acc, mid), 0xa2a2, 2);
    let s3 = c_recurse_alpha_wide(mix_wide(s2, seed), 0xa3a3, 1);
    black_box(c_recurse_alpha_wide(mix_wide(s2, s3), 0xa4a4, 1))
}


fn main() {
    let i32_a: [i32; 8] = black_box([10, -20, 30, -40, 50, -60, 70, -80]);
    let i32_b: [i32; 8] = black_box([3, 6, 9, 12, 15, 18, 21, 24]);

    let wide_a: [Wide; 8] = black_box([
        Wide { a: 1, b: 2, c: 3 }, Wide { a: 4, b: 5, c: 6 },
        Wide { a: 7, b: 8, c: 9 }, Wide { a: 10, b: 11, c: 12 },
        Wide { a: 13, b: 14, c: 15 }, Wide { a: 16, b: 17, c: 18 },
        Wide { a: 19, b: 20, c: 21 }, Wide { a: 22, b: 23, c: 24 },
    ]);
    let wide_b: [Wide; 8] = black_box([
        Wide { a: 31, b: 32, c: 33 }, Wide { a: 34, b: 35, c: 36 },
        Wide { a: 37, b: 38, c: 39 }, Wide { a: 40, b: 41, c: 42 },
        Wide { a: 43, b: 44, c: 45 }, Wide { a: 46, b: 47, c: 48 },
        Wide { a: 49, b: 50, c: 51 }, Wide { a: 52, b: 53, c: 54 },
    ]);

    // generic alpha (2 call sites per type)
    let pa_i32_1 = process_alpha(&i32_a, black_box(7_i32));
    let pa_i32_2 = process_alpha(&i32_b, black_box(-9_i32));
    let pa_w_1 = process_alpha(&wide_a, black_box(Wide { a: 7, b: 8, c: 9 }));
    let pa_w_2 = process_alpha(&wide_b, black_box(Wide { a: 10, b: 11, c: 12 }));

    // generic beta (2 call sites per type)
    let pb_i32_1 = process_beta(&i32_a, black_box(11_i32));
    let pb_i32_2 = process_beta(&i32_b, black_box(-13_i32));
    let pb_w_1 = process_beta(&wide_a, black_box(Wide { a: 11, b: 12, c: 13 }));
    let pb_w_2 = process_beta(&wide_b, black_box(Wide { a: 14, b: 15, c: 16 }));

    // concrete alpha mirror (2 call sites per type)
    let ca_i32_1 = c_process_alpha_i32(&i32_a, black_box(7_i32));
    let ca_i32_2 = c_process_alpha_i32(&i32_b, black_box(-9_i32));
    let ca_w_1 = c_process_alpha_wide(&wide_a, black_box(Wide { a: 7, b: 8, c: 9 }));
    let ca_w_2 = c_process_alpha_wide(&wide_b, black_box(Wide { a: 10, b: 11, c: 12 }));

    black_box((
        pa_i32_1, pa_i32_2, pa_w_1, pa_w_2,
        pb_i32_1, pb_i32_2, pb_w_1, pb_w_2,
        ca_i32_1, ca_i32_2, ca_w_1, ca_w_2,
    ));
}
