"""
Equivalents of the base paper's Figure 17 and Figure 18, built from runs.csv.
Run:  python fig1718.py        (needs runs.csv in the same folder)
"""
import pandas as pd, numpy as np, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = pathlib.Path("results/paper_figs"); OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv("runs.csv")
df = df[(df.wns_ns >= 0) & (df.WIDTH == 8)]

BLUE, ORANGE, GREY = "#1F5C99", "#E07A2F", "#808A99"
plt.rcParams.update({"font.size": 12, "figure.facecolor": "white",
                     "axes.facecolor": "white"})

# ---------------------------------------------------------- Figure 17 style
# Paper: CLB Registers and CLB LUTs as bars, dynamic power as a line on a
# second axis, across systolic array sizes. Ours uses weight stationary.
d = df[df.DATAFLOW == 1].sort_values("N")
x = np.arange(len(d)); w = 0.36

fig, ax = plt.subplots(figsize=(8, 4.8))
ax.bar(x - w/2, d.ff,  w, color=BLUE,   label="CLB Registers", zorder=3)
ax.bar(x + w/2, d.lut, w, color=ORANGE, label="CLB LUTs",      zorder=3)
ax.set_ylabel("CLB REGISTERS / LUTS")
ax.set_xticks(x); ax.set_xticklabels([f"SA {n}x{n}" for n in d.N])
ax.grid(axis="y", color="#E7E9ED", zorder=0); ax.set_axisbelow(True)

ax2 = ax.twinx()
ax2.plot(x, d.power_mw, "o-", color=GREY, lw=2, ms=8,
         label="Power (mW)", zorder=4)
ax2.set_ylabel("Power (mW)")

h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, 1.14),
          ncol=3, frameon=False)
ax.set_title("Systolic array hardware resource comparison (XC7S50, 8-bit, WS)",
             pad=34, fontsize=13)
fig.tight_layout(); fig.savefig(OUT / "Fig17_equivalent.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------- Figure 18 style
# Paper: performance per area as bars for OS and WS. Its speedup lines are
# relative to a Rocket CPU, which we do not have, so they are omitted.
DSP_EQ = 100
df = df.copy()
df["area"]  = df.lut + DSP_EQ * df.dsp
df["gmacs"] = df.N ** 2 * df.fmax_mhz / 1000
df["ppa"]   = df.gmacs / df.area.clip(lower=1)
p = df.pivot_table(index="N", columns="DATAFLOW", values="ppa").sort_index()

x = np.arange(len(p)); w = 0.36
fig, ax = plt.subplots(figsize=(8, 4.8))
b1 = ax.bar(x - w/2, p[0], w, color="#E8B33C", label="OS Dataflow", zorder=3)
b2 = ax.bar(x + w/2, p[1], w, color="#2E86C1", label="WS Dataflow", zorder=3)
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width()/2, r.get_height()*1.02,
                f"{r.get_height():.4f}", ha="center", fontsize=9)
ax.set_ylabel("Performance per area  (GMAC/s per area unit)")
ax.set_xticks(x); ax.set_xticklabels([f"SA {n}x{n}" for n in p.index])
ax.grid(axis="y", color="#E7E9ED", zorder=0); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False)
ax.set_title("Performance per area of our configurations (XC7S50, 8-bit)",
             fontsize=13)
fig.tight_layout(); fig.savefig(OUT / "Fig18_equivalent.png", dpi=150)
plt.close(fig)

print("Written to", OUT.resolve())
for f in sorted(OUT.glob("*.png")):
    print("  ", f.name)
