# Phase 1 Report — Baseline Pipeline

## Source

- Source: `https://api.crossref.org/works`
- Records loaded: **24**
- Run date: `2026-09-25T07:45:00.816438+00:00`

## Baseline Metrics

| Metric | Value |
| --- | ---: |
| `samples` | 5 |
| `retrieval_hit_rate` | 1.0 |
| `mean_token_f1` | 0.7157894736842105 |
| `judge_accuracy` | 0.6 |
| `mean_judge_score` | 3.8 |

## Data Quality

- Quality gate: **PASS**
- Rows checked: **24**
- Freshness: **FRESH**
- Stale rows: **1 / 24**
- Latest published: `2026-07-22`

## Conclusion

The baseline pipeline completed ingestion, cleaning, vector indexing, evaluation, and observability checks on the clean corpus.
