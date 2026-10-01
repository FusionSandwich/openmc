# Bernstein prefix A/B - frozen offset bank

Not a native-throughput or transport benchmark and not an 80% claim. Root retains scientific interpretation and independent-oracle acceptance.

Clean aggregate uses runs 04/05, 10/11, and 12/13 as three sequential on/off pairs. Runs 06-09 are retained below but excluded because they overlapped an independent Fraction verifier and may be background-load-confounded.

Frozen CSV SHA-256: `fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723`. The binary, CSV, WISTELL fixture, offset engine sources, and frozen-bank source hashes match across all six clean receipts. Each run has 160 ordered IDs matching the CSV, and all non-timing query fields are identical across the three replicates within each variant.

| Run | Variant | Wall s | Sum distance ns | Median hit ns | Median no-hit ns | Telemetry failures | Bernstein certified true | Missing distance/evaluate/normal timing |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 04 | on | 1.385988 | 843030202 | 8434400 | 2500 | 9 | 66 | 0/0/9 |
| 05 | off | 3.988863 | 3452209311 | 35858401 | 2000 | 9 | 0 | 0/0/9 |
| 10 | on | 1.797642 | 866762204 | 8381900 | 2200 | 9 | 66 | 0/0/9 |
| 11 | off | 4.004265 | 3489909531 | 36276699 | 1900 | 9 | 0 | 0/0/9 |
| 12 | on | 1.460061 | 887151978 | 8746600 | 2500 | 9 | 66 | 0/0/9 |
| 13 | off | 4.105158 | 3580167041 | 36055399 | 2500 | 9 | 0 | 0/0/9 |

## Clean three-pair summary

- bernstein_on: per-run summed distance time mean 865648128.000 ns, median 866762204.000 ns; child wall mean 1.547897 s, median 1.460061 s; Bernstein-certified rows total 198.
- bernstein_off: per-run summed distance time mean 3507428627.667 ns, median 3489909531.000 ns; child wall mean 4.032762 s, median 4.004265 s; Bernstein-certified rows total 0.

Paired ratio is on divided by off; greater than 1 indicates a larger observed value in on runs.

- 04/05: summed distance-time ratio 0.244200; child-walltime ratio 0.347464.
- 10/11: summed distance-time ratio 0.248362; child-walltime ratio 0.448932.
- 12/13: summed distance-time ratio 0.247796; child-walltime ratio 0.355665.
- Paired ratios: distance-time mean 0.246786, median 0.247796; walltime mean 0.384020, median 0.355665.

## Background-confounded observations (excluded from clean aggregate)

| Run | Variant | Wall s | Sum distance ns | Bernstein certified true |
|---|---|---:|---:|---:|
| 06 | on | 1.803754 | 841958228 | 66 |
| 07 | off | 4.151657 | 3613611428 | 0 |
| 08 | on | 1.395308 | 870451185 | 66 |
| 09 | off | 4.199794 | 3663889446 | 0 |

## Telemetry failures

- Run 04: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 05: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 10: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 11: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 12: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 13: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 06: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 07: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 08: a00, w0, w1, w2, w3, w4, w5, w6, w7
- Run 09: a00, w0, w1, w2, w3, w4, w5, w6, w7

Historical run 03 summed candidate distance time was 24,945,547,355 ns; descriptive reference only. All timings are local fresh-process observations, not a matched native-throughput or transport result; no 80% claim is made. Scientific interpretation and independent-oracle acceptance remain with the root reviewer.
