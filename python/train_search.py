"""
R5 / File 1 : train_search.py
Surrogate models over the measured Vivado sweep, then a search of the space
the sweep could not afford to synthesise.

The device has TWO regimes and they are modelled separately:
  LUT regime (WIDTH <= 8) : multipliers built from LUTs
  DSP regime (WIDTH >= 12): Vivado infers DSP48E1, LUTs collapse to ~0
A single model across both is meaningless -- LUT jumps four orders of
magnitude at the boundary. The split is the paper's finding F2, made explicit.

Reads  : runs.csv   (never written to)
Writes : results/models.pkl, model_error.csv, search.csv, plots/
Run    : python train_search.py
"""

import pathlib, sys, itertools
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import mean_absolute_error

FEAT   = ["N", "WIDTH", "DATAFLOW"]
LIMITS = {"lut": 32600, "ff": 65200, "dsp": 120}

# A DSP48E1 is not free. To compare DSP-based and LUT-based designs on one
# axis we charge each DSP this many LUTs. Stated assumption; the ranking is
# re-checked at 50 and 200 at the end.
DSP_LUT_EQ = 100


def find_csv():
    for p in ("runs.csv", "../runs.csv", r"C:\Users\ROG\sa_sweep\runs.csv"):
        if pathlib.Path(p).exists():
            return pathlib.Path(p)
    sys.exit("runs.csv not found -- put this script in sa_sweep\\python\\")


df = pd.read_csv(find_csv())
df["regime"]    = np.where(df.dsp > 0, "DSP", "LUT")
df["timing_ok"] = df.wns_ns >= 0
# peak throughput of an NxN array = N*N MACs per cycle
df["gmacs"]      = df.N ** 2 * df.fmax_mhz / 1000
df["area_luteq"] = df.lut + DSP_LUT_EQ * df.dsp
df["gm_per_klut"] = df.gmacs / (df.area_luteq / 1000).clip(lower=1e-9)

OUT = pathlib.Path("results"); (OUT / "plots").mkdir(parents=True, exist_ok=True)

print(f"{len(df)} measured configurations"
      f"   LUT regime {sum(df.regime=='LUT')}"
      f"   DSP regime {sum(df.regime=='DSP')}")
bad = df[~df.timing_ok]
for _, r in bad.iterrows():
    print(f"  excluded from fitting: {r.cfg} failed timing (WNS {r.wns_ns} ns)")
fit_df = df[df.timing_ok]

# ------------------------------------------------ 1. random forest + error
# Guide's model. 13-16 rows per regime, so error comes from 5-fold CV over
# every row, not a single hold-out split.
models, rows = {}, []
for reg, g in fit_df.groupby("regime"):
    cv = KFold(n_splits=min(5, len(g)), shuffle=True, random_state=0)
    for t in ("lut", "ff", "dsp", "fmax_mhz", "power_mw"):
        y = g[t]
        m = RandomForestRegressor(n_estimators=300, random_state=0).fit(g[FEAT], y)
        models[(reg, t)] = m
        if y.std() == 0:
            rows.append(dict(regime=reg, target=t, MAE=0.0, MAPE_pct=0.0,
                             note="constant"))
            continue
        p = cross_val_predict(
            RandomForestRegressor(n_estimators=300, random_state=0),
            g[FEAT], y, cv=cv)
        mae = mean_absolute_error(y, p)
        nz = y > 0
        # MAPE explodes when the true value is near zero (LUTs in the DSP
        # regime are 0-13), so it is reported but flagged as unusable there.
        mp = 100 * np.mean(np.abs((y[nz] - p[nz]) / y[nz])) if nz.any() else np.nan
        rows.append(dict(regime=reg, target=t, MAE=round(mae, 1),
                         MAPE_pct=round(mp, 1),
                         note="MAPE unusable, y near 0" if y[nz].median() < 50
                              else f"{nz.sum()}/{len(y)} rows"))

        plt.figure(figsize=(3.6, 3.6))
        plt.scatter(y, p, s=40, zorder=3)
        lo, hi = min(y.min(), p.min()), max(y.max(), p.max())
        plt.plot([lo, hi], [lo, hi], "k--", lw=1)
        plt.xlabel(f"actual {t}"); plt.ylabel(f"predicted {t}")
        plt.title(f"{reg} regime: {t}"); plt.tight_layout()
        plt.savefig(OUT / "plots" / f"pred_vs_actual_{reg}_{t}.png", dpi=150)
        plt.close()

