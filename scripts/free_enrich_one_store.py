"""Free, public-web enrichment for one store.

This proof-of-concept fetches a store's active website presence, follows a small
set of useful public links, and extracts evidence for products, events, hours,
and contact details. It is read-only by default. Use ``--apply`` to upsert the
result into ``store_external_refs.provider = 'website_content'``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import and_, select

from lgs_directory.db import get_session
from lgs_directory.models.enums import ChannelType, CheckType, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef
from lgs_directory.models.validation_log import ValidationLog

USER_AGENT = "RollForStoreBot/0.1 (+https://www.rollforstore.com)"
TIMEOUT_SECS = 15
MAX_HTML_LEN = 400_000
MAX_PAGES = 8
COMMON_PAGE_PATHS = (
    "/pages/games-tcg",
    "/pages/events",
    "/pages/calendar",
    "/pages/contact",
    "/pages/location",
)

PRODUCT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "mtg": [
        re.compile(r"magic\s*:?\s*the\s+gathering", re.IGNORECASE),
        re.compile(r"\bmtg\b", re.IGNORECASE),
        re.compile(r"\bcommander\b", re.IGNORECASE),
    ],
    "pokemon": [re.compile(r"pok[eé]mon", re.IGNORECASE)],
    "yugioh": [re.compile(r"yu[\-\s]?gi[\-\s]?oh", re.IGNORECASE)],
    "lorcana": [re.compile(r"\blorcana\b", re.IGNORECASE)],
    "fab": [re.compile(r"flesh\s+and\s+blood", re.IGNORECASE)],
    "warhammer": [
        re.compile(r"\bwarhammer\b", re.IGNORECASE),
        re.compile(r"\b40k\b", re.IGNORECASE),
        re.compile(r"age\s+of\s+sigmar", re.IGNORECASE),
    ],
    "dnd": [
        re.compile(r"dungeons?\s*&?\s*dragons?", re.IGNORECASE),
        re.compile(r"\bd&d\b", re.IGNORECASE),
        re.compile(r"\brpgs?\b", re.IGNORECASE),
        re.compile(r"\bpathfinder\b", re.IGNORECASE),
    ],
    "board_games": [
        re.compile(r"board\s+games?", re.IGNORECASE),
        re.compile(r"tabletop\s+games?", re.IGNORECASE),
    ],
    "comics": [
        re.compile(r"\bcomics?\b", re.IGNORECASE),
        re.compile(r"graphic\s+novels?", re.IGNORECASE),
    ],
    "sports_cards": [
        re.compile(r"sports?\s+cards?", re.IGNORECASE),
        re.compile(r"\bpanini\b", re.IGNORECASE),
        re.compile(r"\btopps\b", re.IGNORECASE),
    ],
    "retro_games": [
        re.compile(r"retro\s+(video\s+)?games?", re.IGNORECASE),
        re.compile(r"video\s+games?", re.IGNORECASE),
    ],
    "miniatures": [
        re.compile(r"\bminiatures?\b", re.IGNORECASE),
        re.compile(r"\bpaints?\b", re.IGNORECASE),
        re.compile(r"\bterrain\b", re.IGNORECASE),
    ],
}

EVENT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "events": [re.compile(r"\bevents?\b", re.IGNORECASE)],
    "calendar": [re.compile(r"\bcalendar\b", re.IGNORECASE)],
    "fnm": [
        re.compile(r"friday\s+night\s+magic", re.IGNORECASE),
        re.compile(r"\bfnm\b", re.IGNORECASE),
    ],
    "commander": [re.compile(r"\bcommander\b", re.IGNORECASE)],
    "prerelease": [re.compile(r"\bpre[\-\s]?release\b", re.IGNORECASE)],
    "tournament": [re.compile(r"\btournaments?\b", re.IGNORECASE)],
    "pokemon_league": [
        re.compile(r"pok[eé]mon\s+league", re.IGNORECASE),
        re.compile(r"league\s+challenge", re.IGNORECASE),
    ],
    "event_calendar": [
        re.compile(r"event\s+calendar", re.IGNORECASE),
        re.compile(r"calendar\s+of\s+events", re.IGNORECASE),
    ],
}

HOURS_PATTERN = re.compile(
    r"\b(?:mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"[^<\n]{0,80}?\b(?:am|pm|closed)\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?:\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"
)
SCRIPT_REDIRECT_PATTERN = re.compile(
    r"window\.location\.href\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
PARKED_DOMAIN_PATTERNS = [
    re.compile(r"parking-lander", re.IGNORECASE),
    re.compile(r"adsense/domains/caf\.js", re.IGNORECASE),
    re.compile(r"window\._trfd.*parking", re.IGNORECASE),
]

LINK_HINTS = (
    "about",
    "calendar",
    "contact",
    "event",
    "hours",
    "magic",
    "pokemon",
    "product",
    "shop",
    "tcg",
    "tournament",
    "warhammer",
)


@dataclass(frozen=True)
class PageEvidence:
    """Evidence extracted from one fetched page."""

    url: str
    title: str | None
    description: str | None
    products: list[str]
    event_types: list[str]
    event_urls: list[str]
    phones: list[str]
    hours_text: list[str]
    json_ld_types: list[str]
    status_code: int


@dataclass(frozen=True)
class EventInstance:
    """Dated event instance extracted from a public calendar widget."""

    title: str
    start_date: str
    end_date: str
    timezone: str
    source_url: str
    service_id: str | None = None
    event_id: str | None = None
    status: str | None = None
    price: str | None = None
    location: str | None = None
    product_url: str | None = None
    description: str | None = None
    is_not_bookable: bool | None = None


@dataclass
class EnrichmentDossier:
    """Combined public-web enrichment evidence for one store."""

    store_id: str
    slug: str | None
    store_name: str
    address: dict[str, Any]
    store_phone: str | None
    google_place_id: str | None
    website_url: str
    fetched_at: str
    google_hours_weekday_text: list[str] | None = None
    google_rating: float | None = None
    google_user_rating_count: int | None = None
    pages_fetched: list[str] = field(default_factory=list)
    skipped_urls: list[dict[str, str]] = field(default_factory=list)
    description: str | None = None
    products: list[str] = field(default_factory=list)
    has_events: bool = False
    event_url: str | None = None
    event_types: list[str] = field(default_factory=list)
    event_services: list[dict[str, Any]] = field(default_factory=list)
    events_next_30_days: list[EventInstance] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    hours_text: list[str] = field(default_factory=list)
    structured_data_types: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    recommended_next_step: str = "manual_review"


def _clean_url(url: str) -> str:
    """Normalize URL enough to dedupe fetch candidates."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", "", ""))


