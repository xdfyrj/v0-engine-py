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

impl Scalar for f64 {
    fn tweak(x: Self, salt: u64) -> Self {
        x * 1.125 + ((salt % 31) as f64) * 0.25
    }
    fn mix(a: Self, b: Self) -> Self {
        a * 1.5 + b * 0.75
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

// ============ 공유 leaf P (2중 루프) — share 와 drive 양쪽에서 호출됨 => 호출자 다수 => 생존 ============
#[cfg_attr(keep, inline(never))]
fn leaf_p<T: Scalar>(data: &[T], seed: T) -> T {
    let data = black_box(data);
    let mut a = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        a = T::mix(a, T::tweak(black_box(data[i]), (i as u64).wrapping_mul(2).wrapping_add(1)));
        i += 1;
    }
    let mut b = black_box(a);
    let mut j = 0usize;
    while j < data.len() {
        b = T::tweak(b, (j as u64).wrapping_add(7));
        j += 1;
    }
    black_box(b)
}

// ============ 공유 leaf Q (2중 루프, 연산 순서 다름) ============
#[cfg_attr(keep, inline(never))]
fn leaf_q<T: Scalar>(data: &[T], seed: T) -> T {
    let data = black_box(data);
    let mut a = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        a = T::tweak(T::mix(a, black_box(data[i])), (i as u64).wrapping_mul(4).wrapping_add(3));
        i += 1;
    }
    let mut b = black_box(a);
    let mut j = 0usize;
    while j < data.len() {
        b = T::mix(b, T::tweak(b, (j as u64).wrapping_mul(6)));
        j += 1;
    }
    black_box(b)
}

// ============ 중간 계층 share (leaf_p x2 + leaf_q x1 호출) — drive 두 개가 공유 호출 ============
#[cfg_attr(keep, inline(never))]
fn share<T: Scalar>(data: &[T], seed: T) -> T {
    let data = black_box(data);
    // 생존용 루프
    let mut warm = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        warm = T::mix(warm, T::tweak(black_box(data[i]), (i as u64).wrapping_mul(5)));
        i += 1;
    }
    // 공유 leaf 호출: leaf_p x2, leaf_q x1
    let p1 = leaf_p(data, warm);
    let q1 = leaf_q(data, T::mix(p1, seed));
    let p2 = leaf_p(data, T::tweak(q1, 13));
    black_box(p2)
}

// ============ Driver X (2중 루프 + share x2) ============
#[cfg_attr(keep, inline(never))]
fn drive_x<T: Scalar>(data: &[T], seed: T) -> T {
    let data = black_box(data);
    let mut a = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        a = T::tweak(a, (i as u64).wrapping_add(3));
        i += 1;
    }
    let mut b = black_box(a);
    let mut j = 0usize;
    while j < data.len() {
        b = T::mix(b, T::tweak(black_box(data[j]), j as u64));
        j += 1;
    }
    let r1 = share(data, b);
    let r2 = share(data, T::mix(r1, seed));
    black_box(r2)
}

// ============ Driver Y (2중 루프 + share x3) ============
#[cfg_attr(keep, inline(never))]
fn drive_y<T: Scalar>(data: &[T], seed: T) -> T {
    let data = black_box(data);
    let mut a = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        a = T::mix(a, T::tweak(black_box(data[i]), (i as u64).wrapping_mul(7)));
        i += 1;
    }
    let mut b = black_box(a);
    let mut j = 0usize;
    while j < data.len() {
        b = T::tweak(b, (j as u64).wrapping_add(9));
        j += 1;
    }
    let r1 = share(data, b);
    let r2 = share(data, T::mix(r1, seed));
    let r3 = share(data, T::tweak(r2, 11));
    black_box(r3)
}

// ============ Noise A — 큰 concrete leaf looper(3중 루프), main 이 호출 ============
#[cfg_attr(keep, inline(never))]
fn decoy_a(data: &[i32], seed: i32) -> i32 {
    let data = black_box(data);
    let mut a = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        a = a.wrapping_mul(3).wrapping_add(black_box(data[i]) ^ (i as i32));
        i += 1;
    }
    let mut b = black_box(a);
    let mut j = 0usize;
    while j < data.len() {
        b = b.wrapping_add(black_box(data[j]).wrapping_mul(5)).rotate_left(3);
        j += 1;
    }
    let mut c = black_box(b);
    let mut k = 0usize;
    while k < data.len() {
        c ^= black_box(data[k]).wrapping_mul(c | 1);
        k += 1;
    }
    black_box(c)
}

// ============ Noise B — 큰 concrete f64 leaf looper ============
#[cfg_attr(keep, inline(never))]
fn decoy_b(data: &[f64], seed: f64) -> f64 {
    let data = black_box(data);
    let mut a = black_box(seed);
    let mut i = 0usize;
    while i < data.len() {
        a = a * 1.25 + black_box(data[i]) * 0.5 - (i as f64);
        i += 1;
    }
    let mut b = black_box(a);
    let mut j = 0usize;
    while j < data.len() {
        b = b * 0.875 + black_box(data[j]) * 1.5;
        j += 1;
    }
    let mut c = black_box(b);
    let mut k = 0usize;
    while k < data.len() {
        c = (c + black_box(data[k])) * 0.5;
        k += 1;
    }
    black_box(c)
}


fn main() {
    let i32_a: [i32; 8] = black_box([10, -20, 30, -40, 50, -60, 70, -80]);
    let i32_b: [i32; 8] = black_box([3, 6, 9, 12, 15, 18, 21, 24]);

    let f64_a: [f64; 8] = black_box([1.5, -2.5, 3.5, -4.5, 5.5, -6.5, 7.5, -8.5]);
    let f64_b: [f64; 8] = black_box([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]);

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

    // drive_x (타입당 2회)
    let y_i2 = drive_y(&i32_b, black_box(-13_i32));
    let y_f2 = drive_y(&f64_b, black_box(-13.0_f64));
    let x_w2 = drive_x(&wide_b, black_box(Wide { a: 10, b: 11, c: 12 }));
    let y_i1 = drive_y(&i32_a, black_box(11_i32));
    let d_b1 = decoy_b(&f64_a, black_box(5.0_f64));
    let y_w1 = drive_y(&wide_a, black_box(Wide { a: 11, b: 12, c: 13 }));
    let d_a1 = decoy_a(&i32_a, black_box(5_i32));
    let y_f1 = drive_y(&f64_a, black_box(11.0_f64));
    let x_i2 = drive_x(&i32_b, black_box(-9_i32));
    let x_f1 = drive_x(&f64_a, black_box(7.0_f64));
    let d_a2 = decoy_a(&i32_b, black_box(-7_i32));
    let d_b2 = decoy_b(&f64_b, black_box(-7.0_f64));
    let x_w1 = drive_x(&wide_a, black_box(Wide { a: 7, b: 8, c: 9 }));
    let y_w2 = drive_y(&wide_b, black_box(Wide { a: 14, b: 15, c: 16 }));
    let x_i1 = drive_x(&i32_a, black_box(7_i32));
    let x_f2 = drive_x(&f64_b, black_box(-9.0_f64));


    black_box((
        x_i1, x_i2, x_f1, x_f2, x_w1, x_w2,
        y_i1, y_i2, y_f1, y_f2, y_w1, y_w2,
        d_a1, d_a2, d_b1, d_b2,
    ));
}
