// family_graph_01.rs
use std::hint::black_box;

trait Scalar: Copy + PartialOrd {
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

impl Scalar for u64 {
    fn tweak(x: Self, salt: u64) -> Self {
        x.wrapping_mul(3).wrapping_add(salt.wrapping_mul(17))
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

#[cfg_attr(keep, inline(never))]
fn shared_recursive<T: Scalar>(value: T, salt: u64, depth: u64) -> T {
    let salt = black_box(salt);
    let depth = black_box(depth);
    let mixed = black_box(T::tweak(value, salt));

    if depth == 0 {
        mixed
    } else {
        let next_salt = salt
            .rotate_left(7)
            .wrapping_add(depth.wrapping_mul(0x9e37_79b9));
        let next_value = T::mix(mixed, value);
        let child = shared_recursive(next_value, next_salt, depth - 1);
        black_box(T::mix(mixed, child))
    }
}

#[cfg_attr(keep, inline(never))]
fn combine<T: Scalar>(left: T, right: T, salt: u64) -> T {
    let guard = shared_recursive(left, salt ^ 0x517c_c1b7, 2);
    let a = black_box(T::tweak(T::mix(left, guard), salt));
    let b = black_box(T::tweak(right, salt ^ 0x9e37_79b9));

    let base = T::mix(a, b);

    if a > b {
        T::mix(base, a)
    } else {
        T::mix(base, b)
    }
}

#[cfg_attr(keep, inline(never))]
fn score<T: Scalar>(items: &[T], seed: T) -> T {
    let mut acc = shared_recursive(seed, items.len() as u64 ^ 0x243f_6a88, 1);
    let mut i = 0usize;

    while i < items.len() {
        let item = black_box(items[i]);
        acc = combine(acc, item, (i as u64).wrapping_mul(17).wrapping_add(3));
        i += 1;
    }

    acc
}

#[cfg_attr(keep, inline(never))]
fn process<T: Scalar>(items: &[T], seed: T) -> T {
    let seed = shared_recursive(seed, items.len() as u64 ^ 0x85a3_08d3, 1);
    let s1 = score(items, seed);
    let mid = black_box(items[items.len() / 2]);
    let s2 = combine(s1, mid, 0x55aa);
    combine(s2, seed, items.len() as u64)
}

#[cfg_attr(keep, inline(never))]
fn summarize<T: Scalar>(a: &[T], b: &[T], seed: T) -> T {
    let seed = shared_recursive(seed, (a.len() as u64) << 32 | b.len() as u64, 1);
    let p1 = process(a, seed);
    let p2 = process(b, T::tweak(seed, 11));
    combine(p1, p2, 0xaa55)
}

fn main() {
    let i32_a: [i32; 8] = black_box([10, -20, 30, -40, 50, -60, 70, -80]);
    let i32_b: [i32; 8] = black_box([3, 6, 9, 12, 15, 18, 21, 24]);

    let u64_a: [u64; 8] = black_box([10, 20, 30, 40, 50, 60, 70, 80]);
    let u64_b: [u64; 8] = black_box([3, 6, 9, 12, 15, 18, 21, 24]);

    let f64_a: [f64; 8] = black_box([1.5, -2.5, 3.5, -4.5, 5.5, -6.5, 7.5, -8.5]);
    let f64_b: [f64; 8] = black_box([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]);

    let r_i32 = summarize(&i32_a, &i32_b, black_box(7));
    let r_u64 = summarize(&u64_a, &u64_b, black_box(7));
    let r_f64 = summarize(&f64_a, &f64_b, black_box(7.0));

    black_box((r_i32, r_u64, r_f64));
}
