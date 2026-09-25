from __future__ import annotations

from datetime import UTC, datetime
import re

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import compact_join, normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
   """Normalize raw papers into deterministic, embedding-ready rows."""
   run_timestamp = pd.Timestamp(run_date)
   if run_timestamp.tzinfo is None:
      run_timestamp = run_timestamp.tz_localize(UTC)
   rows = []
   for record in records:
      title = normalize_whitespace(re.sub(r"<[^>]+>", " ", record.title or ""))
      summary = normalize_whitespace(re.sub(r"<[^>]+>", " ", record.summary or ""))
      published = pd.to_datetime(record.published, errors="coerce", utc=True)
      updated = pd.to_datetime(record.updated, errors="coerce", utc=True)
      if not record.paper_id or not title or not summary or pd.isna(published):
         continue
      authors = [normalize_whitespace(value) for value in record.authors if normalize_whitespace(value)]
      categories = [normalize_whitespace(value) for value in record.categories if normalize_whitespace(value)]
      published_text = published.date().isoformat()
      updated_text = updated.date().isoformat() if not pd.isna(updated) else published_text
      age_days = max(0, (run_timestamp - published).days)
      authors_joined = compact_join(authors)
      categories_joined = compact_join(categories)
      rows.append({
         "paper_id": normalize_whitespace(record.paper_id),
         "title": title,
         "summary": summary,
         "authors": authors,
         "categories": categories,
         "primary_category": normalize_whitespace(record.primary_category) or (categories[0] if categories else "Unknown"),
         "published": published_text,
         "updated": updated_text,
         "abs_url": record.abs_url or "",
         "pdf_url": record.pdf_url or "",
         "comment": normalize_whitespace(record.comment or ""),
         "authors_joined": authors_joined,
         "categories_joined": categories_joined,
         "summary_chars": len(summary),
         "age_days": age_days,
         "text_for_embedding": (
            f"Title: {title}\nAuthors: {authors_joined or 'Unknown'}\n"
            f"Published: {published_text}\nCategories: {categories_joined or 'Unknown'}\n"
            f"Summary: {summary}"
         ),
      })
   result = pd.DataFrame(rows)
   if result.empty:
      return result
   result = result.drop_duplicates("paper_id", keep="first")
   return result.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
