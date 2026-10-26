"""Analytical models used for (a) validating the simulator and (b) the proposed scheme.

* Bianchi (2000) Markov-chain model of 802.11 DCF with binary exponential backoff.
* Optimal per-slot attempt probability tau*(n) of a p-persistent CSMA/CA system
  (Cali et al. 2000; Bianchi 2000) -- used by CEAB to turn an estimate of the number
  of contenders into a target contention window.
"""
from functools import lru_cache
import numpy as np
from scipy.optimize import brentq, minimize_scalar

from .phy import PhyParams


def throughput_from_tau(tau: float, n: float, phy: PhyParams) -> float:
    """Saturation throughput (Mb/s) of n stations each attempting with probability tau per slot."""
    p_idle = (1 - tau) ** n
    p_tr = 1 - p_idle
    if p_tr <= 0:
        return 0.0
    p_s = n * tau * (1 - tau) ** (n - 1) / p_tr
    num = p_s * p_tr * phy.payload * 8
    den = p_idle * phy.slot + p_tr * p_s * phy.ts + p_tr * (1 - p_s) * phy.tc
    return num / den  # bits per microsecond == Mb/s


def bianchi(n: int, phy: PhyParams) -> dict:
    """Solve Bianchi's fixed point (W = CWmin+1, m backoff stages, unlimited retries)."""
    W = phy.cw_min
    m = int(round(np.log2(phy.cw_max / phy.cw_min)))

    def tau_of_p(p):
        if abs(1 - 2 * p) < 1e-12:
            p += 1e-9
        return 2 * (1 - 2 * p) / ((1 - 2 * p) * (W + 1) + p * W * (1 - (2 * p) ** m))

    if n == 1:
        tau, p = tau_of_p(0.0), 0.0
    else:
        f = lambda p: p - (1 - (1 - tau_of_p(p)) ** (n - 1))
        p = brentq(f, 1e-9, 1 - 1e-9)
        tau = tau_of_p(p)
    return {"tau": tau, "p": p, "throughput": throughput_from_tau(tau, n, phy)}


@lru_cache(maxsize=64)
def _tau_opt_table(tc: float, ts: float, slot: float, payload: int):
    phy_like = type("P", (), {"tc": tc, "ts": ts, "slot": slot, "payload": payload})
    ns = np.concatenate([np.arange(1, 10, 0.25), np.arange(10, 100, 1.0), np.arange(100, 1001, 10.0)])
    taus = []
    for n in ns:
        r = minimize_scalar(lambda t: -throughput_from_tau(t, n, phy_like),
                            bounds=(1e-5, 0.999), method="bounded",
                            options={"xatol": 1e-7})
        taus.append(r.x)
    return ns, np.array(taus)


def tau_opt(n_hat, phy: PhyParams):
    """Optimal attempt probability for an (estimated, possibly fractional) number of contenders."""
    ns, taus = _tau_opt_table(phy.tc, phy.ts, phy.slot, phy.payload)
    return np.interp(np.clip(n_hat, ns[0], ns[-1]), ns, taus)


def w_opt(n_hat, phy: PhyParams):
    """Window size W (backoff uniform on [0, W-1]) whose mean attempt rate equals tau*: tau = 2/(W+1)."""
    return 2.0 / tau_opt(n_hat, phy) - 1.0


def optimal_idle_slots(phy: PhyParams, n: float = 50) -> float:
    """Mean number of idle slots between transmission attempts at the throughput optimum
    (target value for the Idle Sense controller)."""
    t = tau_opt(n, phy)
    p_idle = (1 - t) ** n
    return p_idle / (1 - p_idle)
