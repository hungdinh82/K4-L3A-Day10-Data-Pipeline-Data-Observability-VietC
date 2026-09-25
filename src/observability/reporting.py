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
    """TODO(student): viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines = [
        "# Phase 1 Report — Baseline Pipeline",
        "",
        "## Source",
        "",
        f"- Source: `{source_summary.get('source', 'Crossref')}`",
        f"- Records loaded: **{source_summary.get('records_loaded', 0)}**",
        f"- Run date: `{source_summary.get('run_date', '')}`",
        "",
        "## Baseline Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        lines.append(f"| `{key}` | {metrics.get(key, 'N/A')} |")
    lines.extend(
        [
            "",
            "## Data Quality",
            "",
            f"- Quality gate: **{'PASS' if quality.get('success') else 'FAIL'}**",
            f"- Rows checked: **{quality.get('row_count', 0)}**",
            f"- Freshness: **{'FRESH' if freshness.get('is_fresh') else 'STALE'}**",
            f"- Stale rows: **{freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}**",
            f"- Latest published: `{freshness.get('latest_published')}`",
            "",
            "## Conclusion",
            "",
            "The baseline pipeline completed ingestion, cleaning, vector indexing, evaluation, and observability checks on the clean corpus.",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))


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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    rows = [
        ("retrieval_hit_rate", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("mean_token_f1", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("judge_accuracy", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("mean_judge_score", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("quality_success", corrupted_quality, corrupted_quality, repaired_quality),
        ("freshness", corrupted_freshness, corrupted_freshness, repaired_freshness),
    ]
    lines = [
        "# Corruption and Repair Report",
        "",
        "| Signal | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, baseline, corrupted, repaired in rows:
        lines.append(f"| `{key}` | {baseline.get(key, baseline.get('success', baseline.get('is_fresh', 'N/A')))} | {corrupted.get(key, corrupted.get('success', corrupted.get('is_fresh', 'N/A')))} | {repaired.get(key, repaired.get('success', repaired.get('is_fresh', 'N/A')))} |")
    lines.append("")
    write_text(report_path, "\n".join(lines))
