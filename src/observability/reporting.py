from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline evidence report."""
    text = "\n".join([
        "# Phase 1 Baseline Report", "", "## Source", f"- Source: {source_summary.get('source', 'Crossref')}",
        f"- Records: {source_summary.get('records', 0)}", "", "## Evaluation",
        f"- Samples: {metrics.get('samples', 0)}", f"- Retrieval hit rate: {metrics.get('retrieval_hit_rate', 0):.3f}",
        f"- Mean token F1: {metrics.get('mean_token_f1', 0):.3f}", f"- Judge accuracy: {metrics.get('judge_accuracy', 0):.3f}",
        "", "## Data Quality", f"- Quality gate: **{quality.get('success', False)}**",
        f"- Rows: {quality.get('row_count', 0)}", "", "## Freshness",
        f"- Latest published: {freshness.get('latest_published')}", f"- Stale rows: {freshness.get('stale_rows', 0)}",
        f"- Freshness SLA: **{freshness.get('is_fresh', False)}**", "",
    ])
    write_text(report_path, text)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a three-state comparison report for corruption and repair."""
    def metric_row(label: str, key: str) -> str:
        return f"| {label} | {baseline_metrics.get(key, 0):.3f} | {corrupted_metrics.get(key, 0):.3f} | {repaired_metrics.get(key, 0):.3f} |"

    text = "\n".join([
        "# Corruption and Repair Report", "", "| Metric | Baseline | Corrupted | Repaired |", "|---|---:|---:|---:|",
        metric_row("Retrieval hit rate", "retrieval_hit_rate"), metric_row("Mean token F1", "mean_token_f1"),
        metric_row("Judge accuracy", "judge_accuracy"), metric_row("Mean judge score", "mean_judge_score"), "",
        "## Quality and Freshness", "", "| State | Quality gate | Freshness | Stale rows |", "|---|---|---|---:|",
        f"| Corrupted | {corrupted_quality.get('success', False)} | {corrupted_freshness.get('is_fresh', False)} | {corrupted_freshness.get('stale_rows', 0)} |",
        f"| Repaired | {repaired_quality.get('success', False)} | {repaired_freshness.get('is_fresh', False)} | {repaired_freshness.get('stale_rows', 0)} |", "",
        "The repaired state is rebuilt from the preserved raw snapshot, making the repair repeatable and independent of the corrupted dataframe.", "",
    ])
    write_text(report_path, text)
