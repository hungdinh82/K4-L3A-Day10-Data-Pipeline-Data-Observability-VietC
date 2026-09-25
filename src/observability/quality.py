from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    """Run the GX quality gate and the freshness SLA check.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    validation_df = df.copy()
    # GX's not-null expectation treats an empty string as a value. Converting
    # blank required values to NA enforces the lab's "not null and not blank"
    # contract without changing the caller's dataframe.
    for column in ("paper_id", "title", "text_for_embedding"):
        if column in validation_df.columns:
            validation_df[column] = validation_df[column].replace(r"^\s*$", pd.NA, regex=True)

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": validation_df})

    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    suite = gx.ExpectationSuite(
        name=f"{safe_slug(report_name)}_quality_suite",
        expectations=expectations,
    )
    validation = batch.validate(suite, result_format="SUMMARY")
    gx_result = validation.to_json_dict()

    freshness_path = (
        settings.paths.freshness_report
        if report_name in {"baseline", "test"}
        else settings.paths.quality_dir / f"{safe_slug(report_name)}_freshness_report.json"
    )
    freshness = build_freshness_report(df, settings, freshness_path)
    gx_success = bool(gx_result.get("success", False))
    overall_success = gx_success and bool(freshness["is_fresh"])

    report: dict[str, Any] = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "freshness_success": freshness["is_fresh"],
        "statistics": gx_result.get("statistics", {}),
        "results": gx_result.get("results", []),
        "freshness": freshness,
    }

    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"
    write_json(report_path, report)
    return report


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path,
) -> dict[str, Any]:
    """Build and persist a publication freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    published = (
        pd.to_datetime(df["published"], errors="coerce", utc=True)
        if "published" in df.columns
        else pd.Series(dtype="datetime64[ns, UTC]")
    )
    ages = (
        pd.to_numeric(df["age_days"], errors="coerce")
        if "age_days" in df.columns
        else pd.Series(index=df.index, dtype="float64")
    )
    stale_mask = ages.gt(settings.freshness_threshold_days)
    total_rows = int(len(df))
    stale_rows = int(stale_mask.sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0

    valid_published = published.dropna()
    report: dict[str, Any] = {
        "freshness_threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "latest_published": (
            valid_published.max().date().isoformat() if not valid_published.empty else None
        ),
        "oldest_published": (
            valid_published.min().date().isoformat() if not valid_published.empty else None
        ),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": total_rows > 0 and stale_ratio <= 0.25,
    }
    write_json(report_path, report)
    return report
