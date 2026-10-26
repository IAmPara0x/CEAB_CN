#!/usr/bin/env python3
"""Live demo: baseline (BEB) vs proposed (CEAB) -- or any other strategies -- with any parameters.

Examples
  python demo.py compare                                   # BEB vs CEAB, 50 stations
  python demo.py compare -n 20 --strategies beb eied idlesense ceab --runs 5
  python demo.py compare -n 30 --load 25                   # unsaturated, 25 Mb/s offered
  python demo.py compare -n 20 --fer 0.1 --rts             # lossy channel, RTS/CTS access
  python demo.py compare --churn 3:50 6:10 -n 50 --start 5 --plot
  python demo.py gui                                       # sliders + buttons, re-run on click
  python demo.py trace -n 5 --strategies beb ceab --events 25   # per-frame channel log
  python demo.py list                                      # available strategies
"""
import argparse
import sys
import time
import warnings

import numpy as np

from csmasim import REGISTRY, simulate

ROWS = [("throughput", "Throughput (Mb/s)", "{:.2f}", True),
        ("collision_prob", "Collision probability", "{:.3f}", False),
        ("access_delay_mean", "Mean access delay (ms)", "{:.2f}", False),
        ("access_delay_p99", "p99 access delay (ms)", "{:.2f}", False),
        ("e2e_delay_mean", "Mean end-to-end delay (ms)", "{:.2f}", False),
        ("jain_short", "Short-term Jain fairness", "{:.3f}", True),
        ("drop_rate", "Drop rate", "{:.4f}", False)]


def _smooth(series):
    """3-bin moving average of the throughput series, warm-up bins (NaN) removed."""
    ok = ~np.isnan(series["throughput"])
    t, y = series["t"][ok], series["throughput"][ok]
    if y.size >= 3:
        y = np.convolve(y, np.ones(3) / 3, mode="valid")
        t = t[1:-1]
    return t, y


def build_kwargs(a, strategy, seed):
    kw = dict(n=a.nodes, strategy=strategy, duration=a.duration, warmup=min(1.0, a.duration / 5),
              seed=seed, fer=a.fer, rts_cts=a.rts, payload=a.payload, cw_min=a.cwmin,
              cw_max=a.cwmax, retry_limit=a.retry)
    if a.load:
        kw["arrival_rate"] = a.load * 1e6 / (a.nodes * a.payload * 8)
    if a.churn:
        kw["churn"] = [(float(t), int(k)) for t, k in (c.split(":") for c in a.churn)]
        kw["initial_active"] = a.start or a.nodes
        kw["warmup"] = 0.3
    if a.ceab_k is not None or a.ceab_m is not None:
        ck = {}
        if a.ceab_k is not None:
            ck["K"] = a.ceab_k
        if a.ceab_m is not None:
            ck["M"] = a.ceab_m
        kw["strategy_kwargs"] = {"ceab": ck}
    return kw


def run_compare(a):
    print(f"\n  N={a.nodes}  traffic={'%g Mb/s offered' % a.load if a.load else 'saturated'}  "
          f"FER={a.fer}  access={'RTS/CTS' if a.rts else 'basic'}  payload={a.payload} B  "
          f"duration={a.duration}s x {a.runs} run(s)" + (f"  churn={a.churn}" if a.churn else ""))
    res, series = {}, {}
    for st in a.strategies:
        t0 = time.time()
        rs = [simulate(**build_kwargs(a, st, seed)) for seed in range(1, a.runs + 1)]
        res[st] = {k: np.array([r.metrics[k] for r in rs], dtype=float) for k, *_ in ROWS}
        series[st] = rs[0].series
        print(f"  ran {REGISTRY[st].label:<18} in {time.time() - t0:.1f}s")
    w = 22
    head = f"\n  {'Metric':<28}" + "".join(f"{REGISTRY[s].label:>{w}}" for s in a.strategies)
    base = a.strategies[0]
    if len(a.strategies) > 1:
        head += f"{'Δ last vs first':>{w}}"
    print(head)
    print("  " + "-" * (len(head) - 3))
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    for key, name, f, higher in ROWS:
        if a.churn and key == "jain_short":
            continue          # fairness over a changing station set is not meaningful
        line = f"  {name:<28}"
        for st in a.strategies:
            v = res[st][key]
            if np.all(np.isnan(v)):
                cell = "n/a"
            elif a.runs > 1:
                cell = f.format(np.nanmean(v)) + " ± " + f.format(np.nanstd(v, ddof=1))
            else:
                cell = f.format(np.nanmean(v))
            line += f"{cell:>{w}}"
        if len(a.strategies) > 1:
            b, p = np.nanmean(res[base][key]), np.nanmean(res[a.strategies[-1]][key])
            if b and not np.isnan(b) and not np.isnan(p):
                imp = (p - b) / b * 100 if higher else (b - p) / b * 100
                line += f"{imp:>+{w - 1}.1f}%"
        print(line)
    print("  (Δ is the improvement of the last strategy over the first; positive = better)\n")
    if a.plot:
        plot(a, res, series)


