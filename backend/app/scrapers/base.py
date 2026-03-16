"""
RealDeal AI - Abstract Base Scraper

Provides the foundation for all property scrapers with rate limiting,
retry logic with exponential backoff, proxy rotation, and user-agent rotation.
"""

import asyncio
import hashlib
import logging
import random
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Optional

import aiohttp

from app.ai.deal_analyzer import PropertyData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User agent pool
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]


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
    - Async HTTP fetching via aiohttp
    - BrightData proxy rotation
    - User-agent rotation
    - Exponential backoff retry
    - Session management
    """

    SOURCE_NAME: str = "base"
    DEFAULT_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    BASE_BACKOFF: float = 1.0  # seconds

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        brightdata_username: Optional[str] = None,
        brightdata_password: Optional[str] = None,
        brightdata_host: str = "brd.superproxy.io",
        brightdata_port: int = 22225,
    ):
        self._proxy_url = proxy_url
        self._bd_user = brightdata_username
        self._bd_pass = brightdata_password
        self._bd_host = brightdata_host
        self._bd_port = brightdata_port
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    # ------------------------------------------------------------------
    # Proxy rotation
    # ------------------------------------------------------------------

    def _get_proxy(self) -> Optional[str]:
        """Build a BrightData proxy URL with session rotation."""
        if self._proxy_url:
            return self._proxy_url

        if not self._bd_user or not self._bd_pass:
            return None

        # Rotate session ID to get different exit IPs
        session_id = random.randint(100_000, 999_999)
        user = f"{self._bd_user}-session-{session_id}"
        return f"http://{user}:{self._bd_pass}@{self._bd_host}:{self._bd_port}"

    def _get_headers(self) -> dict[str, str]:
        """Return randomised request headers."""
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    # ------------------------------------------------------------------
    # HTTP fetch with retry
    # ------------------------------------------------------------------

    async def _fetch(self, url: str, method: str = "GET", **kwargs) -> str:
        """
        Fetch a URL with exponential backoff retry and proxy rotation.

        Returns the response body as text.
        Raises after MAX_RETRIES consecutive failures.
        """
        session = await self._get_session()
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
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
                            "[%s] 403 Forbidden on %s (attempt %d/%d), rotating proxy",
                            self.SOURCE_NAME,
                            url,
                            attempt + 1,
                            self.MAX_RETRIES,
                        )
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 5))
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
            backoff = self.BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(backoff)

        raise ScrapingError(
            f"[{self.SOURCE_NAME}] Failed after {self.MAX_RETRIES} attempts on {url}: {last_exc}"
        )

    async def _fetch_json(self, url: str, **kwargs) -> dict:
        """Fetch and parse JSON."""
        session = await self._get_session()
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
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
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        await asyncio.sleep(retry_after)
                        continue

            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                last_exc = exc

            backoff = self.BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
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
