from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import html
import re
from pathlib import Path
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


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
    """Parse Crossref records while tolerating optional and varied fields."""
    def clean(value: object) -> str:
        text = html.unescape(str(value or ""))
        return normalize_whitespace(re.sub(r"<[^>]+>", " ", text))

    def first(value: object) -> str:
        if isinstance(value, list):
            return clean(value[0]) if value else ""
        return clean(value)

    def date_value(item: dict, *keys: str) -> str:
        for key in keys:
            parts = item.get(key, {}).get("date-parts", [])
            if parts and parts[0]:
                values = parts[0]
                try:
                    year = int(values[0])
                    month = int(values[1]) if len(values) > 1 else 1
                    day = int(values[2]) if len(values) > 2 else 1
                    return date(year, month, day).isoformat()
                except (TypeError, ValueError):
                    continue
        return ""

    records: list[PaperRecord] = []
    seen: set[str] = set()
    for item in payload.get("message", {}).get("items", []):
        paper_id = clean(item.get("DOI") or item.get("URL"))
        title = first(item.get("title"))
        summary = clean(item.get("abstract"))
        if not paper_id or not title or not summary or paper_id.lower() in seen:
            continue
        authors = [
            clean(" ".join(part for part in (author.get("given"), author.get("family")) if part))
            for author in item.get("author", [])
        ]
        authors = [author for author in authors if author]
        categories = [clean(value) for value in item.get("subject", []) if clean(value)]
        links = item.get("link") or []
        pdf_url = next((link.get("URL", "") for link in links if link.get("content-type") == "application/pdf"), "")
        abs_url = clean(item.get("URL") or item.get("resource", {}).get("primary.URL"))
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "Unknown",
            published=date_value(item, "published", "published-print", "published-online", "issued"),
            updated=date_value(item, "updated", "created"),
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=clean(item.get("comment")),
        ))
        seen.add(paper_id.lower())
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data, preserving the response and supporting offline runs."""
    response_path = settings.paths.raw_api_response
    payload = None
    if not settings.refresh_source and response_path.exists():
        payload = read_json(response_path)
    else:
        params = {"query": settings.source_query, "filter": settings.source_filter, "rows": settings.max_results}
        try:
            for attempt in range(3):
                response = requests.get("https://api.crossref.org/works", params=params, timeout=30)
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    payload = response.json()
                    break
                if attempt < 2:
                    time.sleep(2 ** attempt)
        except requests.RequestException:
            payload = None
        if payload is not None:
            write_json(response_path, payload)
        elif response_path.exists():
            payload = read_json(response_path)
        else:
            raise RuntimeError("Crossref is unavailable and no offline snapshot exists.")

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [record.__dict__ for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the normalized raw-record snapshot into typed records."""
    payload = read_json(path)
    if isinstance(payload, dict):
        return parse_crossref_payload(payload)
    return [PaperRecord(**item) for item in payload]