def run_trace(a):
    """Print the first channel events like a packet capture: who transmitted, with which window."""
    for st in a.strategies:
        kw = build_kwargs(a, st, 1)
        kw.update(duration=max(0.05, a.events * 0.002), warmup=0.0, trace_limit=a.events)
        tr = simulate(**kw).series["trace"]
        print(f"\n  {REGISTRY[st].label}: first {len(tr)} busy periods, N={a.nodes}")
        print(f"  {'#':>3} {'time (us)':>10} {'idle':>5}  {'outcome':<11} {'stations':<14} "
              f"{'W used':<14} {'retry':<10} {'busy (us)':>9}")
        for k, e in enumerate(tr, 1):
            print(f"  {k:>3} {e['t_us']:>10.0f} {e['idle_slots']:>5}  {e['outcome']:<11} "
                  f"{','.join(f'S{i + 1}' for i in e['tx']):<14} {','.join(map(str, e['W'])):<14} "
                  f"{','.join(map(str, e['retry'])):<10} {e['busy_us']:>9.0f}")
    print()


def plot(a, res, series):
    import matplotlib.pyplot as plt

    from csmasim.analysis import HIGHLIGHT, style
    style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [2, 1]})
    for st in a.strategies:
        s = series[st]
        t, y = _smooth(s)
        axes[0].plot(t, y, label=REGISTRY[st].label,
                     color=HIGHLIGHT.get(st, "#8f8d86"), linewidth=2)
    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel("Throughput (Mb/s)")
    axes[0].set_title("Throughput over time (run 1)")
    axes[0].legend()
    x = np.arange(len(a.strategies))
    axes[1].bar(x, [np.nanmean(res[s]["access_delay_p99"]) for s in a.strategies],
                color=[HIGHLIGHT.get(s, "#8f8d86") for s in a.strategies])
    axes[1].set_xticks(x, [REGISTRY[s].label for s in a.strategies], rotation=20)
    axes[1].set_title("p99 access delay (ms)")
    plt.tight_layout()
    plt.show()


