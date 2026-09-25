from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into an embedding-ready dataframe.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    rows = []
    run_day = run_date.date()
    for record in records:
        title = " ".join(str(record.title).split())
        summary = " ".join(str(record.summary).split())
        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        if not record.paper_id or not title or pd.isna(published):
            continue
        authors = ", ".join(" ".join(str(value).split()) for value in record.authors if value)
        categories = ", ".join(" ".join(str(value).split()) for value in record.categories if value)
        published_date = published.date()
        age_days = (run_day - published_date).days
        rows.append(
            {
                "paper_id": str(record.paper_id).strip().lower(),
                "title": title,
                "summary": summary,
                "authors_joined": authors,
                "categories_joined": categories,
                "primary_category": record.primary_category,
                "published": published_date.isoformat(),
                "updated": record.updated,
                "age_days": age_days,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "summary_chars": len(summary),
                "text_for_embedding": (
                    f"Title: {title}\nAuthors: {authors}\nPublished: {published_date.isoformat()}\n"
                    f"Categories: {categories}\nSummary: {summary}"
                ),
            }
        )
    df = pd.DataFrame(rows).drop_duplicates(subset=["paper_id"], keep="first")
    if not df.empty:
        df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