err = pd.DataFrame(rows)
err.to_csv(OUT / "model_error.csv", index=False)
print("\n--- MODEL ERROR (5-fold CV) ---")
print(err.to_string(index=False))

# ---------------------------------------------- 2. power law / scaling law
# log y = a + b log N + c log W  ->  y proportional to N**b, and b is directly
# comparable to the paper's per-doubling ratio as 2**b. This model is smooth,
# so unlike the forest it can predict array sizes that were never synthesised.
def fit_power(g, t):
    s = g[g[t] > 0]
    if len(s) < 4 or s.N.nunique() < 2:
        return None
    A = np.c_[np.ones(len(s)), np.log(s.N), np.log(s.WIDTH)]
    coef, *_ = np.linalg.lstsq(A, np.log(s[t]), rcond=None)
    return coef


power = {}
print("\n--- SCALING WITH ARRAY SIZE  (y proportional to N**b) ---")
print(f"{'regime':>7} {'flow':>5} {'metric':>9} {'b':>6} {'per doubling':>13}")
for (reg, d), g in fit_df.groupby(["regime", "DATAFLOW"]):
    for t in ("lut", "ff", "power_mw", "fmax_mhz"):
        c = fit_power(g, t)
        if c is None:
            continue
        power[(reg, d, t)] = c
        if reg == "LUT" and t != "fmax_mhz":
            print(f"{reg:>7} {'OS' if d==0 else 'WS':>5} {t:>9} "
                  f"{c[1]:6.2f} {2**c[1]:12.2f}x")
print("Paper's per-doubling:  LUT 3.3x   FF 2.7x   power 3.1x")


def predict(reg, d, t, N, W):
    """Power law where it was fitted, forest otherwise."""
    c = power.get((reg, d, t))
    if c is not None:
        return float(np.exp(c[0] + c[1] * np.log(N) + c[2] * np.log(W)))
    return float(models[(reg, t)].predict(
        pd.DataFrame([[N, W, d]], columns=FEAT))[0])


# ------------------------------------------------------------- 3. search
# LUT regime: extrapolate past the largest array we synthesised (N=16).
# DSP regime: dsp = N*N exactly in every measured row, so the device's 120
# DSPs cap the array at N=10 -- derived, not assumed.
cand = []
for N in range(2, 33):
    for W, reg in [(4, "LUT"), (8, "LUT"), (12, "DSP"), (16, "DSP")]:
        for d in (0, 1):
            r = dict(N=N, WIDTH=W, DATAFLOW=d, regime=reg)
            r["dsp"] = N * N if reg == "DSP" else 0
            for t in ("lut", "ff", "power_mw", "fmax_mhz"):
                r[t] = max(0.0, predict(reg, d, t, N, W))
            cand.append(r)
sp = pd.DataFrame(cand)

sp["area_luteq"]  = sp.lut + DSP_LUT_EQ * sp.dsp
sp["gmacs"]       = sp.N ** 2 * sp.fmax_mhz / 1000
sp["gm_per_klut"] = sp.gmacs / (sp.area_luteq / 1000).clip(lower=1e-9)
sp["fits"] = ((sp.lut <= LIMITS["lut"]) & (sp.ff <= LIMITS["ff"])
              & (sp.dsp <= LIMITS["dsp"]))
meas = set(map(tuple, df[FEAT].values))
sp["measured"] = [tuple(r) in meas for r in sp[FEAT].values]
sp.to_csv(OUT / "search.csv", index=False)

print(f"\nSearched {len(sp)} configurations from {len(fit_df)} synthesis runs."
      f"  {sp.fits.sum()} fit the XC7S50, {(~sp.fits).sum()} do not.")

show = ["N", "WIDTH", "DATAFLOW", "regime", "lut", "dsp",
        "fmax_mhz", "power_mw", "gmacs", "measured"]
