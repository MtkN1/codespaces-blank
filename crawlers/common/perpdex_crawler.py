#!/usr/bin/env python3
"""Recursive docs crawler for Perp DEX documentation sites.

- Traverses pages recursively within configured allowlist.
- Uses Playwright Chromium for dynamic/static pages.
- Stores raw HTML and metadata without normalization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse


@dataclass(frozen=True)
class CrawlConfig:
    exchange: str
    start_urls: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...] = ("/",)


class RecursiveDocsCrawler:
    def __init__(
        self,
        config: CrawlConfig,
        out_dir: Path,
        max_pages: int = 200,
        delay_sec: float = 0.2,
    ) -> None:
        self.config = config
        self.out_dir = out_dir
        self.max_pages = max_pages
        self.delay_sec = delay_sec

        self.raw_dir = out_dir / "raw_html"
        self.meta_dir = out_dir / "metadata"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_url(self, base: str, href: str) -> str | None:
        if not href:
            return None
        abs_url = urljoin(base, href)
        abs_url, _fragment = urldefrag(abs_url)
        parsed = urlparse(abs_url)
        if parsed.scheme not in {"http", "https"}:
            return None
        return abs_url

    def _is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc not in self.config.allowed_domains:
            return False
        return any(parsed.path.startswith(p) for p in self.config.allowed_path_prefixes)

    @staticmethod
    def _url_id(url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def _persist_page(self, url: str, status: int, html: str, outlinks: Iterable[str]) -> None:
        url_id = self._url_id(url)
        timestamp = int(time.time())

        (self.raw_dir / f"{url_id}.html").write_text(html, encoding="utf-8")
        metadata = {
            "url": url,
            "url_id": url_id,
            "status": status,
            "fetched_at_unix": timestamp,
            "exchange": self.config.exchange,
            "outlinks": sorted(set(outlinks)),
        }
        (self.meta_dir / f"{url_id}.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with (self.out_dir / "url_index.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")

    async def run(self) -> None:
        from playwright.async_api import async_playwright

        queue: deque[str] = deque(self.config.start_urls)
        visited: set[str] = set()
        failed: list[dict[str, str]] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            while queue and len(visited) < self.max_pages:
                url = queue.popleft()
                if url in visited or not self._is_allowed(url):
                    continue

                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=45_000)
                    status = response.status if response else 0
                    html = await page.content()
                    hrefs = await page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.getAttribute('href'))",
                    )
                    outlinks: list[str] = []
                    for href in hrefs:
                        nxt = self._normalize_url(url, href)
                        if not nxt:
                            continue
                        outlinks.append(nxt)
                        if self._is_allowed(nxt) and nxt not in visited:
                            queue.append(nxt)

                    self._persist_page(url=url, status=status, html=html, outlinks=outlinks)
                    visited.add(url)
                    print(f"[OK] {status} {url}")
                    if self.delay_sec > 0:
                        await page.wait_for_timeout(int(self.delay_sec * 1000))
                except Exception as exc:  # prototype: log and continue
                    failed.append({"url": url, "error": str(exc)})
                    visited.add(url)
                    print(f"[ERR] {url} -> {exc}")

            await context.close()
            await browser.close()

        (self.out_dir / "crawl_summary.json").write_text(
            json.dumps(
                {
                    "exchange": self.config.exchange,
                    "visited_pages": len(visited),
                    "failed_pages": len(failed),
                    "max_pages": self.max_pages,
                    "start_urls": list(self.config.start_urls),
                    "failed": failed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recursive Perp DEX docs crawler")
    parser.add_argument("--exchange", required=True, help="Exchange key for output folder")
    parser.add_argument("--start-url", action="append", required=True, help="Seed docs URL (repeatable)")
    parser.add_argument("--allow-domain", action="append", required=True, help="Allowed domain (repeatable)")
    parser.add_argument(
        "--allow-prefix",
        action="append",
        default=["/"],
        help="Allowed path prefix in allowed domains (repeatable)",
    )
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--delay-sec", type=float, default=0.2)
    parser.add_argument("--output-root", default="outputs")
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    config = CrawlConfig(
        exchange=args.exchange,
        start_urls=tuple(args.start_url),
        allowed_domains=tuple(args.allow_domain),
        allowed_path_prefixes=tuple(args.allow_prefix),
    )
    out_dir = Path(args.output_root) / args.exchange
    crawler = RecursiveDocsCrawler(
        config=config,
        out_dir=out_dir,
        max_pages=args.max_pages,
        delay_sec=args.delay_sec,
    )
    await crawler.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
