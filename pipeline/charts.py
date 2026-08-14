"""Render findings charts (light mode, static PNG) from samples_with_features.csv.

Palette: dataviz reference categorical slots 1-3, validated 3-slot light mode.
Color follows the station everywhere: CREEK=blue, LM5=orange, LM6=aqua.
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
C = {"CREEK": "#2a78d6", "LM5": "#eb6834", "LM6": "#1baf7a"}
LABEL = {
    "CREEK": "San Pedro Creek (E. coli >320)",
    "LM5": "Linda Mar Beach #5 (entero >104)",
    "LM6": "Linda Mar Beach #6 (entero >104)",
}

plt.rcParams.update(
    {
        "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "axes.edgecolor": BASE,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "figure.dpi": 200,
    }
)

RAIN_ORDER = ["dry (0)", "0.1-5mm", "5-15mm", "15-40mm", ">40mm"]


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(False)
    ax.tick_params(length=0)


def headline_frame():
    df = pd.read_csv(ROOT / "data" / "samples_with_features.csv", parse_dates=["date"])
    return df[
        ((df["station"] == "CREEK") & (df["analyte"] == "ecoli"))
        | ((df["station"].isin(["LM5", "LM6"])) & (df["analyte"] == "ent"))
    ].copy()


def chart_rain_response(df):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    stations = ["CREEK", "LM5"]
    x = np.arange(len(RAIN_ORDER))
    w = 0.38
    for i, st in enumerate(stations):
        g = df[df["station"] == st]
        rates, ns = [], []
        for b in RAIN_ORDER:
            gb = g[g["rain_bin"] == b]
            rates.append(100 * gb["exceed"].mean() if len(gb) else np.nan)
            ns.append(len(gb))
        pos = x + (i - 0.5) * (w + 0.02)  # 2px-ish surface gap between pair
        bars = ax.bar(pos, rates, width=w, color=C[st], label=LABEL[st], zorder=3)
        for b, r in zip(bars, rates):
            if not np.isnan(r):
                ax.text(
                    b.get_x() + b.get_width() / 2, r + 1.5, f"{r:.0f}%",
                    ha="center", va="bottom", fontsize=8.5, color=INK,
                )
    ax.set_xticks(x, RAIN_ORDER)
    ax.set_ylim(0, 90)
    ax.set_ylabel("samples exceeding standard (%)")
    ax.set_xlabel("rain in the 72h before sampling")
    ax.set_title(
        "More rain, more failures — but the creek starts high",
        fontsize=13, color=INK, loc="left", pad=14,
    )
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.text(
        0.01, 0.01,
        "County weekly samples: creek 2015–2026 (n=523), beach #5 2000–2026 (n=1,255). "
        "Rain: ERA5 daily at watershed. Single-sample standards, MPN/100mL.",
        fontsize=7, color=MUTED,
    )
    style(ax)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "exceedance_vs_rain.png")
    plt.close(fig)


def chart_dry_baseline(df):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    stations = ["CREEK", "LM5", "LM6"]
    rates, ns = [], []
    for st in stations:
        g = df[(df["station"] == st) & (df["prev30"] == 0)]
        rates.append(100 * g["exceed"].mean())
        ns.append(len(g))
    bars = ax.bar(
        np.arange(3), rates, width=0.5, color=[C[s] for s in stations], zorder=3
    )
    for b, r, n in zip(bars, rates, ns):
        ax.text(
            b.get_x() + b.get_width() / 2, r + 1.2, f"{r:.0f}%",
            ha="center", va="bottom", fontsize=10, color=INK, fontweight="bold",
        )
        ax.text(
            b.get_x() + b.get_width() / 2, -4.5, f"n={n}",
            ha="center", va="top", fontsize=8, color=MUTED,
        )
    ax.set_xticks(np.arange(3), [LABEL[s].split(" (")[0] for s in stations])
    ax.set_ylim(0, 62)
    ax.set_ylabel("samples exceeding standard (%)")
    ax.set_title(
        "After 30 days with zero rain, the creek still fails half the time",
        fontsize=13, color=INK, loc="left", pad=14,
    )
    fig.text(
        0.01, 0.01,
        "Samples with no measured rain in the prior 30 days. Beach #6 sits away from "
        "the creek mouth (sampled 1998–2008); #5 is at the creek mouth.",
        fontsize=7, color=MUTED,
    )
    style(ax)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT / "dry_weather_baseline.png")
    plt.close(fig)


def chart_lm5_by_year(df):
    g = df[df["station"] == "LM5"].copy()
    g["year"] = g["date"].dt.year
    yearly = g.groupby("year").agg(rate=("exceed", "mean"), n=("exceed", "size"))
    yearly = yearly[yearly["n"] >= 20]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(
        yearly.index, 100 * yearly["rate"], color=C["LM5"], linewidth=2,
        marker="o", markersize=5, zorder=3,
    )
    last = yearly.index[-1]
    ax.annotate(
        f"{100 * yearly.loc[last, 'rate']:.0f}%", (last, 100 * yearly.loc[last, "rate"]),
        textcoords="offset points", xytext=(8, 2), fontsize=9, color=INK,
    )
    ax.set_ylim(0, 80)
    ax.set_ylabel("samples exceeding standard (%)")
    ax.set_title(
        "Linda Mar Beach #5: enterococcus exceedance by year",
        fontsize=13, color=INK, loc="left", pad=14,
    )
    fig.text(
        0.01, 0.01,
        "Years with ≥20 weekly samples. Single-sample standard >104 MPN/100mL. "
        "The step up after 2020 needs decomposition (methods/season mix) before "
        "being read as pure degradation.",
        fontsize=7, color=MUTED,
    )
    style(ax)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT / "lm5_by_year.png")
    plt.close(fig)


def main():
    df = headline_frame()
    chart_rain_response(df)
    chart_dry_baseline(df)
    chart_lm5_by_year(df)
    print("charts ->", OUT)


if __name__ == "__main__":
    main()
