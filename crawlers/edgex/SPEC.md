# edgeX Docs Crawler 仕様

## 対象
- Exchange: edgeX
- Seed URL: `https://docs.edgex.exchange/`
- 許可ドメイン: `docs.edgex.exchange`
- 許可パス: `/`

## サイト構造の想定
- 専用 docs サブドメイン
- ドキュメントページは複数階層
- JS描画/遅延ロードの可能性あり

## クロール方針
- Playwright + 再帰リンク探索
- 同一サブドメイン内のみ巡回
- 失敗ページは `crawl_summary.json` の `failed` に記録

## 出力
- `outputs/edgex/raw_html/*.html`
- `outputs/edgex/metadata/*.json`
- `outputs/edgex/url_index.jsonl`
- `outputs/edgex/crawl_summary.json`

## 実行
```bash
python crawlers/edgex/crawl_edgex_docs.py
```
