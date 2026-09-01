# Local stellarator model catalog

Generated `2026-09-01T00:14:42-04:00` from an explicit local campaign index.
No source geometry was copied. Paths and hashes describe local-only inputs;
`public fixture = unknown` means redistribution was not established.

| Configuration | Component | Class | NFP read from file | Status | SHA-256 | Bytes | Public fixture |
|---|---|---|---:|---|---|---:|---|
| WISTELL-D | plasma | stellarator reactor study | 4 | PASS_SINGLE_CHART | `9231969001203a81` | 4626928 | unknown |
| WISTELL-D | coil | stellarator reactor study | 4 | PASS_SINGLE_CHART | `7748369407d28a70` | 1737790 | unknown |
| FPP11.5 free boundary | plasma | stellarator reactor study | 4 | REJECT_THETA_FOLD | `56fa6ce0747b4c95` | 50246960 | unknown |
| FPP11.5 free boundary | coil | stellarator reactor study | 4 | REJECT_THETA_FOLD | `7da3081cb401ebef` | 3712501 | unknown |
| QA nfp=1 | plasma | QA | 1 | REJECT_THETA_FOLD | `ea02a98853b53ed9` | 609044 | unknown |
| QA nfp=1 | coil | QA | 1 | REJECT_THETA_FOLD | `571e9a2517c9fa03` | 180379 | unknown |
| QA nfp=2 | plasma | QA | 2 | PASS_SINGLE_CHART | `2ab476162d895188` | 1091412 | unknown |
| QA nfp=2 | coil | QA | 2 | PASS_SINGLE_CHART | `a80f45e19eca5791` | 216481 | unknown |
| QA nfp=3 | plasma | QA | 3 | PASS_SINGLE_CHART | `2a4621dbda843a78` | 1091412 | unknown |
| QA nfp=3 | coil | QA | 3 | PASS_SINGLE_CHART | `52e53fdd9ff1be36` | 324715 | unknown |
| QA nfp=4 | plasma | QA | 4 | PASS_SINGLE_CHART | `705abf9e08291b2b` | 1091412 | unknown |
| QA nfp=4 | coil | QA | 4 | PASS_SINGLE_CHART | `6aebac4d8f0cd972` | 841211 | unknown |
| QA nfp=5 | plasma | QA | 5 | PASS_SINGLE_CHART | `23ed88623bbb54f0` | 1091412 | unknown |
| QA nfp=5 | coil | QA | 5 | PASS_SINGLE_CHART | `d955cfa89f436725` | 360749 | unknown |
| QA nfp=6 | plasma | QA | 6 | PASS_SINGLE_CHART | `9bc742fc62045afb` | 1091412 | unknown |
| QA nfp=6 | coil | QA | 6 | PASS_SINGLE_CHART | `2cf073043952a00c` | 432931 | unknown |
| QA nfp=7 | plasma | QA | 7 | PASS_SINGLE_CHART | `a8a3c3509dbb7c18` | 1091412 | unknown |
| QA nfp=7 | coil | QA | 7 | PASS_SINGLE_CHART | `1d9b04075297ea87` | 505099 | unknown |
| Landreman-Paul QA | plasma | QA | 2 | PASS_SINGLE_CHART | `ba8dcfaf18d27c99` | 548772 | unknown |
| Landreman-Paul QA | coil | QA | 2 | PASS_SINGLE_CHART | `09ca0a1e26f127a2` | 114263 | unknown |
| QH simple scaled | plasma | QH | 4 | PASS_SINGLE_CHART | `c80125a1cd1073e8` | 1703508 | unknown |
| n3are R7.75 B5.7 | plasma | stellarator equilibrium | 3 | REJECT_THETA_FOLD | `78ca93ea25774b12` | 3979400 | unknown |
| NCSX C09R00 | plasma | QA | 3 | REJECT_THETA_FOLD | `ecfdc7241f5bece4` | 1352208 | unknown |
| NCSX C09R00 | coil | QA | 3 | REJECT_THETA_FOLD | `f151d4f4a1f02067` | 1708219 | unknown |
| HELIAS 5B-like | plasma | HELIAS / QI-like | 5 | PASS_SINGLE_CHART | `1460ec2a789f0ba4` | 9381888 | unknown |
| HELIAS 5B-like | coil | HELIAS / QI-like | 5 | PASS_SINGLE_CHART | `d79736fcd71ad7af` | 471763 | unknown |
| W7-X standard | plasma | HELIAS / QI-like | 5 | REJECT_THETA_FOLD | `336a41939e881127` | 3906480 | unknown |
| W7-X standard | coil | HELIAS / QI-like | 5 | REJECT_THETA_FOLD | `1395559ff04a45fa` | 652993 | unknown |

## Qualification boundary

The statuses above are retained prior single-chart admissibility results,
not dual-track performance qualification. Coil-file NFP remains null when
the coil file does not declare periods/NFP; the paired VMEC record supplies
the independently read equilibrium NFP. License-unclear files remain local.
