"""Backoff ("waiting") strategies for CSMA/CA.

Every strategy manages the contention window W of a *group* of stations, stored as numpy
arrays indexed by the station's local index inside the group. The simulator calls:

    window(idx)            -> current window size W for stations idx (backoff ~ U[0, W-1])
    on_success(idx)        after an ACKed transmission
    on_failure(idx, retry) after an un-ACKed transmission (collision or channel error);
                           `retry` is the retry count of the head-of-line frame after the failure
    on_drop(idx)           when the frame exceeded the retry limit and was discarded
    observe(idle, tx_mask, contending_mask, success, src, busy_us, idle_us)
                           once per channel busy period: `idle` idle slots preceded it,
                           tx_mask marks the group members that transmitted in it,
                           `success` tells whether it carried a decodable frame, `src` is the
                           global id of that frame's transmitter, busy_us its duration and
                           idle_us the wall-clock idle time since the previous busy period
    reset(idx)             a station (re)joins the network
"""
import numpy as np

from .analytical import w_opt, tau_opt, optimal_idle_slots
from .phy import PhyParams


class Strategy:
    name = "base"
    label = "Base"

    def __init__(self, n: int, phy: PhyParams, **kw):
        self.n = n
        self.phy = phy
        self.wmin = float(phy.cw_min)
        self.wmax = float(phy.cw_max)
        self.W = np.full(n, self.wmin)

    def window(self, idx):
        return np.clip(np.rint(self.W[idx]), 1, self.wmax).astype(np.int64)

    def on_success(self, idx):
        self.W[idx] = self.wmin

    def on_failure(self, idx, retry):
        pass

    def on_drop(self, idx):
        self.W[idx] = self.wmin

    def observe(self, idle, tx_mask, contending_mask, success, src=-1, busy_us=0.0, idle_us=0.0):
        pass

    def reset(self, idx):
        self.W[idx] = self.wmin


# --------------------------------------------------------------------- classic schemes
class BEB(Strategy):
    """IEEE 802.11 DCF binary exponential backoff (baseline)."""
    name, label = "beb", "BEB (802.11)"

    def on_failure(self, idx, retry):
        self.W[idx] = np.minimum(self.W[idx] * 2, self.wmax)


class Constant(Strategy):
    """No adaptation: fixed window regardless of outcome (p-persistent-like)."""
    name, label = "constant", "Constant W=64"

    def __init__(self, n, phy, w=64, **kw):
        super().__init__(n, phy)
        self.w = float(w)
        self.W[:] = self.w

    def on_success(self, idx):
        pass

    def on_drop(self, idx):
        pass

    def reset(self, idx):
        self.W[idx] = self.w


class Linear(Strategy):
    """Linear increase (W += W0 per failure), reset on success."""
    name, label = "linear", "Linear"

    def on_failure(self, idx, retry):
        self.W[idx] = np.minimum(self.W[idx] + self.wmin, self.wmax)


class Fibonacci(Strategy):
    """Window follows the Fibonacci sequence across retries: W0*{1,2,3,5,8,13,...}."""
    name, label = "fibonacci", "Fibonacci"
    FIB = np.array([1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144], dtype=float)

    def on_failure(self, idx, retry):
        k = np.minimum(retry, len(self.FIB) - 1)
        self.W[idx] = np.minimum(self.wmin * self.FIB[k], self.wmax)


class Quadratic(Strategy):
    """Polynomial growth: W = W0 * (retry+1)^2."""
    name, label = "quadratic", "Quadratic"

    def on_failure(self, idx, retry):
        self.W[idx] = np.minimum(self.wmin * (np.asarray(retry) + 1.0) ** 2, self.wmax)


class MILD(Strategy):
    """Multiplicative Increase (x1.5) Linear Decrease (-1 slot) -- MACAW, Bharghavan et al. 1994."""
    name, label = "mild", "MILD"

    def on_success(self, idx):
        self.W[idx] = np.maximum(self.W[idx] - 1.0, self.wmin)

    def on_failure(self, idx, retry):
        self.W[idx] = np.minimum(self.W[idx] * 1.5, self.wmax)

    def on_drop(self, idx):
        pass


class EIED(Strategy):
    """Exponential Increase Exponential Decrease (x2 / /2) -- Song et al. 2003."""
    name, label = "eied", "EIED"

    def on_success(self, idx):
        self.W[idx] = np.maximum(self.W[idx] / 2.0, self.wmin)

    def on_failure(self, idx, retry):
        self.W[idx] = np.minimum(self.W[idx] * 2.0, self.wmax)

    def on_drop(self, idx):
        pass


class IdleSense(Strategy):
    """Simplified re-implementation of Idle Sense (Heusse et al., SIGCOMM 2005).

    Each station averages the number of idle slots between consecutive transmissions over
    `maxtrans` busy periods and steers its window so that this average matches the
    throughput-optimal target: additive increase when the channel is too busy,
    multiplicative decrease when it is too idle. No per-collision doubling.
    """
    name, label = "idlesense", "Idle Sense"

    def __init__(self, n, phy, eps=6.0, alpha=1 / 1.0666, maxtrans=5, **kw):
        super().__init__(n, phy)
        self.eps, self.alpha, self.maxtrans = eps, alpha, maxtrans
        self.target = optimal_idle_slots(phy)
        self.sum_idle = np.zeros(n)
        self.ntrans = np.zeros(n)

    def on_success(self, idx):
        pass

    def on_drop(self, idx):
        pass

    def observe(self, idle, tx_mask, contending_mask, success, src=-1, busy_us=0.0, idle_us=0.0):
        m = contending_mask
        self.sum_idle[m] += idle
        self.ntrans[m] += 1
        ready = m & (self.ntrans >= self.maxtrans)
        if ready.any():
            avg = self.sum_idle[ready] / self.ntrans[ready]
            w = self.W[ready]
            self.W[ready] = np.where(avg < self.target,
                                     np.minimum(w + self.eps, self.wmax),
                                     np.maximum(w * self.alpha, self.wmin))
            self.sum_idle[ready] = 0
            self.ntrans[ready] = 0

    def reset(self, idx):
        super().reset(idx)
        self.sum_idle[idx] = 0
        self.ntrans[idx] = 0


