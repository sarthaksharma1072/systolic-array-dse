
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def quantize(tensor, bits):
    """Convert values to signed integers of the selected bit width."""
    qmax = (1 << (bits - 1)) - 1
    qmin = -(1 << (bits - 1))

    max_value = tensor.abs().max().item()

    if max_value == 0:
        return torch.zeros_like(tensor, dtype=torch.int64)

    return torch.round(
        tensor / max_value * qmax
    ).clamp(qmin, qmax).to(torch.int64)


def save_hex(path, values, bits):
    """Save signed integers as two's-complement hexadecimal."""
    mask = (1 << bits) - 1
    digits = (bits + 3) // 4

    with open(path, "w") as f:
        for value in np.asarray(values).flatten():
            f.write(f"{int(value) & mask:0{digits}x}\n")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--array-size", type=int, default=16)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--accw", type=int, default=32)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out-dir", type=str, default="/content/stim")

    args = parser.parse_args()

    N = args.array_size
    WIDTH = args.width
    ACCW = args.accw

    if WIDTH < 2 or ACCW < WIDTH:
        raise ValueError("Invalid WIDTH or ACCW")

    if N not in (2, 4, 8, 16):
        raise ValueError("N must be 2, 4, 8, or 16")

    if N < 12:
        raise ValueError("This convolution example needs N=16")

    # 1. Create a sample convolution layer
    torch.manual_seed(args.seed)

    conv = nn.Conv1d(
        in_channels=4,
        out_channels=4,
        kernel_size=3,
        bias=False
    ).double()

    x = torch.relu(torch.randn(1, 4, 16, dtype=torch.float64))

    # 2. Quantize input and weights
    qx = quantize(x, WIDTH)
    qw = quantize(conv.weight.detach(), WIDTH)

    # 3. Convert input windows into rows using im2col
    patches = F.unfold(
        qx.to(torch.float64).unsqueeze(-1),
        kernel_size=(3, 1)
    )

    A = (
        patches.squeeze(0)
        .transpose(0, 1)
        .to(torch.int64)
        .cpu()
        .numpy()
    )

    # 4. Flatten each filter into one column
    B = (
        qw.reshape(4, -1)
        .transpose(0, 1)
        .cpu()
        .numpy()
    )

    # 5. Calculate matrix multiplication
    C = A @ B

    # 6. Independently check against quantized convolution
    reference = F.conv1d(
        qx.to(torch.float64),
        qw.to(torch.float64)
    )

    reference = (
        reference.squeeze(0)
        .transpose(0, 1)
        .to(torch.int64)
        .cpu()
        .numpy()
    )

    np.testing.assert_array_equal(C, reference)

    # 7. Pad matrices to fit the 16x16 array
    A_pad = np.zeros((A.shape[0], N), dtype=np.int64)
    B_pad = np.zeros((N, N), dtype=np.int64)

    A_pad[:, :A.shape[1]] = A
    B_pad[:B.shape[0], :B.shape[1]] = B

    C_pad = A_pad @ B_pad

    np.testing.assert_array_equal(C_pad[:, :4], C)
    np.testing.assert_array_equal(C_pad[:, 4:], 0)

    # Check that the output fits the accumulator width
    limit = 1 << (ACCW - 1)

    if C_pad.min() < -limit or C_pad.max() >= limit:
        raise ValueError("Output exceeds accumulator width")

    # 8. Save the hardware stimulus files
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    save_hex(out / "A_conv.hex", A_pad, WIDTH)
    save_hex(out / "B_conv.hex", B_pad, WIDTH)
    save_hex(out / "C_conv.hex", C_pad, ACCW)
    save_hex(out / "C_conv_valid.hex", C, ACCW)

    metadata = {
        "N": N,
        "WIDTH": WIDTH,
        "ACCW": ACCW,
        "A_shape": list(A.shape),
        "B_shape": list(B.shape),
        "C_shape": list(C.shape),
        "padded_A_shape": list(A_pad.shape),
        "padded_B_shape": list(B_pad.shape),
        "padded_C_shape": list(C_pad.shape),
        "seed": args.seed,
        "verification": "PASS"
    }

    (out / "im2col_metadata.json").write_text(
        json.dumps(metadata, indent=2)
    )

    print("\n--- IM2COL GENERATION SUMMARY ---")
    print(f"Valid GEMM: A {A.shape} @ B {B.shape} -> C {C.shape}")
    print(f"Padded A: {A_pad.shape}")
    print(f"Padded B: {B_pad.shape}")
    print(f"Padded C: {C_pad.shape}")
    print("PASS: GEMM matches quantized PyTorch convolution")
    print("Hexadecimal stimulus files generated.")
    print("Note: RTL hardware verification is still required.")


if __name__ == "__main__":
    main()
