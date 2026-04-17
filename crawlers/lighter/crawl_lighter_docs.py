#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from crawlers.common.perpdex_crawler import CrawlConfig, RecursiveDocsCrawler


async def main() -> None:
    config = CrawlConfig(
        exchange="lighter",
        start_urls=("https://docs.lighter.xyz/",),
        allowed_domains=("docs.lighter.xyz",),
        allowed_path_prefixes=("/",),
    )
    crawler = RecursiveDocsCrawler(config=config, out_dir=ROOT / "outputs" / "lighter")
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
