"""Event-driven slot-level simulator of the IEEE 802.11 DCF (single collision domain).

The simulator skips idle slots in bulk: at each step it finds the smallest backoff counter
among contending stations and jumps straight to that slot boundary (unless a packet arrival
or a churn event happens first). A transmission occupies the channel for Ts (exactly one
transmitter, no channel error) or Tc (two or more transmitters, or a corrupted frame);
backoff counters are frozen during busy periods, as in the standard.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math

import numpy as np

from .phy import PhyParams
from .strategies import REGISTRY, Strategy


@dataclass
class SimConfig:
    n: int = 20                                  # number of stations
    strategy: str | list = "beb"                 # name, or [(name, count), ...] for a mixed network
    duration: float = 10.0                       # simulated seconds
    warmup: float = 1.0                          # seconds discarded before measuring
    seed: int = 1
    phy: PhyParams = field(default_factory=PhyParams)
    arrival_rate: float | None = None            # packets/s per station (Poisson); None = saturated
    queue_cap: int = 100                         # per-station buffer (unsaturated traffic)
    fer: float = 0.0                             # frame error rate of the channel (non-collision losses)
    churn: list = field(default_factory=list)    # [(time_s, n_active), ...]
    initial_active: int | None = None            # stations active at t=0 (default: all)
    strategy_kwargs: dict = field(default_factory=dict)
    sample_interval: float = 0.05                # s, time-series bin width
    fairness_window: float = 0.1                 # s, window for short-term Jain index
    trace_limit: int = 0                         # record the first k channel events (packet-capture-like)


@dataclass
class SimResult:
    config: SimConfig
    metrics: dict
    series: dict


def jain(x) -> float:
    x = np.asarray(x, dtype=float)
    s2 = (x ** 2).sum()
    return float(x.sum() ** 2 / (len(x) * s2)) if s2 > 0 else 1.0


class Simulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.phy = cfg.phy
        self.rng = np.random.default_rng(cfg.seed)
        n = cfg.n
        spec = [(cfg.strategy, n)] if isinstance(cfg.strategy, str) else list(cfg.strategy)
        assert sum(c for _, c in spec) == n, "strategy counts must add up to n"
        self.groups: list[tuple[Strategy, np.ndarray]] = []
        self.group_of = np.zeros(n, dtype=np.int64)
        self.local_of = np.zeros(n, dtype=np.int64)
        start = 0
        for gi, (name, count) in enumerate(spec):
            strat = REGISTRY[name](count, self.phy, n_total=n, **cfg.strategy_kwargs.get(name, {}))
            idx = np.arange(start, start + count)
            self.groups.append((strat, idx))
            self.group_of[idx] = gi
            self.local_of[idx] = np.arange(count)
            start += count
        self.observers = [g for g, (s, _) in enumerate(self.groups)
                          if type(s).observe is not Strategy.observe]
        self.label_of = [REGISTRY[name].name for name, _ in spec]

    # ------------------------------------------------------------------ helpers
    def _draw(self, i: int):
        strat, _ = self.groups[self.group_of[i]]
        w = int(strat.window(self.local_of[i]))
        self.counter[i] = self.rng.integers(0, w)

    def _call(self, i: int, method: str, *args):
        strat, _ = self.groups[self.group_of[i]]
        getattr(strat, method)(np.array([self.local_of[i]]), *args)

    # ------------------------------------------------------------------ main loop
    def run(self) -> SimResult:
        cfg, phy, rng = self.cfg, self.phy, self.rng
        n = cfg.n
        T = cfg.duration * 1e6
        T0 = cfg.warmup * 1e6
        saturated = cfg.arrival_rate is None

        self.counter = np.full(n, -1, dtype=np.int64)
        retry = np.zeros(n, dtype=np.int64)
        hol = np.zeros(n)                            # time the head-of-line frame reached the MAC head
        queues = [deque() for _ in range(n)]         # arrival timestamps (unsaturated)
        n_init = n if cfg.initial_active is None else cfg.initial_active
        active = np.zeros(n, dtype=bool)
        active[:n_init] = True

        if saturated:
            next_arr = np.full(n, math.inf)
        else:
            next_arr = rng.exponential(1e6 / cfg.arrival_rate, n)
        churn = sorted((t * 1e6, k) for t, k in cfg.churn)
        ci = 0

        now = 0.0
        for i in np.flatnonzero(active):
            if saturated:
                self._draw(i)

        # statistics
        succ_t, succ_node, acc_delay, e2e_delay = [], [], [], []
        attempts = failures_coll = failures_err = drops = overflow = 0
        busy_coll_events = busy_events = 0
        n_samples = int(math.ceil(cfg.duration / cfg.sample_interval))
        s_W = np.full(n_samples, np.nan)
        s_nhat = np.full(n_samples, np.nan)
        s_active = np.zeros(n_samples)
        next_sample = 0
        idle_acc = 0
        trace = []
        last_busy_end = 0.0
        slot = phy.slot

        def take_samples(upto):
            nonlocal next_sample
            while next_sample < n_samples and next_sample * cfg.sample_interval * 1e6 <= upto:
                act = np.flatnonzero(active)
                ws, nh = [], []
                for strat, idx in self.groups:
                    sel = np.isin(idx, act)
                    if sel.any():
                        ws.append(strat.W[sel])
                        if hasattr(strat, "n_hat"):
                            nh.append(strat.n_hat()[sel])
                if ws:
                    s_W[next_sample] = np.concatenate(ws).mean()
                if nh:
                    s_nhat[next_sample] = np.concatenate(nh).mean()
                s_active[next_sample] = act.size
                next_sample += 1

        while now < T:
            take_samples(now)
            t_arr = next_arr.min() if not saturated else math.inf
            t_churn = churn[ci][0] if ci < len(churn) else math.inf
            t_ev = min(t_arr, t_churn)
            cont = np.flatnonzero(self.counter >= 0)

            if cont.size:
                m = int(self.counter[cont].min())
                t_tx = now + m * slot
            else:
                t_tx = math.inf

            if t_tx == math.inf and t_ev == math.inf:
                break

            if t_ev < t_tx:
                # advance to the slot boundary at/after the event, then handle it
                k = max(0, math.ceil((t_ev - now) / slot))
                if cont.size and k:
                    self.counter[cont] -= k
                if cont.size:
                    idle_acc += k
                now += k * slot
                if ci < len(churn) and churn[ci][0] <= now:
                    target = churn[ci][1]
                    ci += 1
                    cur = int(active.sum())
                    if target > cur:
                        for i in np.flatnonzero(~active)[: target - cur]:
                            active[i] = True
                            self._call(i, "reset")
                            retry[i] = 0
                            if saturated or queues[i]:
                                hol[i] = now
                                self._draw(i)
                    elif target < cur:
                        for i in np.flatnonzero(active)[target:]:
                            active[i] = False
                            self.counter[i] = -1
                if not saturated:
                    for i in np.flatnonzero(next_arr <= now):
                        while next_arr[i] <= now:
                            if len(queues[i]) < cfg.queue_cap:
                                queues[i].append(next_arr[i])
                                if len(queues[i]) == 1 and active[i]:
                                    hol[i] = now
                                    retry[i] = 0
                                    self._draw(i)
                            elif next_arr[i] >= T0:
                                overflow += 1
                            next_arr[i] += rng.exponential(1e6 / cfg.arrival_rate)
                continue

            # ---- a transmission starts at t_tx
            self.counter[cont] -= m
            idle_acc += m
            now = t_tx
            tx = cont[self.counter[cont] == 0]
            measuring = now >= T0
            success = tx.size == 1 and (cfg.fer == 0 or rng.random() >= cfg.fer)
            busy = phy.ts if success else phy.tc
            if measuring:
                attempts += tx.size
                busy_events += 1
                if tx.size > 1:
                    busy_coll_events += 1
                    failures_coll += tx.size
                elif not success:
                    failures_err += 1

            if len(trace) < cfg.trace_limit:
                trace.append({"t_us": now, "idle_slots": idle_acc, "tx": [int(i) for i in tx],
                              "W": [int(self.groups[self.group_of[i]][0].window(self.local_of[i]))
                                    for i in tx],
                              "retry": [int(retry[i]) for i in tx],
                              "outcome": "SUCCESS" if success else
                              ("COLLISION" if tx.size > 1 else "FRAME-ERROR"),
                              "busy_us": busy})
            if self.observers:
                tx_mask = np.zeros(n, dtype=bool)
                tx_mask[tx] = True
                cont_mask = self.counter >= 0
                for g in self.observers:
                    strat, idx = self.groups[g]
                    strat.observe(idle_acc, tx_mask[idx], cont_mask[idx], success,
                                  int(tx[0]) if success else -1, busy,
                                  now - last_busy_end)
            idle_acc = 0
            now += busy
            last_busy_end = now

            for i in tx:
                if success:
                    if measuring:
                        succ_t.append(now)
                        succ_node.append(i)
                        acc_delay.append(now - hol[i])
                        if not saturated:
                            e2e_delay.append(now - queues[i][0])
                    self._call(i, "on_success")
                    retry[i] = 0
                    if saturated:
                        hol[i] = now
                        self._draw(i)
                    else:
                        queues[i].popleft()
                        if queues[i]:
                            hol[i] = now
                            self._draw(i)
                        else:
                            self.counter[i] = -1
                else:
                    retry[i] += 1
                    if phy.retry_limit is not None and retry[i] > phy.retry_limit:
                        if measuring:
                            drops += 1
                        self._call(i, "on_drop")
                        retry[i] = 0
                        if not saturated:
                            queues[i].popleft()
                            if not queues[i]:
                                self.counter[i] = -1
                                continue
                        hol[i] = now
                        self._draw(i)
                    else:
                        self._call(i, "on_failure", retry[i])
                        self._draw(i)

        take_samples(T)
        self.trace = trace
        return self._finish(succ_t, succ_node, acc_delay, e2e_delay, attempts, failures_coll,
                            failures_err, drops, overflow, busy_events, busy_coll_events,
                            s_W, s_nhat, s_active)

    # ------------------------------------------------------------------ metrics
    def _finish(self, succ_t, succ_node, acc_delay, e2e_delay, attempts, failures_coll,
                failures_err, drops, overflow, busy_events, busy_coll_events, s_W, s_nhat, s_active):
        cfg, phy = self.cfg, self.phy
        meas_us = (cfg.duration - cfg.warmup) * 1e6
        succ_t = np.asarray(succ_t)
        succ_node = np.asarray(succ_node, dtype=np.int64)
        acc = np.asarray(acc_delay) / 1e3        # ms
        e2e = np.asarray(e2e_delay) / 1e3
        nsucc = succ_t.size
        bits = phy.payload * 8

        per_node = np.bincount(succ_node, minlength=cfg.n)
        # short-term fairness over fixed windows (only meaningful without churn)
        win = cfg.fairness_window * 1e6
        nwin = int(meas_us // win)
        st = []
        if nsucc and nwin:
            b = ((succ_t - cfg.warmup * 1e6) // win).astype(np.int64)
            ok = b < nwin
            counts = np.zeros((nwin, cfg.n))
            np.add.at(counts, (b[ok], succ_node[ok]), 1)
            st = [jain(row) for row in counts]

        # per-group share (coexistence experiments)
        share = {}
        for (strat, idx), name in zip(self.groups, self.label_of):
            share[name] = float(per_node[idx].sum() * bits / meas_us) if nsucc else 0.0

        bins = np.arange(0, cfg.duration * 1e6 + 1, cfg.sample_interval * 1e6)
        thr_series = np.histogram(succ_t, bins=bins)[0] * bits / (cfg.sample_interval * 1e6)
        if cfg.warmup > 0:
            thr_series[: int(cfg.warmup / cfg.sample_interval)] = np.nan

        metrics = {
            "throughput": nsucc * bits / meas_us,                       # Mb/s
            "collision_prob": failures_coll / attempts if attempts else 0.0,
            "busy_collision_ratio": busy_coll_events / busy_events if busy_events else 0.0,
            "access_delay_mean": float(acc.mean()) if acc.size else math.nan,
            "access_delay_p99": float(np.percentile(acc, 99)) if acc.size else math.nan,
            "access_delay_std": float(acc.std()) if acc.size else math.nan,
            "e2e_delay_mean": float(e2e.mean()) if e2e.size else math.nan,
            "jain_long": jain(per_node),
            "jain_short": float(np.mean(st)) if st else math.nan,
            "drop_rate": drops / (nsucc + drops) if (nsucc + drops) else 0.0,
            "overflow": overflow,
            "attempts": attempts,
            "successes": nsucc,
            "error_failures": failures_err,
            "share": share,
        }
        series = {
            "t": bins[:-1] / 1e6,
            "throughput": thr_series,
            "mean_W": s_W[: len(bins) - 1],
            "n_hat": s_nhat[: len(bins) - 1],
            "active": s_active[: len(bins) - 1],
        }
        series["trace"] = getattr(self, "trace", [])
        return SimResult(cfg, metrics, series)


def simulate(**kw) -> SimResult:
    phy_kw = {k: kw.pop(k) for k in list(kw) if k in PhyParams.__dataclass_fields__}
    if phy_kw:
        kw["phy"] = PhyParams(**phy_kw)
    return Simulator(SimConfig(**kw)).run()
