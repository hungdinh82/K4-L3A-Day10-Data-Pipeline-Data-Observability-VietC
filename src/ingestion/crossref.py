from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import unescape
import json
from pathlib import Path
import re

import requests

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref payload into PaperRecord objects.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    records: list[PaperRecord] = []
    for item in payload.get("message", {}).get("items", []):
        paper_id = str(item.get("DOI") or item.get("doi") or "").strip().lower()
        title = _clean_text(item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", ""))
        summary = _clean_text(item.get("abstract", ""))
        if not paper_id or not title:
            continue

        authors = []
        for author in item.get("author", []) or []:
            name = " ".join(filter(None, [author.get("given", ""), author.get("family", "")]))
            if name:
                authors.append(_clean_text(name))
        categories = [_clean_text(value) for value in item.get("subject", []) or [] if _clean_text(value)]
        published = _parse_date(item.get("published") or item.get("published-print") or item.get("created"))
        updated = _parse_date(item.get("updated") or item.get("created"))
        url = str(item.get("URL") or f"https://doi.org/{paper_id}").strip()
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=str(item.get("link", [{}])[0].get("URL", url)) if item.get("link") else url,
                comment=_clean_text(item.get("comment", "")),
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch source data, preserve the raw response, and parse records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    if not settings.refresh_source and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    payload = None
    try:
        response = requests.get(settings.source_api, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        if not settings.paths.raw_api_response.exists():
            raise
        payload = json.loads(settings.paths.raw_api_response.read_text(encoding="utf-8"))

    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.raw_api_response.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    records = parse_crossref_payload(payload)
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.raw_records_json.write_text(
        json.dumps([record.__dict__ for record in records], indent=2), encoding="utf-8"
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a JSON snapshot and map it to PaperRecord objects."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in payload]


def _clean_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, dict):
        parts = (value.get("date-parts") or [[]])[0]
        if parts:
            year, month = parts[0], parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        value = value.get("date-time", "")
    return str(value).replace("Z", "+00:00")[:10]
