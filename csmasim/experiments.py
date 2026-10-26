"""Experiment definitions: every scenario of the evaluation, run with repeated seeds."""
from __future__ import annotations

import csv
import json
import os
from multiprocessing import Pool

import numpy as np

from .analytical import bianchi, throughput_from_tau, tau_opt
from .phy import PhyParams
from .simulator import simulate
from .strategies import ALL

METRICS = ["throughput", "collision_prob", "access_delay_mean", "access_delay_p99",
           "access_delay_std", "e2e_delay_mean", "jain_short", "jain_long", "drop_rate"]
MAIN = ["beb", "eied", "idlesense", "ceab"]          # strategies used in the heavier sweeps


def build_jobs(runs: int, duration: float, quick: bool = False):
    seeds = list(range(1, runs + 1))
    J = []

    def add(tag, param, **kw):
        kw.setdefault("duration", duration)
        for s in seeds:
            J.append((tag, param, s, kw))

    # S1-S3: low / medium / high contention, saturated, every strategy
    for label, n in [("S1", 5), ("S2", 20), ("S3", 50)]:
        for st in ALL:
            add(label, n, n=n, strategy=st)
    # number-of-stations sweep (saturated)
    for n in ([2, 5, 10, 20, 35, 50, 75, 100] if not quick else [5, 20, 50]):
        for st in ALL:
            add("sweep_n", n, n=n, strategy=st)
    # validation against Bianchi (BEB, unlimited retries)
    for n in [2, 5, 10, 20, 35, 50, 75, 100]:
        add("validation", n, n=n, strategy="beb", retry_limit=None)
    # unsaturated traffic: offered load sweep at N = 30
    for load in ([2, 5, 10, 15, 20, 25, 28, 32, 40] if not quick else [5, 20, 32]):
        lam = load * 1e6 / (30 * 1500 * 8)
        for st in MAIN:
            add("load", load, n=30, strategy=st, arrival_rate=lam)
    # frame error rate (non-collision loss)
    for fer in [0.0, 0.05, 0.1, 0.2, 0.3]:
        for st in MAIN:
            add("fer", fer, n=20, strategy=st, fer=fer)
    # RTS/CTS access (collisions become cheap)
    for n in [5, 20, 50]:
        for st in MAIN:
            add("rts", n, n=n, strategy=st, rts_cts=True)
    # payload size
    for pl in [256, 512, 1000, 1500, 2304]:
        for st in MAIN:
            add("payload", pl, n=20, strategy=st, payload=pl)
    # coexistence: 10 legacy BEB + 10 stations of strategy X
    for st in ["beb", "eied", "idlesense", "ceab"]:
        add("coexist", st, n=20, strategy=[("beb", 10), (st, 10)])
    # ablation of CEAB parameters at N = 50 and N = 20
    for n in [20, 50]:
        for K in [0, 1, 2]:
            add("ablation_K", f"{n}:{K}", n=n, strategy="ceab", strategy_kwargs={"ceab": {"K": K}})
        for M in [50, 100, 200, 500, 1000]:
            add("ablation_M", f"{n}:{M}", n=n, strategy="ceab", strategy_kwargs={"ceab": {"M": M}})
    # churn: 5 -> 50 -> 15 stations, time series kept
    churn_kw = dict(n=50, initial_active=5, churn=[(4, 50), (8, 15)], duration=12, warmup=0.5,
                    _keep_series=True)
    for st in MAIN:
        for s in seeds[: max(3, len(seeds) // 2)]:
            kw = dict(churn_kw, strategy=st)
            J.append(("churn", st, s, kw))
    return J


def _strip(kw):
    return {k: v for k, v in kw.items() if not k.startswith("_")}


def _job_wrapper(args):
    tag, param, seed, kw = args
    keep = kw.get("_keep_series", False)
    r = simulate(seed=seed, **_strip(kw))
    row = {"scenario": tag, "param": param, "seed": seed,
           "strategy": kw["strategy"] if isinstance(kw["strategy"], str) else
           "+".join(f"{c}x{nm}" for nm, c in kw["strategy"])}
    for m in METRICS:
        row[m] = r.metrics[m]
    row["share"] = json.dumps(r.metrics["share"])
    return row, ((tag, param, seed, r.series) if keep else None)


def run_all(outdir: str, runs: int = 10, duration: float = 10.0, procs: int | None = None,
            quick: bool = False, only: list | None = None):
    os.makedirs(outdir, exist_ok=True)
    jobs = build_jobs(runs, duration, quick)
    if only:
        jobs = [j for j in jobs if j[0] in only]
    print(f"running {len(jobs)} simulations on {procs or os.cpu_count()} processes ...", flush=True)
    rows, series = [], []
    with Pool(procs) as pool:
        for k, (row, ser) in enumerate(pool.imap_unordered(_job_wrapper, jobs, chunksize=2), 1):
            rows.append(row)
            if ser is not None:
                series.append(ser)
            if k % 100 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)}", flush=True)
    rows.sort(key=lambda r: (r["scenario"], str(r["param"]), r["strategy"], r["seed"]))
    with open(os.path.join(outdir, "raw_runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    if series:
        out = {}
        for tag, st, seed, s in series:
            for key in ("t", "throughput", "mean_W", "n_hat", "active"):
                out.setdefault(f"{st}/{key}", []).append(s[key])
        np.savez(os.path.join(outdir, "churn_series.npz"),
                 **{k: np.array(v) for k, v in out.items()})
    # analytical curves for the validation figure
    phy = PhyParams(retry_limit=None)
    ana = []
    for n in [2, 3, 5, 7, 10, 15, 20, 25, 35, 50, 75, 100]:
        b = bianchi(n, phy)
        ana.append({"n": n, "bianchi_thr": b["throughput"], "bianchi_p": b["p"],
                    "optimal_thr": throughput_from_tau(float(tau_opt(n, phy)), n, phy)})
    with open(os.path.join(outdir, "analytical.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ana[0]))
        w.writeheader()
        w.writerows(ana)
    return rows
