"""CLI commands for scraping content from store websites."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

import click
from rich.console import Console
from sqlalchemy import select, and_

from lgs_directory.db import get_session
from lgs_directory.models.enums import ChannelType, CheckType, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store_external_ref import StoreExternalRef
from lgs_directory.models.validation_log import ValidationLog

console = Console()

_RATE_LIMIT_SECS = 0.5  # 2 req/sec
_MAX_STORES = 10_000

BLOCKED_DOMAINS = {
    # Social media / marketplaces
    "facebook.com",
    "fb.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
    "ebay.com",
    "amazon.com",
    "etsy.com",
    "tcgplayer.com",
    "yelp.com",
    "google.com",
    # Corporate / chain stores (not LGS)
    "warhammer.com",
    "games-workshop.com",
    "gamestop.com",
    "hobbylobby.com",
    "hobbytown.com",
    "2ndandcharles.com",
    "learningexpress.com",
    "scientificgames.com",
    "drafthouse.com",
    # Wizards of the Coast (not store websites)
    "wizards.com",
    "locator.wizards.com",
    # Other non-store sites
    "sportscard-stores.com",
    "perfectgame.org",
}


def _is_blocked_domain(url: str) -> bool:
    """Return True if the URL's domain is in BLOCKED_DOMAINS."""
    assert isinstance(url, str), "url must be a string"
    assert len(url) > 0, "url must not be empty"

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    domain = hostname.removeprefix("www.")

    assert isinstance(domain, str), "domain must be a string"

    if domain in BLOCKED_DOMAINS:
        return True

    # Check parent domain (e.g. store.warhammer.com -> warhammer.com)
    parts = domain.split(".")
    max_parts = len(parts)
    for i in range(1, max_parts):
        parent = ".".join(parts[i:])
        if parent in BLOCKED_DOMAINS:
            return True

    return False


@click.group()
def scrape() -> None:
    """Scrape content from store websites."""


@scrape.command()
@click.option("--limit", default=50, help="Max stores to scrape.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be done.")
@click.option("--force", is_flag=True, default=False, help="Re-scrape already-scraped stores.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def content(
    limit: int,
    dry_run: bool,
    force: bool,
    verbose: bool,
) -> None:
    """Extract descriptions, products, and events from store websites."""
    from lgs_directory.config import get_settings
    from lgs_directory.validation.content_extract import extract_content

    assert limit > 0, "limit must be positive"
    assert limit <= _MAX_STORES, f"limit must be <= {_MAX_STORES}"

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    settings = get_settings()

    with get_session() as session:
        # Find active website presences
        stmt = (
            select(OnlinePresence)
            .where(OnlinePresence.channel_type == ChannelType.WEBSITE)
            .where(OnlinePresence.status == PresenceStatus.ACTIVE)
            .where(OnlinePresence.url.isnot(None))
        )

        if not force:
            # Exclude stores that already have website_content entries
            already_scraped = (
                select(StoreExternalRef.store_id)
                .where(StoreExternalRef.provider == "website_content")
            )
            stmt = stmt.where(
                OnlinePresence.store_id.notin_(already_scraped)
            )

        stmt = stmt.limit(limit)
        presences = list(session.execute(stmt).scalars().all())
        assert isinstance(presences, list), "presences must be a list"

        console.print(
            f"Found [bold]{len(presences)}[/bold] website presences to scrape"
            f"{' (dry run)' if dry_run else ''}"
        )

        if dry_run:
            for p in presences:
                console.print(f"  Would scrape: {p.url}")
            return

        budget_remaining = settings.llm_budget_cents
        extracted_count = 0
        error_count = 0
        llm_count = 0
        scraped_urls: set[str] = set()

        bounded_limit = min(len(presences), _MAX_STORES)
        for i in range(bounded_limit):
            p = presences[i]
            assert isinstance(p, OnlinePresence), "presence must be OnlinePresence"
            assert p.url is not None, "presence must have a URL"

            url = p.url
            assert isinstance(url, str), "url must be a string"

            # Check blocked domain before printing progress
            if _is_blocked_domain(url):
                console.print(
                    f"  [{i + 1}/{bounded_limit}] {url} [yellow]skipped (blocked domain)[/yellow]"
                )
                continue

            # Check for duplicate URL within this run
            if url in scraped_urls:
                console.print(
                    f"  [{i + 1}/{bounded_limit}] {url} [yellow]skipped (duplicate URL)[/yellow]"
                )
                continue

            scraped_urls.add(url)

            console.print(
                f"  [{i + 1}/{bounded_limit}] {url}",
                end=" ",
            )

            try:
                result = extract_content(
                    url=p.url,
                    anthropic_api_key=settings.anthropic_api_key,
                    llm_budget_cents=budget_remaining,
                )

                # Track LLM budget
                if result.method == "llm":
                    llm_count += 1
                    budget_remaining = max(0, budget_remaining - 5)

                # Build payload
                now_iso = datetime.now(tz=UTC).isoformat()
                payload = {
                    "description": result.description,
                    "products": result.products,
                    "has_events": result.has_events,
                    "event_url": result.event_url,
                    "extracted_at": now_iso,
                    "method": result.method,
                }

                # Upsert into store_external_refs
                existing_ref = session.execute(
                    select(StoreExternalRef).where(
                        and_(
                            StoreExternalRef.store_id == p.store_id,
                            StoreExternalRef.provider == "website_content",
                        )
                    )
                ).scalar_one_or_none()

                if existing_ref is not None:
                    existing_ref.payload = payload
                    existing_ref.last_seen = datetime.now(tz=UTC)
                else:
                    new_ref = StoreExternalRef(
                        store_id=p.store_id,
                        provider="website_content",
                        external_id=str(p.store_id),
                        payload=payload,
                    )
                    session.add(new_ref)

                # Log to validation_logs for audit trail
                log_entry = ValidationLog(
                    store_id=p.store_id,
                    presence_id=p.id,
                    check_type=CheckType.CONTENT_EXTRACT,
                    result={
                        "url": p.url,
                        "products_found": len(result.products),
                        "has_events": result.has_events,
                        "method": result.method,
                        "confidence": result.confidence,
                    },
                )
                session.add(log_entry)

                extracted_count += 1
                status_parts = []
                if result.description:
                    status_parts.append("desc")
                if len(result.products) > 0:
                    status_parts.append(f"{len(result.products)} products")
                if result.has_events:
                    status_parts.append("events")

                console.print(
                    f"[green]{result.method}[/green] "
                    f"({', '.join(status_parts) if status_parts else 'minimal'})"
                )

            except Exception as exc:
                error_count += 1
                console.print(f"[red]error:[/red] {exc}")

            # Rate limit: 2 req/sec
            time.sleep(_RATE_LIMIT_SECS)

    console.print(f"\n[bold]Content Extraction Results:[/bold]")
    console.print(f"  Presences scraped:  {extracted_count}")
    console.print(f"  LLM calls:          {llm_count}")
    console.print(f"  Errors:             {error_count}")
