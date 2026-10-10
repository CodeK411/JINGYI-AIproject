FEATURES = "../data/features.csv"
NAMES    = "../data/Swindon LSOA local names.csv"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patheffects import withStroke
import numpy as np
import pandas as pd

TARGET = "LSOA GVA Estimates (millions)"

feats = pd.read_csv(FEATURES).drop_duplicates(subset=["LSOA21CD"], keep="first")
names = pd.read_csv(NAMES)

swindon_codes = set(names["LSOA21CD"])
sw = pd.merge(names[["LSOA21CD", "Local LSOA21 Name"]], feats,
              on="LSOA21CD", how="left")
ot = feats[~feats["LSOA21CD"].isin(swindon_codes)].copy()
ot["Local LSOA21 Name"] = ot["LSOA21NM"]

def prep(df):
    d = df.dropna(subset=[TARGET]).copy()
    d["jobs"] = d["total_employees"]
    d["jobs_per_resident"] = d["employment_rate_per_pop"]
    d["gva_per_job_k"] = d[TARGET] * 1000 / d["jobs"]      # £m -> £k per job
    return d.dropna(subset=["jobs", "jobs_per_resident", "gva_per_job_k"])

sw, ot = prep(sw), prep(ot)
pool = pd.concat([sw, ot])

MX = pool.jobs_per_resident.median()
MY = pool.gva_per_job_k.median()

def classify(d):
    hi_j, hi_p = d.jobs_per_resident >= MX, d.gva_per_job_k >= MY
    return np.select([hi_j & hi_p, hi_j & ~hi_p, ~hi_j & hi_p, ~hi_j & ~hi_p],
                     ["A", "B", "C", "D"], default="?")

sw["q"], ot["q"] = classify(sw), classify(ot)

JOBS, GVA = sw.jobs.sum(), sw[TARGET].sum()
NAMES_Q = {"A": "Economic engines", "B": "High jobs, low output",
           "C": "Commuter suburbs", "D": "Residential, low output"}

def stats(q):
    s, o = sw[sw.q == q], ot[ot.q == q]
    med, reg = s.gva_per_job_k.median(), o.gva_per_job_k.median()
    return dict(n=len(s), jobs=100 * s.jobs.sum() / JOBS,
                val=100 * s[TARGET].sum() / GVA, med=med, reg=reg,
                gap=100 * (med - reg) / reg)

S = {q: stats(q) for q in "ABCD"}

print(f"Swindon LSOAs with GVA : {len(sw)}")
print(f"Comparator LSOAs       : {len(ot)}")
print(f"Median dividers        : {MX:.4f} jobs/resident   £{MY:.1f}k per job")
print(f"Swindon totals         : {JOBS:,.0f} jobs   £{GVA:,.0f}m GVA\n")
print(f"{'':2} {'n':>4} {'%jobs':>7} {'%value':>7} {'£k/job':>8} {'regional':>9} {'gap':>7}")
for q in "BACD":
    s = S[q]
    print(f"{q:2} {s['n']:4d} {s['jobs']:6.1f}% {s['val']:6.1f}% "
          f"{s['med']:8.1f} {s['reg']:9.1f} {s['gap']:+6.1f}%")
a, b = S["A"]["med"], S["B"]["med"]
print(f"\nA/B ratio of median GVA per job : {a / b:.2f}x")
top = sw.loc[sw[TARGET].idxmax()]
print(f"Largest area: {top['Local LSOA21 Name']} — £{top[TARGET]:,.0f}m "
      f"({100 * top[TARGET] / GVA:.1f}% of borough GVA), group {top.q}")
big = sw.loc[sw.jobs.idxmax()]
print(f"Most jobs:    {big['Local LSOA21 Name']} — {big.jobs:,.0f} jobs "
      f"at £{big.gva_per_job_k:.0f}k each, group {big.q}")

SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"
MUTED, GRID, AXIS   = "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE        = "#2a78d6", "#eb6834"   # validated pair, light surface
CONTEXT             = "#d5d4cd"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": AXIS, "axes.linewidth": .8,
})

fig = plt.figure(figsize=(7.4, 7.8), dpi=300)
gs = fig.add_gridspec(2, 1, height_ratios=[2.55, 1], hspace=.52)
ax = fig.add_subplot(gs[0])
tb = fig.add_subplot(gs[1]); tb.axis("off")

ax.scatter(ot.jobs_per_resident, ot.gva_per_job_k, s=5, color=CONTEXT,
           alpha=.5, linewidths=0, zorder=1, rasterized=True)
ax.axvline(MX, color=AXIS, lw=1.0, ls=(0, (5, 3)), zorder=2)
ax.axhline(MY, color=AXIS, lw=1.0, ls=(0, (5, 3)), zorder=2)

rest, bgrp = sw[sw.q != "B"], sw[sw.q == "B"]
ax.scatter(rest.jobs_per_resident, rest.gva_per_job_k, s=30, color=BLUE,
           alpha=.85, edgecolors=SURFACE, linewidths=.7, zorder=4,
           label="Swindon LSOA — groups A, C, D")
ax.scatter(bgrp.jobs_per_resident, bgrp.gva_per_job_k, s=42, color=ORANGE,
           edgecolors=SURFACE, linewidths=.8, zorder=5,
           label="Swindon LSOA — group B: high jobs, low output")

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(0.0060, 16); ax.set_ylim(19, 2300)
ax.set_xlabel("Jobs per resident   (log scale)", fontsize=9.5, labelpad=6)
ax.set_ylabel("GVA per job, £ thousands   (log scale)", fontsize=9.5, labelpad=6)
ax.set_xticks([0.01, 0.1, 0.19, 1, 10])
ax.set_xticklabels(["0.01", "0.1", "0.19\nmedian", "1", "10"], fontsize=8.2)
ax.set_yticks([25, 50, 79, 200, 500, 1000])
ax.set_yticklabels(["25", "50", "79  median", "200", "500", "1,000"], fontsize=8.2)
ax.grid(True, which="major", color=GRID, lw=.6, zorder=0)
ax.set_axisbelow(True)

for q, (fx, fy, ha, va) in {"C": (.020, .972, "left", "top"),
                            "A": (.980, .972, "right", "top"),
                            "D": (.020, .028, "left", "bottom"),
                            "B": (.980, .028, "right", "bottom")}.items():
    ax.text(fx, fy, q, transform=ax.transAxes, fontsize=19, fontweight="bold",
            color=ORANGE if q == "B" else "#b9b8b1", ha=ha, va=va, zorder=3)

ax.annotate(f"{top['Local LSOA21 Name']}\n"
            f"{100 * top[TARGET] / GVA:.1f}% of Swindon's GVA",
            xy=(top.jobs_per_resident, top.gva_per_job_k), xytext=(0.135, 1700),
            ha="left", va="center", fontsize=8, color=INK, linespacing=1.4,
            zorder=8, path_effects=[withStroke(linewidth=2.6, foreground=SURFACE)],
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=.8, shrinkA=2,
                            shrinkB=4, connectionstyle="arc3,rad=-0.15"))

ax.set_title("Two-thirds of Swindon's jobs create one-quarter of its value",
             fontsize=12.5, fontweight="bold", color=INK, loc="left", pad=12)

h, _ = ax.get_legend_handles_labels()
ctx = plt.Line2D([], [], marker="o", ls="", color=CONTEXT, markersize=4,
                 label=f"Comparator LSOA — 11 neighbouring authorities (n = {len(ot)})")
ax.legend(handles=[h[1], h[0], ctx], loc="upper left",
          bbox_to_anchor=(-0.005, -0.155), frameon=False, fontsize=7.5,
          handletextpad=.5, labelspacing=.36, borderpad=0,
          bbox_transform=ax.transAxes, labelcolor=INK_2)

