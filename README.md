# Made By F1_Team11

# CSMA/CA backoff strategies: CEAB vs IEEE 802.11 BEB


A slot-level IEEE 802.11 DCF simulator that compares **nine backoff ("waiting") strategies**,
plus a proposed scheme, **CEAB – Contender-Estimation Adaptive Backoff**.

| Strategy | Rule |
|---|---|
| `beb` (baseline) | 802.11 binary exponential backoff: W×2 on failure, reset to CWmin on success |
| `constant` | fixed W = 64 |
| `linear` | W += W0 on failure, reset on success |
| `fibonacci` | W = W0·Fib(retry) |
| `quadratic` | W = W0·(retry+1)² |
| `mild` | ×1.5 on failure, −1 on success (MACAW) |
| `eied` | ×2 on failure, ÷2 on success |
| `idlesense` | AIMD towards an optimal mean idle-slot count (Heusse et al.) |
| **`ceab`** (proposed) | W = throughput-optimal window for the contender count estimated from overheard frame addresses (inverse Simpson index), scaled by an idle-gap load factor |

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Live demo
```bash
.venv/bin/python demo.py compare                       # BEB vs CEAB, N = 50, saturated
.venv/bin/python demo.py compare -n 20 --strategies beb eied idlesense ceab --runs 5
.venv/bin/python demo.py compare -n 30 --load 25        # unsaturated traffic (Mb/s offered)
.venv/bin/python demo.py compare -n 20 --fer 0.1 --rts  # lossy channel + RTS/CTS
.venv/bin/python demo.py compare -n 50 --start 5 --churn 3:50 6:10 --plot
.venv/bin/python demo.py trace -n 5 --events 25         # per-frame channel log ("capture")
.venv/bin/python demo.py gui                            # sliders, checkboxes, Run button
```
Every PHY/MAC parameter can be changed on the command line: `--payload`, `--cwmin`, `--cwmax`,
`--retry`, `--duration`, `--runs`, `--ceab-k`, `--ceab-m` (see `demo.py compare -h`).

## Full evaluation
```bash
.venv/bin/python run_experiments.py            # 2170 runs (10 seeds × 10 s), ~6 min on 16 cores
.venv/bin/python run_experiments.py --quick    # smoke test, ~30 s
.venv/bin/python run_experiments.py --plots-only
```
Outputs: `results/raw_runs.csv` (every run), `results/summary.csv` (mean/SD),
`results/results_tables.md`, `figures/*.png`.

## Tests
```bash
.venv/bin/python -m unittest discover -s tests -v
```
Includes validation against the Bianchi (2000) analytical model and an independent Monte Carlo.

## Report and slides
```bash
.venv/bin/python report/diagrams.py          # architecture / topology / flowcharts
.venv/bin/python report/build_report.py      # report/Project_Report.docx (+ .pdf)
.venv/bin/python presentation/build_ppt.py   # presentation/Project_Presentation.pptx
```

## Layout
```
csmasim/phy.py          802.11g timing (slot, SIFS, DIFS, Ts, Tc)
csmasim/analytical.py   Bianchi model, optimal attempt probability tau*(n)
csmasim/strategies.py   the nine backoff strategies (CEAB at the bottom)
csmasim/simulator.py    event-driven DCF engine + metrics
csmasim/experiments.py  scenario definitions, parallel runner
csmasim/analysis.py     tables, Welch t-tests, figures
demo.py                 CLI / GUI demo
run_experiments.py      full evaluation
tests/                  correctness tests
```
