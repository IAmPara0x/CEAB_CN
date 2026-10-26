"""Summaries, result tables and figures from results/raw_runs.csv."""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

import matplotlib
import matplotlib.ticker
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .strategies import REGISTRY, ALL

# ---------------------------------------------------------------- styling
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
HIGHLIGHT = {"ceab": "#2a78d6", "beb": "#eb6834", "idlesense": "#1baf7a", "eied": "#eda100"}
MUTED = {"mild": ("#8f8d86", "--", "v"), "fibonacci": ("#8f8d86", ":", "s"),
         "linear": ("#b3b1aa", "-.", "^"), "quadratic": ("#b3b1aa", "--", "D"),
         "constant": ("#6f6d67", ":", "x")}
MARK = {"ceab": "o", "beb": "s", "idlesense": "^", "eied": "D"}
LOWER_IS_BETTER = {"collision_prob", "access_delay_mean", "access_delay_p99", "access_delay_std",
                   "e2e_delay_mean", "drop_rate"}
NICE = {"throughput": "Throughput (Mb/s)", "collision_prob": "Collision probability",
        "access_delay_mean": "Mean access delay (ms)", "access_delay_p99": "99th-pct access delay (ms)",
        "access_delay_std": "Access-delay jitter, SD (ms)", "e2e_delay_mean": "Mean end-to-end delay (ms)",
        "jain_short": "Short-term Jain fairness (100 ms)", "jain_long": "Long-term Jain fairness",
        "drop_rate": "Frame drop rate"}


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": INK,
        "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2,
        "lines.markersize": 6, "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
    })


def line_style(st):
    if st in HIGHLIGHT:
        return dict(color=HIGHLIGHT[st], marker=MARK[st], linestyle="-", zorder=3,
                    linewidth=2.4 if st == "ceab" else 2)
    c, ls, mk = MUTED[st]
    return dict(color=c, linestyle=ls, marker=mk, linewidth=1.4, markersize=5, zorder=2)


def label(st):
    return REGISTRY[st].label


# ---------------------------------------------------------------- loading / summary
def load(results_dir):
    rows = []
    with open(os.path.join(results_dir, "raw_runs.csv")) as f:
        for r in csv.DictReader(f):
            for k in list(r):
                if k in ("scenario", "param", "strategy", "share"):
                    continue
                r[k] = float(r[k]) if r[k] not in ("", "nan") else np.nan
            rows.append(r)
    return rows


def group(rows, scenario):
    g = defaultdict(list)
    for r in rows:
        if r["scenario"] == scenario:
            g[(r["param"], r["strategy"])].append(r)
    return g


def ms(vals):
    v = np.asarray(vals, dtype=float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        return np.nan, np.nan
    return float(v.mean()), float(v.std(ddof=1)) if v.size > 1 else 0.0


def summary_csv(rows, path):
    keys = sorted({(r["scenario"], r["param"], r["strategy"]) for r in rows},
                  key=lambda k: (k[0], _num(k[1]), k[2]))
    from .experiments import METRICS
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "param", "strategy", "runs"] +
                   [f"{m}_{s}" for m in METRICS for s in ("mean", "sd")])
        for sc, p, st in keys:
            sel = [r for r in rows if r["scenario"] == sc and r["param"] == p and r["strategy"] == st]
            vals = []
            for m in METRICS:
                vals += list(ms([r[m] for r in sel]))
            w.writerow([sc, p, st, len(sel)] + [f"{v:.6g}" for v in vals])


def _num(x):
    try:
        return float(x)
    except ValueError:
        return float("inf")


def fmt(m, s, metric):
    if metric == "drop_rate":
        return f"{m * 100:.3f}% ± {s * 100:.3f}%"
    if metric in ("collision_prob", "jain_short", "jain_long"):
        return f"{m:.3f} ± {s:.3f}"
    return f"{m:.2f} ± {s:.2f}"


def improvement(base, prop, metric):
    if base == 0 or np.isnan(base):
        return np.nan
    return (base - prop) / base * 100 if metric in LOWER_IS_BETTER else (prop - base) / base * 100


def main_table(rows, base="beb", prop="ceab"):
    """Rubric results table: scenario x metric, baseline vs proposed, mean ± SD, improvement %."""
    out = []
    metrics = ["throughput", "collision_prob", "access_delay_mean", "access_delay_p99",
               "jain_short", "drop_rate"]
    names = {"S1": "S1 (low load, N=5)", "S2": "S2 (medium load, N=20)", "S3": "S3 (high load, N=50)"}
    for sc in ["S1", "S2", "S3"]:
        g = group(rows, sc)
        p = next(iter(g))[0]
        for m in metrics:
            b = [r[m] for r in g[(p, base)]]
            q = [r[m] for r in g[(p, prop)]]
            bm, bs = ms(b)
            qm, qs = ms(q)
            t = stats.ttest_ind(b, q, equal_var=False) if np.std(b) + np.std(q) > 0 else None
            out.append({"scenario": names[sc], "metric": NICE[m], "baseline": fmt(bm, bs, m),
                        "proposed": fmt(qm, qs, m), "improvement": improvement(bm, qm, m),
                        "p_value": float(t.pvalue) if t is not None else np.nan,
                        "key": m, "sc": sc})
    return out


