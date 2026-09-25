from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report


def main() -> None:
    """Run the complete clean-data baseline pipeline."""
    settings = load_settings()
    records = (
        fetch_source_records(settings)
        if settings.refresh_source or not settings.paths.raw_records_json.exists()
        else load_raw_records(settings.paths.raw_records_json)
    )
    dataframe = build_clean_dataframe(records, datetime.now(UTC))
    write_csv(dataframe, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, dataframe.to_dict(orient="records"))

    quality = run_data_quality_checks(dataframe, settings, "baseline")
    freshness = build_freshness_report(dataframe, settings, settings.paths.freshness_report)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(dataframe, settings.paths.eval_testset)

    from retrieval.index import LocalEmbeddingIndex
    from evaluation.metrics import evaluate_pipeline

    index = LocalEmbeddingIndex.build(dataframe, settings, settings.paths.embeddings_json)
    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    generate_phase1_report(
        settings.paths.baseline_report,
        {"source": settings.source_api, "records": len(records)},
        bundle.summary,
        quality,
        freshness,
    )
    print(f"Baseline complete: {len(dataframe)} rows, hit rate={bundle.summary['retrieval_hit_rate']:.3f}")
