# ML-Guided Design Space Exploration of a Systolic Array CNN Accelerator

A parameterised systolic array accelerator on a Xilinx Spartan-7 **XC7S50**, swept across
its configuration space, with a surrogate model trained on the measured synthesis data
that selects a configuration **never synthesised** — and is then verified in Vivado to
within 1%.

Replication and extension of:
> Gookyi et al., *"Deep Learning Accelerators' Configuration Space Exploration Effect on
> Performance and Resource Utilization: A Gemmini Case Study"*, **Sensors 2023, 23, 2380**.
> [doi.org/10.3390/s23052380](https://doi.org/10.3390/s23052380)

---

## Headline result

The surrogate selected **N = 10, 12-bit, weight-stationary**, a configuration held out of
its training data. One Vivado run then checked it:

| Metric | Model predicted | Vivado measured | Error |
|---|---:|---:|---:|
| DSP48E1 | 100 | 100 | **0%** |
| Fmax | 226.5 MHz | 225.6 MHz | **0.4%** |
| Dynamic power | 121.2 mW | 120.0 mW | **1.0%** |
| Flip-flops | 1 007 | 840 | 20% |

Against the baseline we built by hand:

| Metric | Baseline `N16_W8_D0` | Model's pick `N10_W12_D1` | Ratio |
|---|---:|---:|---:|
| Peak throughput | 28.0 GMAC/s | 22.6 GMAC/s | 81% |
| Slice LUTs | 24 104 | **1** | **0.004%** |
| Dynamic power | 448 mW | **120 mW** | **27%** |
| Fmax | 109.4 MHz | **225.6 MHz** | **2.06×** |
| Precision | 8-bit | **12-bit** | higher |

Four fifths of the throughput, the entire LUT fabric handed back, a quarter of the power,
twice the clock — at *higher* precision.

---

## What replicated from the paper

| ID | Finding | Paper | This work |
|---|---|---|---|
| **F1** | Area and power scale with array size | 3.3× LUT, 2.7× FF, 3.1× power per doubling | 3.95×/3.99× LUT, 3.55×/4.08× FF, 3.54×/3.31× power — fitted exponent **b = 2.00** |
| **F2** | Datatype width decides LUT vs DSP mapping | reported | DSP48E1 inferred at WIDTH ≥ 12; LUTs fall **535×** |
| **F3** | Fmax is non-monotonic in array size | reported | 112.7 (N=4) → 113.2 (N=8) → 109.4 MHz (N=16) |

Our ratios run steeper because the paper measures a full Gemmini SoC, whose fixed logic
does not scale with N, while we measure the systolic mesh alone — which lands on pure N².
The paper's own Figure 16 attributes **95.164% of Gemmini's LUTs to the ExecuteController**,
so the mesh is where the cost lives.

## What this work adds

- **Dataflow comparison in synthesis.** The paper compares output- and weight-stationary
  for *performance* only; its synthesis results vary array size and the im2col module, not
  dataflow. We synthesised both: **weight-stationary uses 56% less dynamic power at
  equal area** (199 mW vs 448 mW at N = 16).
- **8 bits is the worst datatype width on this device.** It pays the full cost of
  LUT-based multipliers without reaching the DSP48E1 that WIDTH ≥ 12 wins.
- **ML-guided design space search.** 248 configurations evaluated from 29 synthesis runs;
  132 ruled out as exceeding the device, and the best of the remaining 116 verified in
  hardware.
- **Derived device ceilings** without synthesis: N ≤ 10 in the DSP regime (N = 11 needs
  121 of 120 DSPs), N ≤ 24 in the LUT regime.

---

## Repository layout

```
rtl/        pe.sv, systolic_array.sv, ctrl_fsm.v, top.v
tb/         tb_os.v, tb_ws.v, tb_top.v, tb_conv.v
stim/       hex stimulus + im2col metadata
python/     golden.py, im2col_gen.py, train_search.py, predict.py, plots.py, fig1718.py
vivado/     timing.xdc, run.tcl, sweep.tcl
results/    runs.csv (29 measured configurations), search.csv, model_error.csv,
            models.pkl, reports/N10_W12_D1/, figures/
```

### The design

`pe.sv` is one multiply-accumulate cell that compiles to either dataflow on a parameter.
`systolic_array.sv` tiles it into an N × N mesh with generate loops. `ctrl_fsm.v` sequences
weight load, the skew schedule and result capture; `top.v` wraps the mesh with memories.
Four compile-time parameters define every design point: **N, WIDTH, ACCW, DATAFLOW**.

### Method notes

- **Out-of-context synthesis** is required: the array exposes 11 392 ports at N = 16 and the
  device has 210 pins. The paper synthesised the Mesh the same way.
- **Top module is `systolic_array`**, not `top`, so memories and control never enter the
  area figures.
- **Dynamic power only.** Static power is a fixed ~69 mW leakage on this device and would
  mask every trend. The paper also reports dynamic power.
- `runs.csv` holds 29 of 32 grid points. The three missing are all N = 16 at WIDTH ≥ 12,
  and the run that did complete there consumed all 120 DSPs, spilled 25 220 LUTs and still
  failed timing at WNS = −0.390 ns — that region is **demonstrably** infeasible.
- **`N10_W12_D1` is deliberately absent from `runs.csv`.** It is the model's held-out test
  point; adding it would invalidate the prediction claim.

---

## Functional verification

A quantised PyTorch `Conv1d` layer is reshaped by im2col into A (14×16) × B (16×16) and
executed on the array:

```
im2col integration test   N=16  M=14  WIDTH=8  WS
full padded matrix : 0 of 224 elements wrong
real conv output   : 0 of  56 elements wrong  (14x4)
RESULT: PASS -- the array reproduces the PyTorch convolution exactly
```

Both dataflows are also checked against a NumPy golden model at N = 2, 4, 8 and 16.

---

## Reproducing

**Sweep** (Vivado 2025.1):
```
vivado -mode batch -source vivado/sweep.tcl
```
Resumable — configurations whose reports already exist are skipped. ~4 min per run.

**Model and figures:**
```
pip install pandas scikit-learn matplotlib joblib
python python/train_search.py     # trains, searches 248 configurations
python python/predict.py 10 12 1  # ask the model about one configuration
python python/plots.py            # figures
```

**Stimulus:**
```
python python/golden.py                      # random GEMM vectors
python python/im2col_gen.py --out-dir stim   # PyTorch Conv1d -> GEMM
```

---

## Target device

Xilinx Spartan-7 **XC7S50** (`xc7s50csga324-1`): 32 600 LUTs, 65 200 FFs, 120 DSP48E1,
75 BRAM, 210 I/O. Vivado 2025.1, out-of-context synthesis, 10 ns clock constraint.

Roughly 125× smaller than the paper's Virtex UltraScale+ XCVU19P, which is why trends and
ratios are compared rather than absolute values.

---

## Team

B.E. Electronics and VLSI Design, Thapar Institute of Engineering and Technology, Patiala.
