"""Akamai Bot Manager cookie harvesting via Playwright."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_LOCATOR_URL = "https://locator.wizards.com"
_WAIT_SECS = 5
_AKAMAI_COOKIE_PREFIXES = ("ak_bmsc", "bm_sv")


def get_akamai_cookies() -> dict[str, str]:
    """Launch headless Chromium to harvest Akamai cookies.

    Navigates to the WPN locator page, waits for the Akamai challenge
    to resolve, then extracts relevant cookies.

    Returns:
        Dict mapping cookie name to value for Akamai-related cookies.

    Raises:
        AssertionError: If no Akamai cookies were found.
    """
    from playwright.sync_api import sync_playwright

    assert isinstance(_LOCATOR_URL, str)

    logger.info("Launching headless browser for Akamai cookie harvesting...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        assert browser is not None

        context = browser.new_context()
        page = context.new_page()

        logger.info("Navigating to %s", _LOCATOR_URL)
        page.goto(_LOCATOR_URL, wait_until="networkidle")
        page.wait_for_timeout(_WAIT_SECS * 1000)

        all_cookies = context.cookies()
        assert isinstance(all_cookies, list)

        cookies: dict[str, str] = {}
        for cookie in all_cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if name.startswith(_AKAMAI_COOKIE_PREFIXES):
                cookies[name] = value
                logger.info("Found Akamai cookie: %s", name)

        browser.close()

    assert len(cookies) > 0, (
        "No Akamai cookies found — the challenge may not have resolved. "
        "Ensure Playwright browsers are installed: playwright install chromium"
    )
    logger.info("Harvested %d Akamai cookies", len(cookies))
    return cookies