def all_strategy_table(rows, metric):
    tab = {}
    for sc in ["S1", "S2", "S3"]:
        g = group(rows, sc)
        for (p, st), rs in g.items():
            tab[(sc, st)] = ms([r[metric] for r in rs])
    return tab


def write_markdown(rows, path):
    t = main_table(rows)
    lines = ["# Results (mean ± SD over repeated runs)", "",
             "## Baseline (BEB) vs proposed (CEAB)", "",
             "| Scenario | Metric | Baseline (mean ± SD) | Proposed (mean ± SD) | Improvement (%) | Welch p |",
             "|---|---|---|---|---|---|"]
    for r in t:
        lines.append(f"| {r['scenario']} | {r['metric']} | {r['baseline']} | {r['proposed']} | "
                     f"{r['improvement']:+.1f} | {r['p_value']:.1e} |")
    for metric in ["throughput", "collision_prob", "access_delay_p99", "jain_short"]:
        tab = all_strategy_table(rows, metric)
        lines += ["", f"## All strategies — {NICE[metric]}", "",
                  "| Strategy | S1 (N=5) | S2 (N=20) | S3 (N=50) |", "|---|---|---|---|"]
        for st in ALL:
            cells = [fmt(*tab[(sc, st)], metric) for sc in ["S1", "S2", "S3"]]
            lines.append(f"| {label(st)} | " + " | ".join(cells) + " |")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- figures
def _sweep(ax, rows, scenario, metric, strategies, xlabel, logy=False, band=True):
    g = group(rows, scenario)
    params = sorted({p for p, _ in g}, key=_num)
    xs = np.array([_num(p) for p in params])
    for st in strategies:
        m = np.array([ms([r[metric] for r in g.get((p, st), [])])[0] for p in params])
        s = np.array([ms([r[metric] for r in g.get((p, st), [])])[1] for p in params])
        kw = line_style(st)
        ax.plot(xs, m, label=label(st), **kw)
        if band and st in HIGHLIGHT:
            ax.fill_between(xs, m - s, m + s, color=kw["color"], alpha=0.15, linewidth=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(NICE[metric])
    if logy:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))


