# Frozen offset bank cost observation - run 03

This report summarizes one fresh-process observation. Timings are descriptive, not a matched benchmark or native-throughput comparison. It makes no performance-ratio or 80% claim.

Candidate JSONL SHA-256: `42e015482fbf12e30f322a92b07b55be8a78cbd824ef09b13453bab43d900e17`  
Frozen CSV SHA-256: `fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723`  
Receipt walltime: 27.186356 s; child exit 0; timed out: False; provenance unchanged: True

Identity checks passed: 160 ordered IDs match the frozen CSV, the candidate hash matches the receipt, the frozen CSV hash matches the pre-run receipt hash, and every query is marked `exact_control_offset`.

Timing aggregates use nanoseconds. P95 uses the nearest-rank method; medians use the standard midpoint convention. Missing values are counted and omitted from timing aggregates.

| Group | Count | Resolved | Candidate blocked | Telemetry blocked | Distance ns (sum / median / p95; missing) | Evaluate ns (sum / median / p95; missing) | Normal ns (sum / median / p95; missing) | Sum calls / nodes / visits / excluded slabs (missing each) |
|---|---:|---:|---:|---:|---|---|---|---|
| All | 160 | 160 | 0 | 9 | 24945547355 / 3150849.5 / 423480069; 0 | 417215192 / 2208650.0 / 4852100; 8 | 790606753 / 4992199 / 7301800; 9 | 4104 (0 missing) / 40758 (0 missing) / 16712 (0 missing) / 134 (0 missing) |

### By disposition

| Disposition | Count | Resolved | Candidate blocked | Telemetry blocked | Distance ns (sum / median / p95; missing) | Evaluate ns (sum / median / p95; missing) | Normal ns (sum / median / p95; missing) | Sum calls / nodes / visits / excluded slabs (missing each) |
|---|---:|---:|---:|---:|---|---|---|---|
| hit | 69 | 69 | 0 | 0 | 24446837799 / 236340183 / 1765711170; 0 | 160735495 / 1998000 / 4754800; 0 | 352751677 / 4992199 / 7251100; 0 | 3969 (0 missing) / 39406 (0 missing) / 16410 (0 missing) / 95 (0 missing) |
| no_hit | 91 | 91 | 0 | 9 | 498709556 / 2500 / 44868796; 0 | 256479697 / 2596500 / 4879400; 8 | 437855076 / 5000350.5 / 7301800; 9 | 135 (0 missing) / 1352 (0 missing) / 302 (0 missing) / 39 (0 missing) |

### By geometry

| Geometry | Count | Resolved | Candidate blocked | Telemetry blocked | Distance ns (sum / median / p95; missing) | Evaluate ns (sum / median / p95; missing) | Normal ns (sum / median / p95; missing) | Sum calls / nodes / visits / excluded slabs (missing each) |
|---|---:|---:|---:|---:|---|---|---|---|
| torus | 151 | 151 | 0 | 1 | 24325275182 / 4600 / 487371955; 0 | 417038892 / 2237600 / 4852100; 0 | 789022053 / 5005150.0 / 7301800; 1 | 3947 (0 missing) / 34253 (0 missing) / 16528 (0 missing) / 107 (0 missing) |
| torus_rigid | 1 | 1 | 0 | 0 | 286631104 / 286631104 / 286631104; 0 | 176300 / 176300 / 176300; 0 | 1584700 / 1584700 / 1584700; 0 | 60 (0 missing) / 5228 (0 missing) / 184 (0 missing) / 0 (0 missing) |
| wistell_coil031 | 8 | 8 | 0 | 8 | 333641069 / 39049046.5 / 74327593; 0 | None / None / None; 8 | None / None / None; 8 | 97 (0 missing) / 1277 (0 missing) / 0 (0 missing) / 27 (0 missing) |

### By category

