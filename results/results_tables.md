# Results (mean ± SD over repeated runs)

## Baseline (BEB) vs proposed (CEAB)

| Scenario | Metric | Baseline (mean ± SD) | Proposed (mean ± SD) | Improvement (%) | Welch p |
|---|---|---|---|---|---|
| S1 (low load, N=5) | Throughput (Mb/s) | 30.05 ± 0.07 | 30.61 ± 0.08 | +1.9 | 2.6e-12 |
| S1 (low load, N=5) | Collision probability | 0.265 ± 0.003 | 0.187 ± 0.004 | +29.2 | 7.8e-20 |
| S1 (low load, N=5) | Mean access delay (ms) | 1.99 ± 0.01 | 1.96 ± 0.01 | +1.4 | 6.0e-06 |
| S1 (low load, N=5) | 99th-pct access delay (ms) | 15.39 ± 0.43 | 5.99 ± 0.07 | +61.1 | 4.5e-14 |
| S1 (low load, N=5) | Short-term Jain fairness (100 ms) | 0.917 ± 0.004 | 0.993 ± 0.000 | +8.2 | 5.2e-13 |
| S1 (low load, N=5) | Frame drop rate | 0.005% ± 0.004% | 0.000% ± 0.000% | +100.0 | 6.7e-03 |
| S2 (medium load, N=20) | Throughput (Mb/s) | 25.84 ± 0.06 | 29.93 ± 0.10 | +15.8 | 8.0e-22 |
| S2 (medium load, N=20) | Collision probability | 0.468 ± 0.002 | 0.207 ± 0.005 | +55.7 | 2.1e-21 |
| S2 (medium load, N=20) | Mean access delay (ms) | 8.34 ± 0.09 | 8.02 ± 0.03 | +3.9 | 2.7e-07 |
| S2 (medium load, N=20) | 99th-pct access delay (ms) | 127.05 ± 2.74 | 25.63 ± 0.27 | +79.8 | 7.3e-16 |
| S2 (medium load, N=20) | Short-term Jain fairness (100 ms) | 0.599 ± 0.008 | 0.965 ± 0.001 | +61.1 | 2.1e-16 |
| S2 (medium load, N=20) | Frame drop rate | 0.345% ± 0.033% | 0.000% ± 0.000% | +100.0 | 1.1e-10 |
| S3 (high load, N=50) | Throughput (Mb/s) | 22.33 ± 0.06 | 29.81 ± 0.07 | +33.5 | 6.7e-32 |
| S3 (high load, N=50) | Collision probability | 0.595 ± 0.002 | 0.204 ± 0.004 | +65.7 | 3.4e-27 |
| S3 (high load, N=50) | Mean access delay (ms) | 20.00 ± 0.33 | 20.13 ± 0.05 | -0.6 | 2.8e-01 |
| S3 (high load, N=50) | 99th-pct access delay (ms) | 304.04 ± 5.51 | 64.74 ± 0.89 | +78.7 | 6.9e-17 |
| S3 (high load, N=50) | Short-term Jain fairness (100 ms) | 0.397 ± 0.006 | 0.910 ± 0.002 | +129.1 | 9.9e-22 |
| S3 (high load, N=50) | Frame drop rate | 2.007% ± 0.107% | 0.000% ± 0.000% | +100.0 | 5.4e-13 |

## All strategies — Throughput (Mb/s)

| Strategy | S1 (N=5) | S2 (N=20) | S3 (N=50) |
|---|---|---|---|
| BEB (802.11) | 30.05 ± 0.07 | 25.84 ± 0.06 | 22.33 ± 0.06 |
| Constant W=64 | 30.06 ± 0.05 | 26.22 ± 0.07 | 15.65 ± 0.12 |
| Linear | 29.55 ± 0.07 | 21.97 ± 0.06 | 14.40 ± 0.05 |
| Fibonacci | 29.69 ± 0.08 | 23.99 ± 0.08 | 19.09 ± 0.07 |
| Quadratic | 30.59 ± 0.06 | 27.20 ± 0.05 | 23.64 ± 0.05 |
| MILD | 29.34 ± 6.53 | 21.72 ± 0.06 | 27.91 ± 0.05 |
| EIED | 30.50 ± 0.07 | 28.44 ± 0.05 | 26.79 ± 0.05 |
| Idle Sense | 30.57 ± 0.07 | 29.67 ± 0.08 | 29.06 ± 0.10 |
| CEAB (proposed) | 30.61 ± 0.08 | 29.93 ± 0.10 | 29.81 ± 0.07 |

