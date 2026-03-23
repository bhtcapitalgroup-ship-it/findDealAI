"""
RealDeal AI - Abstract Base Scraper

Provides the foundation for all property scrapers with rate limiting,
retry logic with exponential backoff, free proxy rotation, and user-agent rotation.

NO paid services required -- uses direct HTTP requests with aiohttp,
free User-Agent rotation, optional free proxy lists, and per-domain rate limiting.
"""

import asyncio
import hashlib
import logging
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import wraps
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp

from app.ai.deal_analyzer import PropertyData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User agent pool (20+ real browser UAs)
# ---------------------------------------------------------------------------
USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Firefox (Linux)
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari (iOS)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    # Safari (iPad)
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    # Chrome (Android)
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
]

# ---------------------------------------------------------------------------
# Per-domain rate limiter: max 1 request per 3 seconds per domain
# ---------------------------------------------------------------------------
_domain_last_request: dict[str, float] = defaultdict(float)
_domain_lock: asyncio.Lock = asyncio.Lock()

MIN_DOMAIN_INTERVAL = 3.0  # seconds between requests to the same domain


async def _enforce_domain_rate_limit(url: str) -> None:
    """Wait if needed so we don't exceed 1 request per 3s to the same domain."""
    domain = urlparse(url).netloc
    async with _domain_lock:
        now = time.monotonic()
        elapsed = now - _domain_last_request[domain]
        if elapsed < MIN_DOMAIN_INTERVAL:
            wait = MIN_DOMAIN_INTERVAL - elapsed + random.uniform(0, 0.5)
            await asyncio.sleep(wait)
        _domain_last_request[domain] = time.monotonic()


def rate_limit(calls_per_second: float = 1.0):
    """
    Decorator that enforces a maximum request rate.

    Uses a token-bucket approach: each call sleeps until enough time
    has elapsed since the previous call.
    """
    min_interval = 1.0 / calls_per_second
    last_call: dict[str, float] = {"ts": 0.0}

    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            elapsed = time.monotonic() - last_call["ts"]
            if elapsed < min_interval:
                jitter = random.uniform(0, min_interval * 0.2)
                await asyncio.sleep(min_interval - elapsed + jitter)
            last_call["ts"] = time.monotonic()
            return await fn(*args, **kwargs)

        return wrapper

    return decorator


