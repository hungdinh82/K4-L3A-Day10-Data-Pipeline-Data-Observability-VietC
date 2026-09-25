# Corruption and Repair Report

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 1.000 | 0.500 | 1.000 |
| Mean token F1 | 1.000 | 0.674 | 1.000 |
| Judge accuracy | 1.000 | 0.700 | 1.000 |
| Mean judge score | 5.000 | 3.800 | 5.000 |

## Quality and Freshness

| State | Quality gate | Freshness | Stale rows |
|---|---|---|---:|
| Corrupted | False | True | 3 |
| Repaired | True | True | 1 |

The repaired state is rebuilt from the preserved raw snapshot, making the repair repeatable and independent of the corrupted dataframe.
