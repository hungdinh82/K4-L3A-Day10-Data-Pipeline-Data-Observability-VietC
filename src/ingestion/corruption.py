from __future__ import annotations

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply deterministic corruption mutations and record their impact."""
    corrupted = df.copy(deep=True)
    log = []
    drop_count = max(1, len(corrupted) // 5)
    latest = corrupted.sort_values("published", ascending=False).index[:drop_count]
    corrupted = corrupted.drop(latest).reset_index(drop=True)
    log.append({"type": "drop_latest_records", "rows_affected": drop_count})

    if not corrupted.empty:
        blank_index = corrupted.index[::7]
        corrupted.loc[blank_index, "summary"] = ""
        log.append({"type": "blank_summary", "rows_affected": len(blank_index)})
        noise_index = corrupted.index[1::6]
        corrupted.loc[noise_index, "summary"] = corrupted.loc[noise_index, "summary"].astype(str) + " [NOISE @@###]"
        log.append({"type": "inject_noise", "rows_affected": len(noise_index)})
        title_index = corrupted.index[2::8]
        corrupted.loc[title_index, "title"] = corrupted.loc[title_index, "title"].astype(str).str.slice(0, 7)
        log.append({"type": "truncate_title", "rows_affected": len(title_index)})
        stale_index = corrupted.index[3::9]
        corrupted.loc[stale_index, "published"] = "2024-01-01"
        corrupted.loc[stale_index, "age_days"] = corrupted.loc[stale_index, "age_days"] + 365
        log.append({"type": "stale_date", "rows_affected": len(stale_index)})
        duplicate = corrupted.iloc[[0]].copy()
        corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
        log.append({"type": "duplicate_rows", "rows_affected": 1})

    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"].astype(str)
        + "\nAuthors: " + corrupted["authors_joined"].astype(str)
        + "\nPublished: " + corrupted["published"].astype(str)
        + "\nCategories: " + corrupted["categories_joined"].astype(str)
        + "\nSummary: " + corrupted["summary"].astype(str)
    )
    write_json(output_log_path, {"mutations": log, "original_rows": len(df), "corrupted_rows": len(corrupted)})
    return corrupted
