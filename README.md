# Perp DEX Docs Crawlers (Prototype)

主要Perp DEX（Top 1〜5）向けに、取引所別のドキュメント再帰クローラを用意しています。

## 対象取引所
- Hyperliquid
- Aster
- edgeX
- Lighter
- GRVT

## セットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## 実行例
```bash
python crawlers/hyperliquid/crawl_hyperliquid_docs.py
python crawlers/aster/crawl_aster_docs.py
python crawlers/edgex/crawl_edgex_docs.py
python crawlers/lighter/crawl_lighter_docs.py
python crawlers/grvt/crawl_grvt_docs.py
```

## 共有クロールエンジン
`crawlers/common/perpdex_crawler.py`

- 再帰的に内部リンクを辿る
- 生HTMLを保存（正規化なし）
- 各ページのメタデータJSONを保存
- クロールサマリを保存

詳細な想定サイト構造や制約は各取引所の `SPEC.md` を参照してください。