class BaseScraper(ABC):
    """
    Abstract base for all property data scrapers.

    Features:
    - Async HTTP fetching via aiohttp (no paid proxy service)
    - Optional free proxy rotation from env var FREE_PROXY_LIST
    - 20+ real browser User-Agent rotation
    - Browser-mimicking request headers
    - Random delays between requests (2-5 seconds)
    - Per-domain rate limiting (max 1 request per 3 seconds)
    - Exponential backoff retry with jitter
    - Cookie jar persistence per session
    """

    SOURCE_NAME: str = "base"
    DEFAULT_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    BASE_BACKOFF: float = 2.0  # seconds

    def __init__(
        self,
        free_proxy_list: str = "",
    ):
        """
        Args:
            free_proxy_list: Comma-separated list of free proxy URLs.
                             Can also be set via FREE_PROXY_LIST env var.
                             Completely optional -- works fine without proxies.
        """
        import os

        proxy_str = free_proxy_list or os.getenv("FREE_PROXY_LIST", "")
        self._proxies: list[str] = [
            p.strip() for p in proxy_str.split(",") if p.strip()
        ]
        self._session: Optional[aiohttp.ClientSession] = None
        self._cookie_jar: aiohttp.CookieJar = aiohttp.CookieJar(unsafe=True)
        self._request_count = 0

    # ------------------------------------------------------------------
    # Session management (with persistent cookie jar)
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                cookie_jar=self._cookie_jar,
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    # ------------------------------------------------------------------
    # Proxy rotation (free proxies, optional)
    # ------------------------------------------------------------------

    def _get_proxy(self) -> Optional[str]:
        """Pick a random proxy from the free proxy list, or None."""
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    # ------------------------------------------------------------------
    # Browser-mimicking headers
    # ------------------------------------------------------------------

    def _get_headers(self) -> dict[str, str]:
        """Return randomized request headers that mimic a real browser."""
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-CH-UA": '"Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache",
        }

    # ------------------------------------------------------------------
    # Random delay between requests
    # ------------------------------------------------------------------

    @staticmethod
    async def _random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
        """Add a random delay between requests to appear more human."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # HTTP fetch with retry + exponential backoff
    # ------------------------------------------------------------------

    async def _fetch(self, url: str, method: str = "GET", **kwargs) -> str:
        """
        Fetch a URL with exponential backoff retry, proxy rotation,
        per-domain rate limiting, and random delays.

        Returns the response body as text.
        Raises ScrapingError after MAX_RETRIES consecutive failures.
        """
        session = await self._get_session()
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            # Enforce per-domain rate limit
            await _enforce_domain_rate_limit(url)

            # Add random delay for human-like behavior
            if attempt > 0 or self._request_count > 0:
                await self._random_delay()

            proxy = self._get_proxy()
            headers = self._get_headers()
            headers.update(kwargs.pop("headers", {}))

            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    proxy=proxy,
                    ssl=False,
                    **kwargs,
                ) as resp:
                    self._request_count += 1

                    if resp.status == 200:
                        return await resp.text()

                    if resp.status == 403:
                        logger.warning(
                            "[%s] 403 Forbidden on %s (attempt %d/%d), rotating proxy/UA",
                            self.SOURCE_NAME,
                            url,
                            attempt + 1,
                            self.MAX_RETRIES,
                        )
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 10))
                        logger.warning(
                            "[%s] Rate limited on %s, waiting %ds",
                            self.SOURCE_NAME,
                            url,
                            retry_after,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    elif resp.status >= 500:
                        logger.warning(
                            "[%s] Server error %d on %s",
                            self.SOURCE_NAME,
                            resp.status,
                            url,
                        )
                    else:
                        body = await resp.text()
                        logger.warning(
                            "[%s] Unexpected status %d on %s: %s",
                            self.SOURCE_NAME,
                            resp.status,
                            url,
                            body[:200],
                        )

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Request error on %s (attempt %d/%d): %s",
                    self.SOURCE_NAME,
                    url,
                    attempt + 1,
                    self.MAX_RETRIES,
                    str(exc),
                )

            # Exponential backoff with jitter
            backoff = self.BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 2)
            logger.debug(
                "[%s] Backing off %.1fs before retry %d",
                self.SOURCE_NAME,
                backoff,
                attempt + 2,
            )
            await asyncio.sleep(backoff)

        raise ScrapingError(
            f"[{self.SOURCE_NAME}] Failed after {self.MAX_RETRIES} attempts on {url}: {last_exc}"
        )

    async def _fetch_json(self, url: str, **kwargs) -> dict:
        """Fetch and parse JSON with the same retry/rate-limit logic."""
        session = await self._get_session()
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            await _enforce_domain_rate_limit(url)

            if attempt > 0 or self._request_count > 0:
                await self._random_delay()

            proxy = self._get_proxy()
            headers = self._get_headers()
            headers["Accept"] = "application/json"
            headers.update(kwargs.pop("headers", {}))

            try:
                async with session.request(
                    "GET",
                    url,
                    headers=headers,
                    proxy=proxy,
                    ssl=False,
                    **kwargs,
                ) as resp:
                    self._request_count += 1
                    if resp.status == 200:
                        return await resp.json(content_type=None)

                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 10))
                        await asyncio.sleep(retry_after)
                        continue

            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                last_exc = exc

            backoff = self.BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 2)
            await asyncio.sleep(backoff)

        raise ScrapingError(
            f"[{self.SOURCE_NAME}] JSON fetch failed after {self.MAX_RETRIES} attempts on {url}: {last_exc}"
        )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def scrape(self, url: str) -> dict[str, Any]:
        """
        Scrape a single URL and return structured data.

        Subclasses implement the full scrape-and-parse pipeline.
        """
        ...

    @abstractmethod
    def parse(self, raw_html: str) -> list[PropertyData]:
        """
        Parse raw HTML into a list of PropertyData objects.

        Each scraper implements site-specific parsing logic.
        """
        ...

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_price(text: str) -> float:
        """Extract a numeric price from text like '$425,000'."""
        cleaned = text.replace("$", "").replace(",", "").replace("+", "").strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _clean_int(text: str) -> int:
        cleaned = "".join(c for c in str(text) if c.isdigit())
        try:
            return int(cleaned)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _clean_float(text: str) -> float:
        cleaned = "".join(c for c in str(text) if c.isdigit() or c == ".")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _fingerprint(data: dict) -> str:
        """Generate a dedup fingerprint from address fields."""
        key = f"{data.get('address', '')}-{data.get('zip_code', '')}-{data.get('price', '')}".lower()
        return hashlib.md5(key.encode()).hexdigest()

    @property
    def request_count(self) -> int:
        return self._request_count


class ScrapingError(Exception):
    """Raised when a scraping operation fails after retries."""

    pass
