"""
R5 / File 2 : predict.py  --  the live demo for the viva.
Asks the surrogate what a configuration costs, in milliseconds, instead of
the ~4 minutes Vivado needs to answer the same question.

Run : python predict.py 10 12 1        (N  WIDTH  DATAFLOW)
"""

import sys, pathlib, joblib
import numpy as np, pandas as pd

LIMITS = {"lut": 32600, "ff": 65200, "dsp": 120}

if len(sys.argv) != 4:
    sys.exit("usage: python predict.py <N> <WIDTH> <DATAFLOW 0=OS 1=WS>")
N, W, D = (int(a) for a in sys.argv[1:4])
if D not in (0, 1):
    sys.exit("DATAFLOW must be 0 (output stationary) or 1 (weight stationary)")

mp = pathlib.Path("results/models.pkl")
if not mp.exists():
    sys.exit("results/models.pkl not found -- run  python train_search.py  first")
S = joblib.load(mp)

reg = "DSP" if W >= 12 else "LUT"
pred = {}
for t in ("lut", "ff", "power_mw", "fmax_mhz"):
    c = S["power"].get((reg, D, t))
    if c is not None:
        pred[t] = float(np.exp(c[0] + c[1] * np.log(N) + c[2] * np.log(W)))
    else:
        pred[t] = float(S["models"][(reg, t)].predict(
            pd.DataFrame([[N, W, D]], columns=S["features"]))[0])
    pred[t] = max(0.0, pred[t])
# Every measured row in the DSP regime used exactly N*N DSP48E1 slices.
pred["dsp"] = N * N if reg == "DSP" else 0

print(f"\nN={N}  WIDTH={W}  DATAFLOW={D} ({'OS' if D == 0 else 'WS'})"
      f"   -> {reg} regime")
print("-" * 46)
for t in ("lut", "ff", "dsp", "fmax_mhz", "power_mw"):
    print(f"  predicted {t:<9} {pred[t]:10.1f}")
print(f"  throughput      {N*N*pred['fmax_mhz']/1000:10.1f} GMAC/s")

over = [f"{k} {pred[k]:.0f} > {v}" for k, v in LIMITS.items() if pred[k] > v]
print("-" * 46)
print("  DOES NOT FIT on XC7S50: " + "; ".join(over) if over
      else "  fits on the XC7S50")

# If this point was synthesised, print the measured truth beside it.
for p in ("runs.csv", "../runs.csv", r"C:\Users\ROG\sa_sweep\runs.csv"):
    if pathlib.Path(p).exists():
        df = pd.read_csv(p)
        hit = df[(df.N == N) & (df.WIDTH == W) & (df.DATAFLOW == D)]
        if not hit.empty:
            r = hit.iloc[0]
            print("\n  measured by Vivado:")
            for t in ("lut", "ff", "dsp", "fmax_mhz", "power_mw"):
                e = abs(pred[t] - r[t]) / r[t] * 100 if r[t] else float("nan")
                print(f"    actual {t:<9} {r[t]:10.1f}"
                      + (f"   ({e:.0f}% off)" if r[t] else ""))
        else:
            print("\n  never synthesised -- this is a genuine prediction.")
        break

print("\n  (Vivado would take about 4 minutes to produce this.)")