def run_gui(a):
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button, CheckButtons, RadioButtons, Slider
    from csmasim.analysis import HIGHLIGHT, style
    style()
    fig = plt.figure(figsize=(13, 7.5))
    fig.canvas.manager.set_window_title("CSMA/CA backoff strategies — live demo")
    ax_t = fig.add_axes([0.06, 0.55, 0.6, 0.38])
    ax_b = fig.add_axes([0.06, 0.08, 0.28, 0.36])
    ax_d = fig.add_axes([0.40, 0.08, 0.26, 0.36])
    s_n = Slider(fig.add_axes([0.76, 0.88, 0.17, 0.03]), "Stations N", 2, 100, valinit=a.nodes, valstep=1)
    s_load = Slider(fig.add_axes([0.76, 0.83, 0.17, 0.03]), "Load Mb/s (0=sat)", 0, 40, valinit=a.load or 0, valstep=1)
    s_fer = Slider(fig.add_axes([0.76, 0.78, 0.17, 0.03]), "Frame error rate", 0, 0.3, valinit=a.fer, valstep=0.01)
    s_pl = Slider(fig.add_axes([0.76, 0.73, 0.17, 0.03]), "Payload (B)", 100, 2304, valinit=a.payload, valstep=50)
    s_dur = Slider(fig.add_axes([0.76, 0.68, 0.17, 0.03]), "Duration (s)", 1, 10, valinit=a.duration, valstep=0.5)
    names = list(REGISTRY)
    chk = CheckButtons(fig.add_axes([0.73, 0.24, 0.2, 0.38]), [REGISTRY[s].label for s in names],
                       [s in a.strategies for s in names])
    acc = RadioButtons(fig.add_axes([0.73, 0.13, 0.2, 0.09]), ["basic access", "RTS/CTS"])
    btn = Button(fig.add_axes([0.73, 0.04, 0.2, 0.06]), "Run simulation", color="#cde2fb", hovercolor="#9ec5f4")
    status = fig.text(0.06, 0.965, "Press 'Run simulation'", fontsize=10, color="#52514e")

    def run(_=None):
        chosen = [s for s, on in zip(names, chk.get_status()) if on]
        if not chosen:
            return
        a.nodes, a.fer, a.payload = int(s_n.val), float(s_fer.val), int(s_pl.val)
        a.load, a.duration, a.rts = float(s_load.val) or None, float(s_dur.val), acc.value_selected == "RTS/CTS"
        a.churn = None
        status.set_text("running ...")
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        res = {}
        for st in chosen:
            r = simulate(**build_kwargs(a, st, 1))
            res[st] = r
        for ax in (ax_t, ax_b, ax_d):
            ax.clear()
        grey = iter(["#8f8d86", "#b3b1aa", "#6f6d67", "#a19f98", "#7d7b75"])
        cols = {st: HIGHLIGHT.get(st) or next(grey) for st in chosen}
        for st, r in res.items():
            s = r.series
            t, y = _smooth(s)
            ax_t.plot(t, y, label=REGISTRY[st].label, color=cols[st],
                      linewidth=2.4 if st == "ceab" else 1.6)
        ax_t.set_title("Throughput over time")
        ax_t.set_xlabel("Time (s)")
        ax_t.set_ylabel("Mb/s")
        ax_t.legend(loc="lower right", ncol=3)
        x = np.arange(len(chosen))
        lab = [REGISTRY[s].label.replace(" (proposed)", "*").replace(" (802.11)", "") for s in chosen]
        ax_b.bar(x, [res[s].metrics["throughput"] for s in chosen], color=[cols[s] for s in chosen])
        ax_b.set_xticks(x, lab, rotation=30, ha="right")
        ax_b.set_title("Mean throughput (Mb/s)")
        ax_d.bar(x, [res[s].metrics["access_delay_p99"] for s in chosen], color=[cols[s] for s in chosen])
        ax_d.set_xticks(x, lab, rotation=30, ha="right")
        ax_d.set_title("p99 access delay (ms)")
        for ax in (ax_b, ax_d):
            ax.grid(axis="x", visible=False)
        mode = f"{a.load:g} Mb/s offered" if a.load else "saturated"
        status.set_text(f"N={a.nodes}, {mode}, FER={a.fer:.2f}, payload={a.payload} B, "
                        f"{'RTS/CTS' if a.rts else 'basic'}  —  "
                        + "   ".join(f"{REGISTRY[s].label}: {res[s].metrics['throughput']:.2f} Mb/s"
                                     for s in chosen))
        fig.canvas.draw_idle()

    btn.on_clicked(run)
    run()
    plt.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("compare", "gui", "trace"):
        p = sub.add_parser(name)
        p.add_argument("-n", "--nodes", type=int, default=50)
        p.add_argument("--strategies", nargs="+", default=["beb", "ceab"], choices=list(REGISTRY))
        p.add_argument("--duration", type=float, default=5.0, help="simulated seconds")
        p.add_argument("--runs", type=int, default=1, help="independent seeds (mean ± SD)")
        p.add_argument("--load", type=float, default=None, help="offered load in Mb/s (default saturated)")
        p.add_argument("--fer", type=float, default=0.0, help="frame error rate")
        p.add_argument("--rts", action="store_true", help="use RTS/CTS")
        p.add_argument("--payload", type=int, default=1500)
        p.add_argument("--cwmin", type=int, default=16, help="window size W0 (= CWmin+1)")
        p.add_argument("--cwmax", type=int, default=1024)
        p.add_argument("--retry", type=int, default=7, help="retry limit")
        p.add_argument("--churn", nargs="*", help="time:active pairs, e.g. 3:50 6:10")
        p.add_argument("--start", type=int, help="active stations at t=0 when using --churn")
        p.add_argument("--ceab-k", type=int, help="CEAB escalation cap K")
        p.add_argument("--ceab-m", type=int, help="CEAB estimation window M")
        p.add_argument("--plot", action="store_true", help="show plots (compare)")
        p.add_argument("--events", type=int, default=20, help="events to print (trace)")
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "list":
        for k, c in REGISTRY.items():
            print(f"  {k:<10} {c.label:<18} {(c.__doc__ or '').strip().splitlines()[0]}")
    elif a.cmd == "compare":
        run_compare(a)
    elif a.cmd == "trace":
        run_trace(a)
    else:
        run_gui(a)


if __name__ == "__main__":
    sys.exit(main())