COLX = [.000, .075, .335, .450, .565, .690, .830, .945]
HEAD = ["", "Group", "Areas", "% of\njobs", "% of\nvalue",
        "Median\n£k per job", "Regional\nmedian", "Gap"]
for x, head in zip(COLX, HEAD):
    ha = "left" if x < .3 else "right"
    tb.text(x + (0 if ha == "left" else .055), 1.13, head, fontsize=7.4,
            color=MUTED, ha=ha, va="top", linespacing=1.40,
            transform=tb.transAxes)
tb.plot([0, 1], [.885, .885], color=AXIS, lw=.8, transform=tb.transAxes,
        clip_on=False)

for i, q in enumerate("BACD"):            # B first: it is the finding
    y, s, hot = .775 - i * .172, S[q], q == "B"
    tb.scatter([.012], [y + .045], s=34 if hot else 26,
               color=ORANGE if hot else BLUE, transform=tb.transAxes,
               clip_on=False, zorder=3, edgecolors=SURFACE, linewidths=.7)
    tb.text(COLX[1], y + .045, f"{q}   {NAMES_Q[q]}", fontsize=8.2,
            fontweight="bold" if hot else "normal",
            color=INK if hot else INK_2, ha="left", va="center",
            transform=tb.transAxes)
    for x, v in zip(COLX[2:], [f"{s['n']}", f"{s['jobs']:.0f}%", f"{s['val']:.0f}%",
                               f"{s['med']:.0f}", f"{s['reg']:.0f}", f"{s['gap']:+.0f}%"]):
        tb.text(x + .055, y + .045, v, fontsize=8.2,
                fontweight="bold" if hot else "normal",
                color=INK if hot else INK_2, ha="right", va="center",
                transform=tb.transAxes)
    if hot:
        tb.plot([0, 1], [y - .045, y - .045], color=GRID, lw=.7,
                transform=tb.transAxes, clip_on=False)

tb.text(0, -.02,
        f"Group B holds two-thirds of Swindon's jobs and produces "
        f"£{S['B']['med']:.0f}k per job against £{S['B']['reg']:.0f}k in comparable "
        f"areas elsewhere — an {abs(S['B']['gap']):.0f}% gap.  Between A and B\n"
        f"the same job is worth {a / b:.1f}× more.  The borough's single largest "
        f"employment site, {big['Local LSOA21 Name']}, sits in group "
        f"{big.q}: {big.jobs:,.0f} jobs at £{big.gva_per_job_k:.0f}k each.",
        fontsize=8, color=INK, va="top", linespacing=1.55, transform=tb.transAxes)

n_clip = int(((pool.gva_per_job_k < 19) | (pool.gva_per_job_k > 2300)).sum())
tb.text(0, -.30,
        f"Swindon n = {len(sw)} LSOAs.  Dividers are medians across all {len(pool):,} "
        f"modelled LSOAs ({len(sw)} Swindon + {len(ot)} comparator), so each Swindon "
        f"area is placed\nagainst an external benchmark rather than Swindon's own "
        f"middle.  Group figures are medians of GVA per job, so the single area "
        f"holding {100 * top[TARGET] / GVA:.1f}% of\nborough GVA cannot distort them.  "
        f"Percentages of jobs and of value are shares of the borough total.  "
        f"{n_clip} comparator areas fall outside the\nplotted range of the vertical "
        f"axis; all {len(sw)} Swindon areas are shown.",
        fontsize=6.6, color=MUTED, va="top", linespacing=1.7,
        transform=tb.transAxes)

fig.savefig("../figures/fig_typology.png", dpi=300, bbox_inches="tight", facecolor=SURFACE)
fig.savefig("../figures/fig_typology.pdf", bbox_inches="tight", facecolor=SURFACE)
print("\nwrote fig_typology.png and fig_typology.pdf")