def _same_site(base: str, candidate: str) -> bool:
    """Return true if candidate is on the same hostname as base."""
    base_host = urlparse(base).hostname or ""
    candidate_host = urlparse(candidate).hostname or ""
    return base_host.removeprefix("www.") == candidate_host.removeprefix("www.")


def _load_robots(client: httpx.Client, website_url: str) -> RobotFileParser | None:
    """Load robots.txt for the website if available."""
    parsed = urlparse(website_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = client.get(robots_url)
    except httpx.HTTPError:
        return None
    if response.status_code >= 400:
        return None
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return parser


def _can_fetch(robots: RobotFileParser | None, url: str) -> bool:
    """Return whether this bot may fetch the URL."""
    if robots is None:
        return True
    return robots.can_fetch(USER_AGENT, url)


def _text_for_scan(soup: BeautifulSoup) -> str:
    """Return compact page text plus selected metadata."""
    parts: list[str] = []
    title = soup.find("title")
    if title is not None:
        parts.append(title.get_text(" ", strip=True))
    for meta_name in ("description", "keywords"):
        meta = soup.find("meta", attrs={"name": meta_name})
        if meta is not None and isinstance(meta.get("content"), str):
            parts.append(str(meta["content"]))
    og = soup.find("meta", attrs={"property": "og:description"})
    if og is not None and isinstance(og.get("content"), str):
        parts.append(str(og["content"]))
    parts.append(soup.get_text(" ", strip=True))
    return " ".join(parts)


def _first_description(soup: BeautifulSoup) -> str | None:
    """Extract a short description from metadata or first substantial paragraph."""
    for attrs in ({"name": "description"}, {"property": "og:description"}):
        meta = soup.find("meta", attrs=attrs)
        if meta is not None and isinstance(meta.get("content"), str):
            value = str(meta["content"]).strip()
            if len(value) > 20:
                return value[:500]
    for paragraph in soup.find_all("p", limit=20):
        value = paragraph.get_text(" ", strip=True)
        if len(value) > 40:
            return value[:500]
    return None


def _scan_patterns(text: str, patterns: dict[str, list[re.Pattern[str]]]) -> dict[str, list[str]]:
    """Return matched categories and snippets."""
    matches: dict[str, list[str]] = defaultdict(list)
    for category, category_patterns in patterns.items():
        for pattern in category_patterns:
            match = pattern.search(text)
            if match is not None:
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                snippet = re.sub(r"\s+", " ", text[start:end]).strip()
                matches[category].append(snippet)
                break
    return dict(matches)


def _json_ld_types(soup: BeautifulSoup) -> list[str]:
    """Collect schema.org @type values from JSON-LD blocks."""
    types: set[str] = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        values = data if isinstance(data, list) else [data]
        for value in values:
            if isinstance(value, dict):
                raw_type = value.get("@type")
                if isinstance(raw_type, str):
                    types.add(raw_type)
                elif isinstance(raw_type, list):
                    types.update(str(item) for item in raw_type)
    return sorted(types)


def _extract_event_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    """Extract internal event/calendar links."""
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        text = link.get_text(" ", strip=True).lower()
        absolute = _clean_url(urljoin(base_url, href))
        haystack = f"{href} {text}".lower()
        if (
            any(hint in haystack for hint in ("event", "calendar", "tournament"))
            and _same_site(base_url, absolute)
            and absolute not in seen
        ):
            seen.add(absolute)
            urls.append(absolute)
    return urls[:5]


def _candidate_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    """Find a small set of likely useful same-site pages."""
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        text = link.get_text(" ", strip=True)
        absolute = _clean_url(urljoin(base_url, href))
        haystack = f"{href} {text}".lower()
        if not _same_site(base_url, absolute):
            continue
        if absolute in seen:
            continue
        if any(hint in haystack for hint in LINK_HINTS):
            seen.add(absolute)
            urls.append(absolute)
    return urls[: MAX_PAGES - 1]


def _common_page_candidates(base_url: str) -> list[str]:
    """Return common same-site page URLs worth probing for store facts."""
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return [_clean_url(urljoin(origin, path)) for path in COMMON_PAGE_PATHS]


def _script_redirect_url(base_url: str, html: str) -> str | None:
    """Return a simple same-site script redirect target if present."""
    match = SCRIPT_REDIRECT_PATTERN.search(html)
    if match is None:
        return None
    candidate = _clean_url(urljoin(base_url, match.group(1)))
    if _same_site(base_url, candidate):
        return candidate
    return None


def _is_parked_page(html: str) -> bool:
    """Return true for common domain-parking shells."""
    return any(pattern.search(html) for pattern in PARKED_DOMAIN_PATTERNS)


def _extract_page(url: str, html: str, status_code: int) -> PageEvidence:
    """Extract enrichment evidence from one HTML page."""
    soup = BeautifulSoup(html[:MAX_HTML_LEN], "html.parser")
    text = _text_for_scan(soup)
    product_matches = _scan_patterns(text, PRODUCT_PATTERNS)
    event_matches = _scan_patterns(text, EVENT_PATTERNS)
    phones = sorted(set(PHONE_PATTERN.findall(text)))[:5]
    hours = sorted(set(match.group(0).strip() for match in HOURS_PATTERN.finditer(text)))[:10]
    title_tag = soup.find("title")
    return PageEvidence(
        url=url,
        title=title_tag.get_text(" ", strip=True)[:250] if title_tag is not None else None,
        description=_first_description(soup),
        products=sorted(product_matches),
        event_types=sorted(event_matches),
        event_urls=_extract_event_links(url, soup),
        phones=phones,
        hours_text=hours,
        json_ld_types=_json_ld_types(soup),
        status_code=status_code,
    )


def _json_assignment(html: str, variable_name: str) -> Any | None:
    """Decode JSON assigned to a JavaScript variable."""
    marker = f"window.{variable_name}"
    marker_index = html.find(marker)
    if marker_index < 0:
        return None
    equals_index = html.find("=", marker_index)
    if equals_index < 0:
        return None
    start_index = equals_index + 1
    while start_index < len(html) and html[start_index].isspace():
        start_index += 1
    try:
        value, _ = json.JSONDecoder().raw_decode(html[start_index:])
    except json.JSONDecodeError:
        return None
    return value


def _extract_cowlendar_calendars(html: str) -> list[dict[str, Any]]:
    """Extract Cowlendar calendar config and service catalog from page HTML."""
    calendar_numbers = sorted(set(
        re.findall(r"window\.cowEventCal(\d+)_config\s*=", html)
        + re.findall(r"window\.cowEventCal(\d+)_services\s*=", html)
    ))
    calendars: list[dict[str, Any]] = []
    for number in calendar_numbers:
        config = _json_assignment(html, f"cowEventCal{number}_config")
        services = _json_assignment(html, f"cowEventCal{number}_services")
        if not isinstance(config, dict) or not isinstance(services, list):
            continue
        calendar_id = config.get("_id")
        if not isinstance(calendar_id, str) or not calendar_id:
            continue
        timezone = config.get("timezone")
        calendars.append({
            "calendar_id": calendar_id,
            "timezone": timezone if isinstance(timezone, str) else None,
            "services": [service for service in services if isinstance(service, dict)],
        })
    return calendars


def _month_periods(start: date, end: date) -> list[str]:
    """Return YYYY-MM periods touched by a date range."""
    periods: list[str] = []
    cursor = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while cursor <= last:
        periods.append(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return periods


def _local_today(timezone_name: str) -> date:
    """Return today's date in the calendar timezone."""
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = UTC
    return datetime.now(tz=timezone).date()


def _event_local_date(event_datetime: str) -> date | None:
    """Parse Cowlendar's local date string."""
    try:
        return datetime.strptime(event_datetime[:16], "%Y-%m-%d %H:%M").date()
    except ValueError:
        return None


def _fetch_cowlendar_events(
    client: httpx.Client,
    robots: RobotFileParser | None,
    source_url: str,
    calendar: dict[str, Any],
    days: int,
) -> list[EventInstance]:
    """Fetch dated Cowlendar events from the Shopify app proxy."""
    parsed = urlparse(source_url)
    endpoint = f"{parsed.scheme}://{parsed.netloc}/apps/cowlendar/event-calendar/events"
    if not _can_fetch(robots, endpoint):
        return []

    timezone_name = calendar.get("timezone") or "UTC"
    start = _local_today(str(timezone_name))
    end = start + timedelta(days=days)
    service_by_id = {
        service.get("_id"): service
        for service in calendar.get("services", [])
        if isinstance(service.get("_id"), str)
    }
    events: list[EventInstance] = []
    seen: set[tuple[str | None, str, str]] = set()
    for period in _month_periods(start, end):
        try:
            response = client.get(
                endpoint,
                params={
                    "calendar_id": calendar["calendar_id"],
                    "period": period,
                    "current_view": "month",
                    "timezone": timezone_name,
                    "is_preview": "false",
                },
            )
        except httpx.HTTPError:
            continue
        if response.status_code >= 400:
            continue
        try:
            payload = response.json()
        except json.JSONDecodeError:
            continue
        raw_events = payload.get("events")
        if not isinstance(raw_events, list):
            continue
        for raw_event in raw_events:
            if not isinstance(raw_event, dict):
                continue
            start_date = raw_event.get("start_date")
            end_date = raw_event.get("end_date")
            service_id = raw_event.get("service_id")
            if not isinstance(start_date, str) or not isinstance(end_date, str):
                continue
            event_day = _event_local_date(start_date)
            if event_day is None or event_day < start or event_day > end:
                continue
            service = service_by_id.get(service_id)
            if service is None:
                continue
            raw_event_id = raw_event.get("id")
            key = (
                service_id if isinstance(service_id, str) else None,
                start_date,
                end_date,
            )
            if key in seen:
                continue
            seen.add(key)
            product_handle = service.get("product_url")
            product_url = (
                urljoin(source_url, f"/products/{product_handle}")
                if isinstance(product_handle, str) and product_handle
                else None
            )
            events.append(EventInstance(
                title=str(service.get("title") or "Untitled event"),
                start_date=start_date,
                end_date=end_date,
                timezone=str(timezone_name),
                source_url=source_url,
                service_id=service_id if isinstance(service_id, str) else None,
                event_id=raw_event_id if isinstance(raw_event_id, str) else None,
                status=(
                    raw_event.get("status")
                    if isinstance(raw_event.get("status"), str)
                    else None
                ),
                price=raw_event.get("price") if isinstance(raw_event.get("price"), str) else None,
                location=(
                    service.get("location")
                    if isinstance(service.get("location"), str)
                    else None
                ),
                product_url=product_url,
                description=(
                    str(service["description"])[:500]
                    if isinstance(service.get("description"), str)
                    else None
                ),
                is_not_bookable=(
                    raw_event.get("is_not_bookable")
                    if isinstance(raw_event.get("is_not_bookable"), bool)
                    else None
                ),
            ))
    return sorted(events, key=lambda event: event.start_date)


def _fetch_page(
    client: httpx.Client,
    robots: RobotFileParser | None,
    url: str,
) -> tuple[str | None, int | None, str | None]:
    """Fetch a page if robots allows it."""
    if not _can_fetch(robots, url):
        return None, None, "robots_disallowed"
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        return None, None, f"http_error:{type(exc).__name__}"
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400:
        return None, response.status_code, "bad_status"
    if "html" not in content_type.lower():
        return None, response.status_code, "non_html"
    return response.text[:MAX_HTML_LEN], response.status_code, None


def _choose_presence(store: Store, presences: list[OnlinePresence]) -> OnlinePresence:
    """Choose the best website presence for enrichment."""
    websites = [
        presence for presence in presences
        if presence.channel_type == ChannelType.WEBSITE
        and presence.status == PresenceStatus.ACTIVE
        and "facebook.com" not in presence.url.lower()
        and "instagram.com" not in presence.url.lower()
    ]
    if websites:
        return websites[0]
    active = [
        presence for presence in presences
        if presence.status == PresenceStatus.ACTIVE
    ]
    if active:
        return active[0]
    raise RuntimeError(f"No active online presence found for {store.name}")


def _load_store(identifier: str) -> tuple[Store, list[OnlinePresence], dict[str, Any] | None]:
    """Load store and presences by UUID or slug."""
    with get_session() as session:
        try:
            store_id = UUID(identifier)
            store = session.get(Store, store_id)
        except ValueError:
            store = session.execute(
                select(Store).where(Store.slug == identifier)
            ).scalar_one_or_none()
        if store is None:
            raise RuntimeError(f"Store not found: {identifier}")
        presences = list(session.execute(
            select(OnlinePresence).where(OnlinePresence.store_id == store.id)
        ).scalars().all())
        google_ref = session.execute(
            select(StoreExternalRef.payload).where(
                StoreExternalRef.store_id == store.id,
                StoreExternalRef.provider == "google_places",
            )
        ).scalar_one_or_none()
    return store, presences, google_ref


def build_dossier(
    store: Store,
    presence: OnlinePresence,
    google_payload: dict[str, Any] | None,
) -> EnrichmentDossier:
    """Fetch public pages and build a combined evidence dossier."""
    fetched_at = datetime.now(tz=UTC).isoformat()
    hours = google_payload.get("hours") if isinstance(google_payload, dict) else None
    weekday_text = hours.get("weekday_text") if isinstance(hours, dict) else None
    dossier = EnrichmentDossier(
        store_id=str(store.id),
        slug=store.slug,
        store_name=store.name,
        address=dict(store.address),
        store_phone=store.phone,
        google_place_id=store.google_place_id,
        website_url=presence.url,
        fetched_at=fetched_at,
        google_hours_weekday_text=weekday_text if isinstance(weekday_text, list) else None,
        google_rating=google_payload.get("rating") if isinstance(google_payload, dict) else None,
        google_user_rating_count=(
            google_payload.get("user_rating_count")
            if isinstance(google_payload, dict)
            else None
        ),
    )

    pages: list[PageEvidence] = []
    event_services_by_id: dict[str, dict[str, Any]] = {}
    events_by_key: dict[tuple[str | None, str, str], EventInstance] = {}
    with httpx.Client(
        headers={"user-agent": USER_AGENT},
        follow_redirects=True,
        timeout=TIMEOUT_SECS,
    ) as client:
        robots = _load_robots(client, presence.url)
        queue = [_clean_url(presence.url)]
        seen: set[str] = set()

        while queue and len(pages) < MAX_PAGES:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            html, status_code, skip_reason = _fetch_page(client, robots, url)
            if skip_reason is not None or html is None or status_code is None:
                dossier.skipped_urls.append({"url": url, "reason": skip_reason or "unknown"})
                continue
            redirect_url = _script_redirect_url(url, html)
            if redirect_url is not None and redirect_url not in seen:
                queue.insert(0, redirect_url)
                dossier.skipped_urls.append({"url": url, "reason": "script_redirect"})
                continue
            if _is_parked_page(html):
                dossier.skipped_urls.append({"url": url, "reason": "parked_domain"})
                continue
            for calendar in _extract_cowlendar_calendars(html):
                for service in calendar.get("services", []):
                    service_id = service.get("_id")
                    if isinstance(service_id, str):
                        event_services_by_id[service_id] = {
                            "service_id": service_id,
                            "title": service.get("title"),
                            "location": service.get("location"),
                            "product_url": (
                                urljoin(url, f"/products/{service['product_url']}")
                                if isinstance(service.get("product_url"), str)
                                else None
                            ),
                        }
                for event in _fetch_cowlendar_events(client, robots, url, calendar, days=30):
                    events_by_key[(event.service_id, event.start_date, event.end_date)] = event
            page = _extract_page(url, html, status_code)
            pages.append(page)
            if len(pages) == 1:
                soup = BeautifulSoup(html, "html.parser")
                for candidate in _candidate_links(url, soup) + _common_page_candidates(url):
                    if candidate not in seen and candidate not in queue:
                        queue.append(candidate)

    product_set: set[str] = set()
    event_type_set: set[str] = set()
    event_urls: list[str] = []
    phones: set[str] = set()
    hours: set[str] = set()
    structured_types: set[str] = set()
    matched_keywords: dict[str, list[str]] = {}

    for page in pages:
        dossier.pages_fetched.append(page.url)
        product_set.update(page.products)
        event_type_set.update(page.event_types)
        event_urls.extend(page.event_urls)
        phones.update(page.phones)
        hours.update(page.hours_text)
        structured_types.update(page.json_ld_types)
        if dossier.description is None and page.description is not None:
            dossier.description = page.description
        for product in page.products:
            matched_keywords.setdefault(product, []).append(page.url)

    dossier.products = sorted(product_set)
    dossier.event_types = sorted(event_type_set)
    dossier.event_services = sorted(
        event_services_by_id.values(),
        key=lambda service: str(service.get("title") or ""),
    )
    dossier.events_next_30_days = sorted(
        events_by_key.values(),
        key=lambda event: event.start_date,
    )
    dossier.has_events = bool(event_type_set or event_urls or dossier.events_next_30_days)
    dossier.event_url = event_urls[0] if event_urls else None
    dossier.phones = sorted(phones)
    dossier.hours_text = sorted(hours)
    dossier.structured_data_types = sorted(structured_types)
    dossier.evidence = {
        "source_urls": dossier.pages_fetched,
        "google_places": {
            "place_id": dossier.google_place_id,
            "hours_weekday_text": dossier.google_hours_weekday_text,
            "rating": dossier.google_rating,
            "user_rating_count": dossier.google_user_rating_count,
        },
        "matched_product_pages": matched_keywords,
        "events_next_30_days_count": len(dossier.events_next_30_days),
        "page_evidence": [asdict(page) for page in pages],
        "user_agent": USER_AGENT,
        "robots_checked": True,
    }
    dossier.confidence = _score_confidence(dossier)
    dossier.recommended_next_step = _recommend_next_step(dossier)
    return dossier


def _score_confidence(dossier: EnrichmentDossier) -> float:
    """Score how useful the evidence is for public-page quality."""
    score = 0.0
    if dossier.pages_fetched:
        score += 0.20
    if dossier.description:
        score += 0.10
    if dossier.products:
        score += min(0.30, 0.10 * len(dossier.products))
    if dossier.has_events:
        score += 0.20
    if dossier.events_next_30_days:
        score += 0.10
    if dossier.phones:
        score += 0.10
    if dossier.hours_text:
        score += 0.10
    return round(min(score, 1.0), 2)


def _recommend_next_step(dossier: EnrichmentDossier) -> str:
    """Recommend whether the evidence is strong enough for review/reactivation."""
    if dossier.confidence >= 0.65 and dossier.products:
        return "review_for_reactivation"
    if dossier.pages_fetched and (dossier.products or dossier.has_events):
        return "keep_suppressed_enriched"
    return "manual_review"


def apply_dossier(dossier: EnrichmentDossier) -> None:
    """Persist dossier as website_content evidence and a validation log."""
    payload = {
        "description": dossier.description,
        "products": dossier.products,
        "has_events": dossier.has_events,
        "event_url": dossier.event_url,
        "event_types": dossier.event_types,
        "event_services": dossier.event_services,
        "events_next_30_days": [asdict(event) for event in dossier.events_next_30_days],
        "contact": {
            "address": dossier.address,
            "phone": dossier.store_phone,
            "website_url": dossier.website_url,
        },
        "google_hours_weekday_text": dossier.google_hours_weekday_text,
        "google_rating": dossier.google_rating,
        "google_user_rating_count": dossier.google_user_rating_count,
        "phones": dossier.phones,
        "hours_text": dossier.hours_text,
        "structured_data_types": dossier.structured_data_types,
        "extracted_at": dossier.fetched_at,
        "method": "free_public_web",
        "confidence": dossier.confidence,
        "recommended_next_step": dossier.recommended_next_step,
        "evidence": dossier.evidence,
    }

    with get_session() as session:
        store_id = UUID(dossier.store_id)
        existing = session.execute(
            select(StoreExternalRef).where(
                and_(
                    StoreExternalRef.store_id == store_id,
                    StoreExternalRef.provider == "website_content",
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(StoreExternalRef(
                store_id=store_id,
                provider="website_content",
                external_id=dossier.store_id,
                payload=payload,
            ))
        else:
            existing.payload = payload
            existing.last_seen = datetime.now(tz=UTC)

        presence = session.execute(
            select(OnlinePresence).where(
                OnlinePresence.store_id == store_id,
                OnlinePresence.url == dossier.website_url,
            )
        ).scalar_one_or_none()

        session.add(ValidationLog(
            store_id=store_id,
            presence_id=presence.id if presence is not None else None,
            check_type=CheckType.CONTENT_EXTRACT,
            result={
                "source": "free_enrich_one_store",
                "website_url": dossier.website_url,
                "pages_fetched": len(dossier.pages_fetched),
                "products": dossier.products,
                "has_events": dossier.has_events,
                "confidence": dossier.confidence,
                "recommended_next_step": dossier.recommended_next_step,
            },
        ))


def main() -> None:
    """Run one-store free enrichment."""
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--store-id", help="Store UUID to enrich.")
    target.add_argument("--slug", help="Store slug to enrich.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    identifier = args.store_id or args.slug
    assert identifier is not None
    store, presences, google_payload = _load_store(identifier)
    presence = _choose_presence(store, presences)
    dossier = build_dossier(store, presence, google_payload)

    output = json.dumps(asdict(dossier), indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    if args.apply:
        apply_dossier(dossier)
        print(
            f"applied website_content evidence for {dossier.store_name}",
            file=sys.stderr,
        )
    else:
        print(
            f"dry run: {dossier.store_name} confidence={dossier.confidence} "
            f"next={dossier.recommended_next_step}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
