# Comparison: ab-base -> ab-adapter

| Dataset | Harness | Role | Paired (dropped) | Base pass@1 | Candidate pass@1 | Gain | New / lost | p (sign test) | Tool-call ratio | Output-token ratio | Latency ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| smoke | pi | untrained | 12 (0) | 100.0% | 75.0% | -25.0% | 0 / 3 | 0.2500 | 0.71 | 0.78 | 1.03 |

Ratios are candidate / base over tasks both solved. Gain in a `transfer` row is the transfer gain.
p-values are per cell and not corrected for multiple comparisons.