def make_figures(rows, results_dir, figdir):
    style()
    os.makedirs(figdir, exist_ok=True)
    figs = {}

    def save(fig, name, caption):
        p = os.path.join(figdir, name)
        fig.savefig(p)
        plt.close(fig)
        figs[name] = caption

    # 1. validation against Bianchi
    ana = list(csv.DictReader(open(os.path.join(results_dir, "analytical.csv"))))
    g = group(rows, "validation")
    params = sorted({p for p, _ in g}, key=_num)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    for ax, key, akey, ylab in [(axes[0], "throughput", "bianchi_thr", NICE["throughput"]),
                                (axes[1], "collision_prob", "bianchi_p", NICE["collision_prob"])]:
        ax.plot([float(a["n"]) for a in ana], [float(a[akey]) for a in ana], color=INK2,
                linestyle="--", linewidth=1.6, label="Bianchi analytical model")
        m = [ms([r[key] for r in g[(p, "beb")]]) for p in params]
        ax.errorbar([_num(p) for p in params], [a for a, _ in m], yerr=[b for _, b in m],
                    color=HIGHLIGHT["beb"], marker="s", linestyle="none", capsize=3,
                    label="Simulator (BEB, mean ± SD)")
        ax.set_xlabel("Number of stations N")
        ax.set_ylabel(ylab)
    axes[0].set_title("Saturation throughput")
    axes[1].set_title("Conditional collision probability")
    axes[0].legend(loc="lower left")
    save(fig, "fig_validation.png", "Simulator validation: BEB saturation throughput and collision "
         "probability versus the Bianchi (2000) analytical model.")

    # 2-5. N sweeps
    for metric, name, logy, title in [
        ("throughput", "fig_throughput_vs_n.png", False, "Saturation throughput vs number of stations"),
        ("collision_prob", "fig_collision_vs_n.png", False, "Collision probability vs number of stations"),
        ("access_delay_p99", "fig_p99_vs_n.png", True, "Tail (99th percentile) access delay"),
        ("jain_short", "fig_fairness_vs_n.png", False, "Short-term fairness (Jain index, 100 ms windows)"),
    ]:
        fig, ax = plt.subplots(figsize=(7.5, 4.3))
        if metric == "throughput":
            ax.plot([float(a["n"]) for a in ana], [float(a["optimal_thr"]) for a in ana], color=INK,
                    linestyle=(0, (1, 2)), linewidth=1.2, label="Analytical optimum (ideal W)")
        _sweep(ax, rows, "sweep_n", metric, ALL, "Number of stations N", logy=logy)
        ax.set_title(title)
        ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5))
        save(fig, name, title + " for all nine backoff strategies (saturated traffic, mean over runs; "
             "shaded band = ±1 SD for highlighted schemes).")

    # 6. S1-S3 grouped bars, throughput and p99
    for metric, name in [("throughput", "fig_s123_throughput.png"),
                         ("access_delay_p99", "fig_s123_p99.png")]:
        tab = all_strategy_table(rows, metric)
        fig, ax = plt.subplots(figsize=(9.5, 4))
        w = 0.8 / len(ALL)
        for i, st in enumerate(ALL):
            ys = [tab[(sc, st)][0] for sc in ["S1", "S2", "S3"]]
            es = [tab[(sc, st)][1] for sc in ["S1", "S2", "S3"]]
            col = HIGHLIGHT.get(st, MUTED.get(st, ("#999",))[0])
            ax.bar(np.arange(3) + (i - len(ALL) / 2 + 0.5) * w, ys, w * 0.92, yerr=es, color=col,
                   label=label(st), capsize=2, error_kw={"elinewidth": 0.8, "ecolor": INK2},
                   hatch=None if st in HIGHLIGHT else "///", edgecolor=SURFACE, linewidth=0.5)
        ax.set_xticks(range(3), ["S1  low (N=5)", "S2  medium (N=20)", "S3  high (N=50)"])
        ax.set_ylabel(NICE[metric])
        ax.grid(axis="x", visible=False)
        ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
        ax.set_title(NICE[metric] + " by scenario")
        save(fig, name, NICE[metric] + " for every strategy in scenarios S1–S3 (bars = mean, "
             "whiskers = ±1 SD over runs).")

    # 7. offered-load sweep
    from .experiments import MAIN
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    _sweep(axes[0], rows, "load", "throughput", MAIN, "Offered load (Mb/s), N = 30")
    axes[0].plot([0, 40], [0, 40], color=GRID, linewidth=1, zorder=1)
    axes[0].set_title("Carried vs offered load")
    _sweep(axes[1], rows, "load", "e2e_delay_mean", MAIN, "Offered load (Mb/s), N = 30", logy=True)
    axes[1].set_title("Mean end-to-end delay")
    axes[0].legend(loc="upper left")
    save(fig, "fig_load.png", "Unsaturated (Poisson) traffic with 30 stations: carried throughput and "
         "end-to-end delay as the offered load grows past saturation.")

    # 8. churn
    z = np.load(os.path.join(results_dir, "churn_series.npz"))
    fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 1.4, 1.4]})
    t = z["beb/t"][0]
    for st in MAIN:
        y = np.nanmean(z[f"{st}/throughput"], axis=0)
        k = 4
        y = np.convolve(np.nan_to_num(y), np.ones(k) / k, mode="same")
        y[(t < 0.6) | (t > t[-1] - 0.15)] = np.nan
        axes[0].plot(t, y, label=label(st), color=HIGHLIGHT[st], linewidth=2.2 if st == "ceab" else 1.6)
    axes[0].set_ylabel("Throughput (Mb/s)")
    axes[0].set_title("Dynamic membership: 5 → 50 stations at t = 4 s, 50 → 15 at t = 8 s")
    axes[0].legend(ncol=4, loc="lower left")
    act = z["ceab/active"][0]
    axes[1].plot(t, act, color=INK2, linestyle="--", linewidth=1.4, label="True active stations")
    axes[1].plot(t, np.nanmean(z["ceab/n_hat"], axis=0), color=HIGHLIGHT["ceab"],
                 label="CEAB estimate n_c (mean over stations)")
    axes[1].set_ylabel("Stations")
    axes[1].legend(loc="upper left")
    for st in MAIN:
        axes[2].plot(t, np.nanmean(z[f"{st}/mean_W"], axis=0), color=HIGHLIGHT[st], label=label(st),
                     linewidth=2 if st == "ceab" else 1.4)
    axes[2].set_yscale("log")
    axes[2].yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    axes[2].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axes[2].set_yticks([16, 32, 64, 128, 256, 512, 1024])
    axes[2].set_ylabel("Mean window W (slots)")
    axes[2].set_xlabel("Time (s)")
    for ax in axes:
        for tc in (4, 8):
            ax.axvline(tc, color=GRID, linewidth=1.2, zorder=1)
    save(fig, "fig_churn.png", "Churn scenario: throughput over time (top), CEAB's contender estimate "
         "against the true number of active stations (middle) and the mean contention window (bottom).")

    # 9. FER, payload, RTS/CTS
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    _sweep(axes[0], rows, "fer", "throughput", MAIN, "Frame error rate (N = 20)")
    axes[0].set_title("Non-collision losses")
    _sweep(axes[1], rows, "payload", "throughput", MAIN, "Payload size (bytes, N = 20)")
    axes[1].set_title("Payload size")
    axes[0].legend(loc="lower left")
    save(fig, "fig_fer_payload.png", "Sensitivity of throughput to channel frame errors (left) and to "
         "payload size (right), 20 saturated stations.")

    g = group(rows, "rts")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    for i, st in enumerate(MAIN):
        mm = [ms([r["throughput"] for r in g[(str(n), st)]]) for n in (5, 20, 50)]
        ax.errorbar(np.arange(3) + (i - 1.5) * 0.12, [a for a, _ in mm], yerr=[b for _, b in mm],
                    color=HIGHLIGHT[st], marker=MARK[st], markersize=8, linestyle="none", capsize=3,
                    label=label(st))
    ax.set_xticks(range(3), ["N = 5", "N = 20", "N = 50"])
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylabel(NICE["throughput"])
    ax.set_title("RTS/CTS access mode (dot plot, axis zoomed)")
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    save(fig, "fig_rts.png", "Throughput with the RTS/CTS handshake, where a collision costs only an "
         "RTS frame (mean ± SD; note the zoomed y-axis).")

    # 10. coexistence
    g = group(rows, "coexist")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    cats = ["beb", "eied", "idlesense", "ceab"]
    legacy, new = [], []
    for st in cats:
        rs = next(v for (p, _), v in g.items() if p == st)
        sh = [json.loads(r["share"]) for r in rs]
        if st == "beb":
            tot = [s["beb"] for s in sh]
            legacy.append(ms([x / 2 for x in tot]))
            new.append(ms([x / 2 for x in tot]))
        else:
            legacy.append(ms([s["beb"] for s in sh]))
            new.append(ms([s[st] for s in sh]))
    x = np.arange(len(cats))
    ax.bar(x - 0.2, [a for a, _ in legacy], 0.38, yerr=[b for _, b in legacy], color=HIGHLIGHT["beb"],
           label="10 legacy BEB stations", capsize=2, edgecolor=SURFACE)
    ax.bar(x + 0.2, [a for a, _ in new], 0.38, yerr=[b for _, b in new], color=HIGHLIGHT["ceab"],
           label="10 stations running the new scheme", capsize=2, edgecolor=SURFACE)
    ax.set_xticks(x, ["BEB (all legacy)", "EIED", "Idle Sense", "CEAB"])
    ax.set_ylabel("Aggregate throughput of group (Mb/s)")
    ax.set_title("Coexistence with legacy 802.11 stations")
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    save(fig, "fig_coexist.png", "Coexistence: throughput obtained by 10 legacy BEB stations and by 10 "
         "stations running each scheme on the same channel.")

    # 11. ablation
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, sc, pname in [(axes[0], "ablation_K", "Escalation cap K"),
                          (axes[1], "ablation_M", "Estimation window M (frames)")]:
        g = group(rows, sc)
        for n, col in [("20", "#86b6ef"), ("50", HIGHLIGHT["ceab"])]:
            ps = sorted({p for p, _ in g if p.startswith(n + ":")}, key=lambda p: float(p.split(":")[1]))
            xs = [float(p.split(":")[1]) for p in ps]
            m = [ms([r["access_delay_p99"] for r in g[(p, "ceab")]]) for p in ps]
            ax.errorbar(xs, [a for a, _ in m], yerr=[b for _, b in m], color=col, marker="o",
                        capsize=3, label=f"N = {n}")
        ax.set_xlabel(pname)
        ax.set_ylabel(NICE["access_delay_p99"])
        if sc == "ablation_M":
            ax.set_xscale("log")
    axes[0].set_title("Effect of per-retry escalation")
    axes[1].set_title("Effect of estimation window")
    axes[0].legend()
    save(fig, "fig_ablation.png", "Ablation of CEAB's design parameters: tail delay versus the "
         "escalation cap K and the estimation window M.")

    with open(os.path.join(figdir, "captions.json"), "w") as f:
        json.dump(figs, f, indent=1)
    return figs
