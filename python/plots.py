"""
R5 / File 3 : plots.py  --  the figures for the slides.
Reads runs.csv and results/search.csv. Writes results/plots/*.png
Run : python plots.py
"""

import pathlib, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = pathlib.Path("results/plots"); P.mkdir(parents=True, exist_ok=True)
csv = next((pathlib.Path(p) for p in
            ("runs.csv", "../runs.csv", r"C:\Users\ROG\sa_sweep\runs.csv")
            if pathlib.Path(p).exists()), None)
if csv is None:
    sys.exit("runs.csv not found")
df = pd.read_csv(csv)
df["ok"] = df.wns_ns >= 0
df["gmacs"] = df.N ** 2 * df.fmax_mhz / 1000

# --- Figure 1: area scaling at 8 bits, with the paper's slope ------------
h = df[(df.WIDTH == 8) & df.ok].sort_values("N")
plt.figure(figsize=(5.5, 4.2))
for d, nm, mk in ((0, "ours, OS", "o"), (1, "ours, WS", "s")):
    s = h[h.DATAFLOW == d]
    plt.plot(s.N, s.lut, mk + "-", label=nm)
n0 = h.N.min(); l0 = h[h.N == n0].lut.max()
ns = np.array(sorted(h.N.unique()), float)
plt.plot(ns, l0 * (ns / n0) ** np.log2(3.3), "k--", lw=1,
         label="paper slope (3.3x / doubling)")
plt.xscale("log", base=2); plt.yscale("log", base=2)
plt.xlabel("array dimension N"); plt.ylabel("LUTs")
plt.title("Area scaling at WIDTH = 8")
plt.legend(); plt.grid(alpha=.3, which="both"); plt.tight_layout()
plt.savefig(P / "scaling_lut.png", dpi=150); plt.close()

# --- Figure 2: WS vs OS, same area, much less power ----------------------
piv = h.pivot_table(index="N", columns="DATAFLOW", values=["lut", "power_mw"])
x = np.arange(len(piv)); w = .38
fig, ax = plt.subplots(1, 2, figsize=(9, 3.8))
for k, (c, unit) in enumerate((("lut", "LUTs"), ("power_mw", "dynamic mW"))):
    ax[k].bar(x - w/2, piv[c][0], w, label="OS")
    ax[k].bar(x + w/2, piv[c][1], w, label="WS")
    ax[k].set_xticks(x); ax[k].set_xticklabels(piv.index)
    ax[k].set_xlabel("N"); ax[k].set_ylabel(unit)
    ax[k].set_title("area" if k == 0 else "dynamic power")
    ax[k].legend(); ax[k].grid(axis="y", alpha=.3)
fig.suptitle("Weight stationary: same area, much lower power")
plt.tight_layout(); plt.savefig(P / "dataflow.png", dpi=150); plt.close()

# --- Figure 3: the DSP cliff -- our finding F2 ---------------------------
fig, ax = plt.subplots(1, 3, figsize=(11, 3.6))
g = df[(df.DATAFLOW == 1) & df.ok]
for k, (c, unit, ttl) in enumerate(
        ((("lut"), "LUTs", "LUTs collapse"),
         (("dsp"), "DSP48E1", "work moves into DSPs"),
         (("fmax_mhz"), "MHz", "and it gets faster"))):
    for N in sorted(g.N.unique()):
        s = g[g.N == N].sort_values("WIDTH")
        ax[k].plot(s.WIDTH, s[c], "o-", label=f"N={N}")
    ax[k].axvline(10, color="crimson", ls="--", lw=1)
    ax[k].set_xlabel("datatype WIDTH (bits)"); ax[k].set_ylabel(unit)
    ax[k].set_title(ttl); ax[k].grid(alpha=.3)
    if k == 0:
        ax[k].set_yscale("symlog"); ax[k].legend(fontsize=8)
fig.suptitle("Finding F2: at WIDTH >= 12 Vivado switches to DSP48E1 "
             "(weight stationary)")
plt.tight_layout(); plt.savefig(P / "dsp_cliff.png", dpi=150); plt.close()

# --- Figure 4: the searched design space ---------------------------------
sp = pathlib.Path("results/search.csv")
if sp.exists():
    s = pd.read_csv(sp)
    area = s.lut + 100 * s.dsp
    fit = s.fits.astype(bool)
    plt.figure(figsize=(6.2, 4.4))
    plt.scatter(area[fit], s.gmacs[fit], s=10, c="#ccc", label="predicted, fits")
    plt.scatter(area[~fit], s.gmacs[~fit], s=10, c="#f3c0c0",
                marker="x", label="predicted, too big")
    m = s.measured.astype(bool)
    plt.scatter(area[m], s.gmacs[m], s=45, c="#1f77b4",
                edgecolor="k", zorder=3, label="synthesised")
    best = s[fit & ~m & (s.WIDTH >= 8)].sort_values("gmacs").iloc[-1]
    plt.scatter([best.lut + 100*best.dsp], [best.gmacs], s=240,
                facecolor="none", edgecolor="crimson", lw=2, zorder=4,
                label=f"pick: N={int(best.N)} W={int(best.WIDTH)}")
    plt.xscale("log")
    plt.xlabel("area  (LUT + 100 x DSP)"); plt.ylabel("peak GMAC/s")
    plt.title(f"{len(s)} configurations explored from {len(df)} synthesis runs")
    plt.legend(fontsize=8); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(P / "design_space.png", dpi=150); plt.close()
else:
    print("results/search.csv missing -- run train_search.py first")

for f in sorted(P.glob("*.png")):
    print("wrote", f)
