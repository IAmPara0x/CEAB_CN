"""Draws the architecture, topology and flowchart figures used in the report."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
INK, INK2, LINE = "#0b0b0b", "#52514e", "#8f8d86"
BLUE, BLUE_L, ORANGE_L, GREY_L, AQUA_L = "#2a78d6", "#cde2fb", "#fbe0d4", "#f0efec", "#d3f0e5"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "savefig.dpi": 220,
                     "savefig.bbox": "tight", "figure.facecolor": "white"})


def box(ax, x, y, w, h, text, fc=GREY_L, ec=LINE, bold=False, fs=8.8, shape="round"):
    if shape == "diamond":
        ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y + h), (x + w, y + h / 2), (x + w / 2, y)],
                             closed=True, fc=fc, ec=ec, lw=1.2))
    else:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p, q, text=None, off=(0.05, 0), color=INK2, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11, color=color, lw=1.2,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, fontsize=8.5, color=INK2)


def path(ax, pts, color=INK2):
    """Orthogonal connector through the given points, arrow head on the last segment."""
    xs, ys = zip(*pts)
    ax.plot(xs[:-1], ys[:-1], color=color, lw=1.2, solid_capstyle="round")
    arrow(ax, pts[-2], pts[-1], color=color)


def architecture():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.8)
    ax.axis("off")
    box(ax, 0.2, 4.7, 3.0, 0.8, "run_experiments.py / demo.py\n(scenarios, seeds, CLI, GUI)", fc=AQUA_L, bold=True)
    box(ax, 6.9, 4.7, 2.9, 0.8, "analysis.py\n(mean ± SD, Welch t-test,\ntables, figures)", fc=AQUA_L, bold=True)
    ax.add_patch(FancyBboxPatch((0.2, 0.3), 4.3, 3.9, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc="white", ec=LINE, lw=1, ls="--"))
    ax.text(0.35, 3.95, "Station i  (×N)", fontsize=10, fontweight="bold", color=INK)
    box(ax, 0.4, 2.9, 1.85, 0.8, "Traffic source\nsaturated / Poisson λ", fs=9)
    box(ax, 2.45, 2.9, 1.85, 0.8, "FIFO queue\n(cap 100 frames)", fs=9)
    box(ax, 0.4, 1.55, 3.9, 0.95, "DCF MAC: backoff counter,\nfreeze on busy, retry limit 7", fc=ORANGE_L)
    box(ax, 0.4, 0.45, 3.9, 0.85, "Backoff strategy plug-in   W = f(history)\nBEB · Linear · Fibonacci · Quadratic · MILD\n"
        "EIED · Constant · Idle Sense · CEAB", fc=BLUE_L, fs=8.4)
    arrow(ax, (2.25, 3.3), (2.45, 3.3))
    arrow(ax, (3.4, 2.9), (3.4, 2.5))
    arrow(ax, (2.35, 1.55), (2.35, 1.3))
    box(ax, 6.0, 1.4, 3.8, 2.6, "", fc=GREY_L)
    ax.text(7.9, 3.7, "Shared channel engine\n(simulator.py)", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(7.9, 2.4, "• jump to next min(backoff) slot\n• 1 transmitter → success, busy Ts\n"
            "• ≥2 transmitters → collision, Tc\n• frame error with prob. FER\n"
            "• tell every station the idle gap\n   and TA of the decoded frame", ha="center", va="center", fontsize=8.8)
    box(ax, 6.0, 0.3, 3.8, 0.8, "PHY timing (phy.py): 802.11g OFDM\n54 Mb/s, slot 9 µs, SIFS 10, DIFS 28 µs", fs=9)
    arrow(ax, (4.3, 2.3), (6.0, 2.3))
    ax.text(5.15, 2.42, "attempt", ha="center", fontsize=8.5, color=INK2)
    arrow(ax, (6.0, 1.75), (4.3, 1.75))
    ax.text(5.15, 1.3, "outcome, idle gap,\nTA overheard", ha="center", fontsize=8.5, color=INK2)
    arrow(ax, (7.9, 1.1), (7.9, 1.4))
    arrow(ax, (1.7, 4.7), (1.7, 4.2))
    ax.text(1.8, 4.4, "SimConfig", fontsize=8.5, color=INK2)
    arrow(ax, (8.35, 4.0), (8.35, 4.7))
    ax.text(8.45, 4.3, "metrics, time series", fontsize=8.5, color=INK2)
    fig.savefig(os.path.join(OUT, "fig_architecture.png"))
    plt.close(fig)


def topology():
    fig, ax = plt.subplots(figsize=(6, 4.4))
    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-2.6, 2.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((0, 0), 2.25, fc="#f6f9fe", ec=BLUE, lw=1.2, ls="--"))
    ax.text(0, 2.05, "single collision domain (every station hears every frame)", ha="center",
            fontsize=8.5, color=BLUE)
    import numpy as np
    n = 12
    for k in range(n):
        a = 2 * np.pi * k / n + 0.2
        x, y = 1.65 * np.cos(a), 1.65 * np.sin(a)
        ax.plot([0, x], [0, y], color="#cfcdc6", lw=1, zorder=1)
        ax.add_patch(Circle((x, y), 0.2, fc=ORANGE_L if k % 3 else BLUE_L, ec=LINE, zorder=2))
        ax.text(x, y, f"S{k + 1 if k < n - 1 else 'N'}", ha="center", va="center", fontsize=7.5, zorder=3)
    ax.add_patch(Circle((0, 0), 0.33, fc=AQUA_L, ec=LINE, zorder=2))
    ax.text(0, 0, "AP", ha="center", va="center", fontweight="bold", zorder=3)
    ax.text(0, -2.5, "Uplink traffic S1…SN → AP, N ∈ {2…100}, 802.11g basic access or RTS/CTS",
            ha="center", fontsize=8.5, color=INK2)
    fig.savefig(os.path.join(OUT, "fig_topology.png"))
    plt.close(fig)


def flowchart():
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 8.4), gridspec_kw={"width_ratios": [1, 1.2]})
    axes[0].set_xlim(-0.45, 6.85)
    axes[1].set_xlim(-1.15, 6.1)
    for ax in axes:
        ax.set_ylim(0, 11)
        ax.axis("off")
    # --- baseline BEB
    ax = axes[0]
    ax.text(3, 10.7, "Baseline: 802.11 BEB", ha="center", fontsize=11, fontweight="bold", color=INK)
    box(ax, 1.4, 9.6, 3.2, 0.7, "Frame at head of queue\nW ← CWmin+1, retry ← 0", fc=ORANGE_L)
    box(ax, 1.4, 8.4, 3.2, 0.7, "draw backoff b ~ U[0, W−1]")
    box(ax, 1.4, 7.2, 3.2, 0.7, "count down idle slots\n(freeze while busy)")
    box(ax, 1.4, 6.0, 3.2, 0.7, "transmit when b = 0")
    box(ax, 1.75, 4.5, 2.5, 1.0, "ACK\nreceived?", shape="diamond")
    box(ax, 0.0, 2.9, 2.6, 0.8, "success:\nW ← CWmin+1", fc=ORANGE_L)
    box(ax, 3.4, 2.9, 3.0, 0.8, "retry++\nW ← min(2W, CWmax+1)", fc=ORANGE_L)
    box(ax, 3.4, 1.4, 3.0, 0.8, "retry > 7 ?  drop frame,\nW ← CWmin+1")
    for y0, y1 in [(9.6, 9.1), (8.4, 7.9), (7.2, 6.7), (6.0, 5.5)]:
        arrow(ax, (3, y0), (3, y1))
    arrow(ax, (1.75, 5.0), (1.3, 3.7))
    ax.text(1.15, 4.4, "yes", fontsize=8.5, color=INK2)
    arrow(ax, (4.25, 5.0), (4.9, 3.7))
    ax.text(4.75, 4.4, "no", fontsize=8.5, color=INK2)
    arrow(ax, (4.9, 2.9), (4.9, 2.2))
    path(ax, [(6.4, 3.3), (6.65, 3.3), (6.65, 8.75), (4.6, 8.75)])
    ax.text(6.55, 6.6, "retry ≤ 7", fontsize=8.5, color=INK2, ha="right")
    path(ax, [(0.0, 3.3), (-0.3, 3.3), (-0.3, 9.95), (1.4, 9.95)])
    ax.text(-0.2, 6.6, "next\nframe", fontsize=8.5, color=INK2)
    ax.text(3.1, 0.5, "Problem: W resets to CWmin after every success, so with\nmany stations every new "
            "frame starts in a window that\nis far too small → repeated collisions.", ha="center",
            fontsize=8.6, color=INK2)
    # --- CEAB
    ax = axes[1]
    ax.text(2.6, 10.7, "Proposed: CEAB", ha="center", fontsize=11, fontweight="bold", color=BLUE)
    ax.text(4.55, 10.25, "channel estimation (every busy period)", ha="center", fontsize=8.5, color=BLUE)
    box(ax, 3.2, 9.0, 2.8, 1.0, "log TA of decoded frame;\nn_eff = M(M−1) / Σ c_j(c_j−1)\n(last M = 200 frames)", fc=BLUE_L, fs=8.4)
    box(ax, 3.2, 7.7, 2.8, 0.85, "EWMA idle gap I_obs\nρ = min(1, I* / I_obs)", fc=BLUE_L, fs=8.4)
    box(ax, 3.2, 6.4, 2.8, 0.85, "n_c = max(1, ρ · n_eff)\nW* = 2 / τ*(n_c) − 1", fc=BLUE_L, fs=8.4)
    box(ax, 3.2, 5.1, 2.8, 0.85, "W_base ← W_base\n+ γ (W* − W_base),  γ = 0.5", fc=BLUE_L, fs=8.4)
    ax.text(2.6 - 2.3, 10.25, "transmission (per frame)", ha="center", fontsize=8.5, color=INK2)
    box(ax, -0.6, 9.1, 2.9, 0.8, "Frame at head of queue\nretry ← 0")
    box(ax, -0.6, 7.75, 2.9, 0.8, "draw b ~ U[0, W−1],\ncount down, transmit")
    box(ax, -0.4, 5.6, 2.5, 1.1, "ACK\nreceived?", shape="diamond")
    box(ax, -0.6, 3.6, 2.9, 0.9, "success:\nW ← W_base\n(never back to CWmin)", fc=BLUE_L, fs=8.4)
    box(ax, 3.2, 3.6, 2.8, 0.9, "failure: retry++\nW ← W_base · 2^min(retry, K)\n(K = 0 by default)", fc=BLUE_L, fs=8.4)
    box(ax, 3.2, 2.3, 2.8, 0.8, "retry ≤ 7: back-off again\nretry > 7: drop, W ← W_base", fs=8.4)
    for y0, y1 in [(9.0, 8.55), (7.7, 7.25), (6.4, 5.95)]:
        arrow(ax, (4.6, y0), (4.6, y1))
    arrow(ax, (0.85, 9.1), (0.85, 8.55))
    arrow(ax, (0.85, 7.75), (0.85, 6.7))
    arrow(ax, (0.85, 5.6), (0.85, 4.5))
    ax.text(0.95, 5.0, "yes", fontsize=8.5, color=INK2)
    arrow(ax, (2.1, 6.15), (3.5, 4.5))
    ax.text(2.75, 5.45, "no", fontsize=8.5, color=INK2)
    arrow(ax, (4.6, 3.6), (4.6, 3.1))
    arrow(ax, (3.2, 5.5), (2.3, 4.3), color=BLUE)
    ax.text(2.35, 4.75, "W_base", fontsize=8.5, color=BLUE)
    path(ax, [(-0.6, 4.05), (-1.0, 4.05), (-1.0, 9.5), (-0.6, 9.5)])
    ax.text(-0.95, 9.62, "next frame", fontsize=8.5, color=INK2)
    path(ax, [(3.2, 2.7), (-0.75, 2.7), (-0.75, 8.15), (-0.6, 8.15)])
    ax.text(1.2, 2.82, "retry ≤ 7", fontsize=8.5, color=INK2)
    ax.text(2.6, 0.9, "Every station derives the same n_eff from overheard frames, so all windows\n"
            "converge to one throughput-optimal value (fairness) whatever backoff rule\n"
            "the other stations run. W_base is refreshed after each own outcome.", ha="center",
            fontsize=8.6, color=INK2)
    fig.savefig(os.path.join(OUT, "fig_flowchart.png"))
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    architecture()
    topology()
    flowchart()
    print("diagrams written to", os.path.abspath(OUT))
