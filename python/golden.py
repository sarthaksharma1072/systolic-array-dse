# Generated from: golden.ipynb
# Converted at: 2026-10-27T06:23:50.219Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import numpy as np


def os_expected(A, B):
    """Output-stationary: after the array drains, PE[i][j] holds C[i][j]."""
    return A @ B


def ws_expected(A, B):
    """Weight-stationary: row i of C leaves the bottom edge."""
    return A @ B


def os_schedule(A, B, N, K):
    """Returns, for each cycle t, the N activations and N vertical values to drive.
    Row i is delayed by i cycles; column j is delayed by j cycles."""
    sched = []
    for t in range(K + 2 * N + 2):
        a = [int(A[i][t - i]) if 0 <= t - i < K else 0 for i in range(N)]
        v = [int(B[t - j][j]) if 0 <= t - j < K else 0 for j in range(N)]
        sched.append((a, v))
    return sched


def ws_schedule(A, N, M):
    """Weights are preloaded. Activation A[i][r] enters row r at cycle i+r.
    Column c emits C[i][c] at cycle i + N + c - 1."""
    sched = []
    for t in range(M + 2 * N + 4):
        a = [int(A[t - r][r]) if 0 <= t - r < M else 0 for r in range(N)]
        sched.append(a)
    return sched


def dump(path, values, bits):
    mask, nibs = (1 << bits) - 1, (bits + 3) // 4
    with open(path, 'w') as f:
        for v in np.asarray(values).flatten():
            f.write(format(int(v) & mask, f'0{nibs}x') + '\n')


if __name__ == '__main__':
    import os

    os.makedirs('stim', exist_ok=True)
    N, K, M, WIDTH, ACCW = 4, 4, 4, 8, 32
    rng = np.random.default_rng(0)
    A = rng.integers(-8, 8, (N, K))
    B = rng.integers(-8, 8, (K, N))
    dump('stim/A.hex', A, WIDTH)
    dump('stim/B.hex', B, WIDTH)
    dump('stim/C.hex', A @ B, ACCW)
    print('expected C =\n', A @ B)