| Category | Count | Resolved | Candidate blocked | Telemetry blocked | Distance ns (sum / median / p95; missing) | Evaluate ns (sum / median / p95; missing) | Normal ns (sum / median / p95; missing) | Sum calls / nodes / visits / excluded slabs (missing each) |
|---|---:|---:|---:|---:|---|---|---|---|
| clear_miss | 1 | 1 | 0 | 1 | 8800 / 8800 / 8800; 0 | 37977502 / 37977502 / 37977502; 0 | None / None / None; 1 | 0 (0 missing) / 0 (0 missing) / 0 (0 missing) / 0 (0 missing) |
| coincident_in | 1 | 1 | 0 | 0 | 276424004 / 276424004 / 276424004; 0 | 711400 / 711400 / 711400; 0 | 4031000 / 4031000 / 4031000; 0 | 58 (0 missing) / 459 (0 missing) / 93 (0 missing) / 1 (0 missing) |
| coincident_out | 1 | 1 | 0 | 0 | 1828800 / 1828800 / 1828800; 0 | 701300 / 701300 / 701300; 0 | 3499300 / 3499300 / 3499300; 0 | 2 (0 missing) / 2 (0 missing) / 0 (0 missing) / 1 (0 missing) |
| competing_roots | 1 | 1 | 0 | 0 | 2084616340 / 2084616340 / 2084616340; 0 | 4484901 / 4484901 / 4484901; 0 | 7554402 / 7554402 / 7554402; 0 | 60 (0 missing) / 4159 (0 missing) / 181 (0 missing) / 0 (0 missing) |
| direction_scaling | 2 | 2 | 0 | 0 | 3523969441 / 1761984720.5 / 1765711170; 0 | 1300300 / 650150.0 / 652400; 0 | 7034901 / 3517450.5 / 3548201; 0 | 120 (0 missing) / 7936 (0 missing) / 316 (0 missing) / 0 (0 missing) |
| grazing | 1 | 1 | 0 | 0 | 3300 / 3300 / 3300; 0 | 1159400 / 1159400 / 1159400; 0 | 3652801 / 3652801 / 3652801; 0 | 0 (0 missing) / 0 (0 missing) / 0 (0 missing) / 0 (0 missing) |
| heldout_unique | 136 | 136 | 0 | 0 | 14437228104 / 3400.0 / 338395268; 0 | 363812388 / 2536700.0 / 4852100; 0 | 734491845 / 5282400.0 / 7301800; 0 | 3388 (0 missing) / 13191 (0 missing) / 14246 (0 missing) / 99 (0 missing) |
| inside | 1 | 1 | 0 | 0 | 50483702 / 50483702 / 50483702; 0 | 723200 / 723200 / 723200; 0 | 3646600 / 3646600 / 3646600; 0 | 46 (0 missing) / 46 (0 missing) / 158 (0 missing) / 1 (0 missing) |
| near_entry_002 | 1 | 1 | 0 | 0 | 250238512 / 250238512 / 250238512; 0 | 637900 / 637900 / 637900; 0 | 3470101 / 3470101 / 3470101; 0 | 60 (0 missing) / 399 (0 missing) / 160 (0 missing) / 0 (0 missing) |
| near_entry_502 | 1 | 1 | 0 | 0 | 1812381393 / 1812381393 / 1812381393; 0 | 641500 / 641500 / 641500; 0 | 3539201 / 3539201 / 3539201; 0 | 60 (0 missing) / 4000 (0 missing) / 158 (0 missing) / 0 (0 missing) |
| near_tangent_minus | 1 | 1 | 0 | 0 | 108421501 / 108421501 / 108421501; 0 | 1176001 / 1176001 / 1176001; 0 | 3097800 / 3097800 / 3097800; 0 | 93 (0 missing) / 93 (0 missing) / 1058 (0 missing) / 5 (0 missing) |
| near_tangent_plus | 1 | 1 | 0 | 0 | 4600 / 4600 / 4600; 0 | 1161100 / 1161100 / 1161100; 0 | 3658800 / 3658800 / 3658800; 0 | 0 (0 missing) / 0 (0 missing) / 0 (0 missing) / 0 (0 missing) |
| rigid_transform | 1 | 1 | 0 | 0 | 286631104 / 286631104 / 286631104; 0 | 176300 / 176300 / 176300; 0 | 1584700 / 1584700 / 1584700; 0 | 60 (0 missing) / 5228 (0 missing) / 184 (0 missing) / 0 (0 missing) |
| seam | 1 | 1 | 0 | 0 | 16300 / 16300 / 16300; 0 | 663000 / 663000 / 663000; 0 | 4573901 / 4573901 / 4573901; 0 | 0 (0 missing) / 0 (0 missing) / 0 (0 missing) / 0 (0 missing) |
| tangent | 1 | 1 | 0 | 0 | 3700 / 3700 / 3700; 0 | 1172600 / 1172600 / 1172600; 0 | 3260401 / 3260401 / 3260401; 0 | 0 (0 missing) / 0 (0 missing) / 0 (0 missing) / 0 (0 missing) |
| transverse | 1 | 1 | 0 | 0 | 1779646685 / 1779646685 / 1779646685; 0 | 716400 / 716400 / 716400; 0 | 3511000 / 3511000 / 3511000; 0 | 60 (0 missing) / 3968 (0 missing) / 158 (0 missing) / 0 (0 missing) |
| wistell_coil031_real | 8 | 8 | 0 | 8 | 333641069 / 39049046.5 / 74327593; 0 | None / None / None; 8 | None / None / None; 8 | 97 (0 missing) / 1277 (0 missing) / 0 (0 missing) / 27 (0 missing) |

### Telemetry-blocked rows

| ID | Error |
|---|---|
| a00 | Exact-control offset normal has no certified unique projection |
| w0 | Exact-control offset normal minimum budget exhausted |
| w1 | Exact-control offset normal minimum budget exhausted |
| w2 | Exact-control offset normal minimum budget exhausted |
| w3 | Exact-control offset normal minimum budget exhausted |
| w4 | Exact-control offset normal minimum budget exhausted |
| w5 | Exact-control offset normal minimum budget exhausted |
| w6 | Exact-control offset normal minimum budget exhausted |
| w7 | Exact-control offset normal minimum budget exhausted |

Source files were read only; this report uses the retained JSONL, receipt, and frozen CSV.