# --------------------------------------------------------------------- proposed scheme
class CEAB(Strategy):
    """Contender-Estimation Adaptive Backoff (proposed).

    1. Contender estimation from overheard frames. Every station decodes the transmitter
       address (TA) of each successful frame on the channel and keeps the last M of them.
       With c_j = frames from station j in that window, the effective number of contenders is
       the inverse Simpson index (unbiased form)
               n_eff = M (M-1) / sum_j c_j (c_j - 1),
       which equals n when n stations share the channel equally and discounts lightly-loaded
       stations. It uses no model of the other stations' backoff rule.
    2. Load factor. Each station keeps an EWMA of the idle gap between busy periods, I_obs (us),
       and compares it with I*, the mean idle gap at the analytical throughput optimum:
               rho = min(1, I* / I_obs),   n_c = max(1, rho * n_eff).
       Under saturation I_obs ~ I* and rho ~ 1; with unsaturated traffic the channel is idle
       far longer than at the optimum, rho << 1, and the window shrinks towards CWmin. The loop
       is self-correcting: a window that is too large creates extra idle time, which lowers rho.
    3. Target window W* = 2/tau*(n_c) - 1, tau*(n) = optimal attempt probability for the PHY
       timing (Ts, Tc, slot); the base window W_base moves a fraction gamma towards W*.
    4. Optional bounded escalation: the k-th retry of a frame uses W_base * 2^min(k, K) and a
       success returns to W_base, never to CWmin. K=0 (default) means collisions do not change
       the window at all -- the estimate alone sets it (see the ablation study).
    """
    name, label = "ceab", "CEAB (proposed)"

    def __init__(self, n, phy, M=200, beta_u=0.05, gamma=0.5, K=0, w_floor=None, **kw):
        super().__init__(n, phy)
        self.M, self.beta_u, self.gamma, self.K = int(M), beta_u, gamma, K
        self.w_floor = float(w_floor if w_floor is not None else phy.cw_min)
        self.W_base = np.full(n, self.wmin)
        self.log = []                               # TA of every successful frame heard
        self.join = np.zeros(n, dtype=np.int64)     # log position when the station (re)joined
        self.n_total = kw.get("n_total", n)
        self.idle = np.full(n, (self.wmin - 1) / 2 * phy.slot)   # EWMA idle gap (us)
        self.idle_star = optimal_idle_slots(phy) * phy.slot       # idle gap at the optimum (us)

    def n_eff(self, i):
        lo = max(int(self.join[i]), len(self.log) - self.M)
        win = self.log[lo:]
        m = len(win)
        if m < 2:
            return 1.0
        c = np.bincount(win)
        d = float((c * (c - 1)).sum())
        return m * (m - 1) / d if d > 0 else float(m)

    def load_factor(self, idx=slice(None)):
        return np.minimum(1.0, self.idle_star / np.maximum(self.idle[idx], 1e-9))

    def n_hat(self, idx=None):
        idx = np.arange(self.n) if idx is None else np.atleast_1d(idx)
        ne = np.array([self.n_eff(i) for i in idx])
        return np.maximum(1.0, self.load_factor(idx) * ne)

    def observe(self, idle, tx_mask, contending_mask, success, src=-1, busy_us=0.0, idle_us=0.0):
        if success and src >= 0:
            self.log.append(int(src))
            if len(self.log) > 4 * self.M:      # trim history nobody needs any more
                cut = len(self.log) - self.M
                self.log = self.log[cut:]
                self.join = np.maximum(self.join - cut, 0)
        b = self.beta_u
        self.idle = (1 - b) * self.idle + b * idle_us

    def _update_base(self, idx):
        target = w_opt(self.n_hat(idx), self.phy)
        wb = self.W_base[idx]
        self.W_base[idx] = np.clip(wb + self.gamma * (target - wb), self.w_floor, self.wmax)

    def on_success(self, idx):
        self._update_base(idx)
        self.W[idx] = self.W_base[idx]

    def on_failure(self, idx, retry):
        self._update_base(idx)
        k = np.minimum(retry, self.K)
        self.W[idx] = np.minimum(self.W_base[idx] * 2.0 ** k, self.wmax)

    def on_drop(self, idx):
        self.W[idx] = self.W_base[idx]

    def reset(self, idx):
        self.W[idx] = self.wmin
        self.W_base[idx] = self.wmin
        self.join[idx] = len(self.log)
        self.idle[idx] = (self.wmin - 1) / 2 * self.phy.slot


REGISTRY = {cls.name: cls for cls in
            [BEB, Constant, Linear, Fibonacci, Quadratic, MILD, EIED, IdleSense, CEAB]}
ALL = list(REGISTRY)
