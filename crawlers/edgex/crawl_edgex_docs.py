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
        exchange="edgex",
        start_urls=("https://docs.edgex.exchange/",),
        allowed_domains=("docs.edgex.exchange",),
        allowed_path_prefixes=("/",),
    )
    crawler = RecursiveDocsCrawler(config=config, out_dir=ROOT / "outputs" / "edgex")
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