## All strategies — Collision probability

| Strategy | S1 (N=5) | S2 (N=20) | S3 (N=50) |
|---|---|---|---|
| BEB (802.11) | 0.265 ± 0.003 | 0.468 ± 0.002 | 0.595 ± 0.002 |
| Constant W=64 | 0.117 ± 0.002 | 0.447 ± 0.003 | 0.778 ± 0.002 |
| Linear | 0.295 ± 0.002 | 0.607 ± 0.002 | 0.809 ± 0.001 |
| Fibonacci | 0.287 ± 0.003 | 0.538 ± 0.003 | 0.693 ± 0.002 |
| Quadratic | 0.215 ± 0.002 | 0.409 ± 0.002 | 0.550 ± 0.001 |
| MILD | 0.014 ± 0.002 | 0.037 ± 0.002 | 0.091 ± 0.002 |
| EIED | 0.231 ± 0.004 | 0.349 ± 0.002 | 0.425 ± 0.002 |
| Idle Sense | 0.159 ± 0.004 | 0.243 ± 0.004 | 0.292 ± 0.004 |
| CEAB (proposed) | 0.187 ± 0.004 | 0.207 ± 0.005 | 0.204 ± 0.004 |

## All strategies — 99th-pct access delay (ms)

| Strategy | S1 (N=5) | S2 (N=20) | S3 (N=50) |
|---|---|---|---|
| BEB (802.11) | 15.39 ± 0.43 | 127.05 ± 2.74 | 304.04 ± 5.51 |
| Constant W=64 | 5.75 ± 0.06 | 33.65 ± 0.22 | 82.47 ± 0.49 |
| Linear | 12.39 ± 0.26 | 64.08 ± 0.68 | 100.89 ± 0.85 |
| Fibonacci | 13.17 ± 0.22 | 98.28 ± 5.27 | 190.57 ± 3.97 |
| Quadratic | 17.88 ± 0.23 | 108.22 ± 3.04 | 265.36 ± 5.20 |
| MILD | 42.67 ± 10.65 | 27.33 ± 0.71 | 63.34 ± 0.43 |
| EIED | 16.35 ± 0.53 | 138.24 ± 3.84 | 292.89 ± 7.47 |
| Idle Sense | 5.90 ± 0.08 | 26.90 ± 0.43 | 70.99 ± 1.10 |
| CEAB (proposed) | 5.99 ± 0.07 | 25.63 ± 0.27 | 64.74 ± 0.89 |

## All strategies — Short-term Jain fairness (100 ms)

| Strategy | S1 (N=5) | S2 (N=20) | S3 (N=50) |
|---|---|---|---|
| BEB (802.11) | 0.917 ± 0.004 | 0.599 ± 0.008 | 0.397 ± 0.006 |
| Constant W=64 | 0.993 ± 0.001 | 0.946 ± 0.001 | 0.751 ± 0.006 |
| Linear | 0.970 ± 0.003 | 0.806 ± 0.005 | 0.598 ± 0.006 |
| Fibonacci | 0.957 ± 0.007 | 0.690 ± 0.007 | 0.481 ± 0.004 |
| Quadratic | 0.923 ± 0.008 | 0.673 ± 0.008 | 0.475 ± 0.005 |
| MILD | 0.295 ± 0.231 | 0.959 ± 0.002 | 0.915 ± 0.002 |
| EIED | 0.832 ± 0.016 | 0.425 ± 0.007 | 0.274 ± 0.004 |
| Idle Sense | 0.993 ± 0.001 | 0.963 ± 0.002 | 0.899 ± 0.002 |
| CEAB (proposed) | 0.993 ± 0.000 | 0.965 ± 0.001 | 0.910 ± 0.002 |