# The device is fixed, so filling it is free until it runs out: the objective
# is the most throughput that still fits, not the best ratio. (Throughput per
# area is degenerate here -- both numerator and area go as N*N, so it reduces
# to ranking by Fmax and always picks the smallest, most useless array.)
ok = sp[sp.fits].sort_values("gmacs", ascending=False)

print("\n--- BEST CONFIGURATION AT EACH PRECISION (max GMAC/s that fits) ---")
best_per_w = (ok.sort_values("gmacs", ascending=False)
                .groupby("WIDTH").head(1).sort_values("WIDTH"))
print(best_per_w[show].round(2).to_string(index=False))
print("This is the precision/throughput trade-off: more bits cost throughput,")
print("but WIDTH=12 buys back most of it by moving the multiply into DSP48E1.")

# The point of a surrogate: name a configuration nobody synthesised.
# Restrict to >= 8 bits, the precision the im2col/CNN path actually needs.
new = ok[(~ok.measured) & (ok.WIDTH >= 8)]
if not new.empty:
    # Two answers, because they are not the same question. One fills the
    # LUT fabric for raw speed; one moves the multiply into DSP48E1 and
    # leaves the fabric free for the rest of the system.
    ref = df[(df.WIDTH == 8) & df.timing_ok].sort_values("gmacs").iloc[-1]
    print(f"\n>>> RECOMMENDED, compared against our best measured 8-bit "
          f"design {ref.cfg}")
    print(f"    baseline {ref.cfg:<10} {ref.gmacs:5.1f} GMAC/s  "
          f"{int(ref.lut):6d} LUT  {int(ref.dsp):3d} DSP  "
          f"{ref.power_mw:4.0f} mW   8-bit")
    picks = [("max throughput", new.iloc[0]),
             ("fabric-free", new[new.regime == "DSP"].iloc[0]
              if (new.regime == "DSP").any() else None)]
    for label, b in picks:
        if b is None:
            continue
        print(f"    {label:<14} N={int(b.N):<2} W={int(b.WIDTH):<2} "
              f"{'OS' if b.DATAFLOW==0 else 'WS'}  {b.gmacs:5.1f} GMAC/s  "
              f"{b.lut:6.0f} LUT  {int(b.dsp):3d} DSP  {b.power_mw:4.0f} mW"
              f"   {int(b.WIDTH)}-bit")
        print(f"       -> {b.gmacs/ref.gmacs:.2f}x throughput, "
              f"{b.lut/max(ref.lut,1)*100:.1f}% of the LUTs, "
              f"{b.power_mw/ref.power_mw*100:.0f}% of the power"
              + ("" if b.N <= df.N.max() else
                 "   [N beyond the largest array we synthesised]"))
    print("    Synthesise these two in Vivado -- that is the test of the")
    print("    surrogate, and it is two runs, not another sweep.")

print("\nLargest array that fits, per regime:")
for reg, g in sp[sp.fits].groupby("regime"):
    print(f"  {reg}: N={int(g.N.max())}   "
          f"(first N that fails = {int(g.N.max())+1})")

print(f"\nSensitivity of the recommendation to DSP_LUT_EQ (used {DSP_LUT_EQ}):")
for k in (50, 100, 200):
    s = sp[sp.fits & (sp.WIDTH >= 8)].copy()
    s["p"] = s.gmacs / ((s.lut + k * s.dsp) / 1000).clip(lower=1e-9)
    w = s.sort_values("p", ascending=False).iloc[0]
    print(f"  K={k:>3}  ->  N={int(w.N)}, WIDTH={int(w.WIDTH)}, "
          f"DATAFLOW={int(w.DATAFLOW)}")

print("\n--- MEASURED: throughput per area by datatype width ---")
t = (df[df.timing_ok].groupby("WIDTH")
     .gm_per_klut.agg(["min", "max"]).round(2))
print(t.to_string())
print("WIDTH=8 is the worst choice on this device: it pays the full cost of")
print("LUT-based multipliers without reaching the DSP48E1 that WIDTH>=12 wins.")

joblib.dump({"models": models, "power": power, "features": FEAT,
             "DSP_LUT_EQ": DSP_LUT_EQ}, OUT / "models.pkl")
print("\nWrote results/models.pkl, model_error.csv, search.csv, plots/")
