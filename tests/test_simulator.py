"""Correctness checks.  Run with:  python -m unittest discover -s tests -v"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csmasim import PhyParams, simulate                       # noqa: E402
from csmasim.analytical import bianchi                        # noqa: E402
from csmasim.simulator import SimConfig, Simulator            # noqa: E402
from csmasim.strategies import Constant                       # noqa: E402


class TestValidation(unittest.TestCase):
    def test_bianchi_throughput_and_collision_probability(self):
        """BEB with unlimited retries must match Bianchi's model (within 3 % / 0.03)."""
        phy = PhyParams(retry_limit=None)
        for n in (5, 20, 50):
            model = bianchi(n, phy)
            r = simulate(n=n, strategy="beb", duration=6, seed=7, retry_limit=None).metrics
            self.assertAlmostEqual(r["throughput"] / model["throughput"], 1.0, delta=0.03, msg=f"N={n}")
            self.assertAlmostEqual(r["collision_prob"], model["p"], delta=0.03, msg=f"N={n}")

    def test_idle_slots_match_independent_monte_carlo(self):
        """Event-skipping engine == naive slot-by-slot Monte Carlo for a constant window."""
        rec = []
        orig = Constant.observe
        Constant.observe = lambda self, idle, *a, **k: rec.append(idle)
        try:
            Simulator(SimConfig(n=5, strategy="constant", duration=3, warmup=0,
                                strategy_kwargs={"constant": {"w": 16}})).run()
        finally:
            Constant.observe = orig
        rng = np.random.default_rng(0)
        c = rng.integers(0, 16, 5)
        mc = []
        for _ in range(60000):
            m = c.min()
            mc.append(m)
            c -= m
            tx = c == 0
            c[tx] = rng.integers(0, 16, tx.sum())
        self.assertAlmostEqual(np.mean(rec), np.mean(mc), delta=0.05)

    def test_single_station_has_no_collisions(self):
        r = simulate(n=1, strategy="beb", duration=2).metrics
        self.assertEqual(r["collision_prob"], 0.0)
        phy = PhyParams()
        expected = phy.payload * 8 / (phy.ts + (phy.cw_min - 1) / 2 * phy.slot)
        self.assertAlmostEqual(r["throughput"], expected, delta=0.02 * expected)


class TestProposed(unittest.TestCase):
    def test_contender_estimate_tracks_true_n(self):
        for n in (5, 20, 50):
            s = simulate(n=n, strategy="ceab", duration=4, seed=3).series
            est = np.nanmean(s["n_hat"][s["t"] > 1.5])
            self.assertAlmostEqual(est / n, 1.0, delta=0.12, msg=f"N={n}, estimate={est:.1f}")

    def test_ceab_beats_beb_under_high_contention(self):
        beb = simulate(n=50, strategy="beb", duration=4, seed=2).metrics
        ceab = simulate(n=50, strategy="ceab", duration=4, seed=2).metrics
        self.assertGreater(ceab["throughput"], 1.15 * beb["throughput"])
        self.assertLess(ceab["access_delay_p99"], beb["access_delay_p99"])

    def test_ceab_shrinks_window_at_light_load(self):
        """At low offered load CEAB should behave like CWmin (no extra delay)."""
        lam = 5e6 / (30 * 1500 * 8)
        beb = simulate(n=30, strategy="beb", duration=4, arrival_rate=lam).metrics
        ceab = simulate(n=30, strategy="ceab", duration=4, arrival_rate=lam).metrics
        self.assertLess(ceab["e2e_delay_mean"], 1.2 * beb["e2e_delay_mean"])


class TestInvariants(unittest.TestCase):
    def test_reproducible_with_seed(self):
        a = simulate(n=20, strategy="eied", duration=2, seed=11).metrics
        b = simulate(n=20, strategy="eied", duration=2, seed=11).metrics
        self.assertEqual(a["successes"], b["successes"])

    def test_carried_equals_offered_when_unsaturated(self):
        lam = 10e6 / (20 * 1500 * 8)
        for st in ("beb", "ceab", "idlesense"):
            r = simulate(n=20, strategy=st, duration=5, arrival_rate=lam).metrics
            self.assertAlmostEqual(r["throughput"], 10.0, delta=0.6, msg=st)

    def test_mixed_network_shares_add_up(self):
        r = simulate(n=20, strategy=[("beb", 10), ("ceab", 10)], duration=2).metrics
        self.assertAlmostEqual(sum(r["share"].values()), r["throughput"], places=6)


if __name__ == "__main__":
    unittest.main()
