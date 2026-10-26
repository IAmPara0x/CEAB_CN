#!/usr/bin/env python3
"""Run the full evaluation (repeated runs of every scenario), then build tables and figures.

    python run_experiments.py                 # full: 10 runs x 10 s per configuration
    python run_experiments.py --quick         # smoke test: 3 runs x 3 s, fewer sweep points
    python run_experiments.py --plots-only    # rebuild tables/figures from results/raw_runs.csv
"""
import argparse
import os
import time

import matplotlib
matplotlib.use("Agg")          # batch run: render figures to files, never open windows

from csmasim.analysis import load, make_figures, summary_csv, write_markdown
from csmasim.experiments import run_all

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=10, help="independent seeds per configuration")
    ap.add_argument("--duration", type=float, default=10.0, help="simulated seconds per run")
    ap.add_argument("--procs", type=int, default=None, help="worker processes (default: all cores)")
    ap.add_argument("--quick", action="store_true", help="3 runs x 3 s, reduced sweeps")
    ap.add_argument("--only", nargs="*", help="run only these scenario tags (e.g. S1 S2 churn)")
    ap.add_argument("--plots-only", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--figs", default=os.path.join(HERE, "figures"))
    a = ap.parse_args()

    if not a.plots_only:
        if a.quick:
            a.runs, a.duration = 3, 3.0
        t0 = time.time()
        run_all(a.out, runs=a.runs, duration=a.duration, procs=a.procs, quick=a.quick, only=a.only)
        print(f"simulations finished in {time.time() - t0:.0f} s")

    rows = load(a.out)
    summary_csv(rows, os.path.join(a.out, "summary.csv"))
    write_markdown(rows, os.path.join(a.out, "results_tables.md"))
    figs = make_figures(rows, a.out, a.figs)
    print(f"wrote {a.out}/summary.csv, {a.out}/results_tables.md and {len(figs)} figures in {a.figs}/")


if __name__ == "__main__":
    main()
