# Corruption and Repair Report

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0 | 0.0 | 1.0 |
| `mean_token_f1` | 0.7157894736842105 | 0.4 | 0.7157894736842105 |
| `judge_accuracy` | 0.6 | 0.4 | 0.6 |
| `mean_judge_score` | 3.8 | 2.6 | 3.6 |
| `quality_success` | True | False | True |
| `freshness` | True | False | True |

## Interpretation

- Corrupted data is intentionally evaluated with the same benchmark as baseline.
- Repaired data is rebuilt from the raw snapshot, then re-indexed and re-evaluated.
- A successful repair requires the quality and freshness gates to pass again.
