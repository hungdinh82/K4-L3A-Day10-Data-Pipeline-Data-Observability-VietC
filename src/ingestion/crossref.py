from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
import re
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_WORKS_URL = "https://api.crossref.org/works"


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
    """Parse a Crossref API payload into normalized paper records.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    def clean_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            value = value[0] if value else ""
        # Crossref abstracts commonly contain JATS tags such as <jats:p>.
        without_tags = re.sub(r"<[^>]+>", " ", str(value))
        return normalize_whitespace(unescape(without_tags))

    def parse_date_parts(value: Any) -> str:
        if not isinstance(value, dict):
            return ""
        parts_groups = value.get("date-parts")
        if not isinstance(parts_groups, list) or not parts_groups:
            return ""
        parts = parts_groups[0]
        if not isinstance(parts, list) or not parts:
            return ""
        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            return ""

    def parse_timestamp_date(value: Any) -> str:
        if not isinstance(value, dict):
            return ""
        date_time = value.get("date-time")
        if isinstance(date_time, str) and date_time:
            # Crossref uses RFC 3339 timestamps; the first ten characters are
            # the ISO calendar date.
            try:
                return date.fromisoformat(date_time[:10]).isoformat()
            except ValueError:
                pass
        return parse_date_parts(value)

    if not isinstance(payload, dict):
        return []
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = clean_text(item.get("DOI")).lower()
        paper_id = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", paper_id)
        title = clean_text(item.get("title"))
        summary = clean_text(item.get("abstract"))

        # DOI and title are the minimum identity fields needed downstream.
        if not paper_id or not title:
            continue

        authors: list[str] = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            name = normalize_whitespace(
                " ".join(
                    part
                    for part in (str(author.get("given", "")), str(author.get("family", "")))
                    if part and part != "None"
                )
            )
            if name:
                authors.append(name)

        raw_subjects = item.get("subject", []) or []
        if isinstance(raw_subjects, str):
            raw_subjects = [raw_subjects]
        categories = [clean_text(subject) for subject in raw_subjects]
        categories = list(dict.fromkeys(category for category in categories if category))

        published = ""
        for field in ("published", "published-online", "published-print", "issued"):
            published = parse_date_parts(item.get(field))
            if published:
                break

        updated = ""
        for field in ("updated", "deposited", "created", "indexed"):
            updated = parse_timestamp_date(item.get(field))
            if updated:
                break
        updated = updated or published

        abs_url = clean_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = ""
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            content_type = str(link.get("content-type", "")).lower()
            candidate = clean_text(link.get("URL"))
            if candidate and ("pdf" in content_type or candidate.lower().endswith(".pdf")):
                pdf_url = candidate
                break
        pdf_url = pdf_url or abs_url

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
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, falling back to the saved response when offline.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "day10-data-observability-lab/0.1 (Crossref educational client)",
        }
    )

    payload: dict[str, Any]
    try:
        response = session.get(CROSSREF_WORKS_URL, params=params, timeout=(5, 30))
        response.raise_for_status()
        received = response.json()
        if not isinstance(received, dict) or not isinstance(received.get("message"), dict):
            raise ValueError("Crossref returned an invalid JSON payload.")
        payload = received
        # Preserve the API response only after it has been validated.
        write_json(settings.paths.raw_api_response, payload)
    except (requests.RequestException, ValueError):
        if not settings.paths.raw_api_response.exists():
            raise RuntimeError(
                "Crossref is unavailable and no local raw snapshot exists at "
                f"{settings.paths.raw_api_response}."
            )
        cached = read_json(settings.paths.raw_api_response)
        if not isinstance(cached, dict):
            raise RuntimeError("The local Crossref snapshot is not a JSON object.")
        payload = cached
    finally:
        session.close()

    records = parse_crossref_payload(payload)[: settings.max_results]
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a normalized JSON snapshot and map it to ``PaperRecord`` objects."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")

    records: list[PaperRecord] = []
    field_names = tuple(PaperRecord.__dataclass_fields__)
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} is not a JSON object.")
        missing = [name for name in field_names if name not in item]
        if missing:
            raise ValueError(f"Raw record at index {index} is missing fields: {', '.join(missing)}")
        values = {name: item[name] for name in field_names}
        if (
            values["authors"] is not None
            and not isinstance(values["authors"], list)
        ) or (
            values["categories"] is not None
            and not isinstance(values["categories"], list)
        ):
            raise ValueError(f"Raw record at index {index} has invalid list fields.")
        values["authors"] = list(values["authors"] or [])
        values["categories"] = list(values["categories"] or [])
        records.append(PaperRecord(**values))
    return records
