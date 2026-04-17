# Lighter Docs Crawler 仕様

## 対象
- Exchange: Lighter
- Seed URL: `https://docs.lighter.xyz/`
- 許可ドメイン: `docs.lighter.xyz`
- 許可パス: `/`

## サイト構造の想定
- docs専用サブドメイン
- 動的ルーティングを含む可能性
- 一部ページはSSR/静的混在の可能性

## クロール方針
- PlaywrightでDOM確定後にリンク収集
- 許可ドメイン内を再帰巡回
- 生HTMLを保持し、正規化・抽出は行わない

## 出力
- `outputs/lighter/raw_html/*.html`
- `outputs/lighter/metadata/*.json`
- `outputs/lighter/url_index.jsonl`
- `outputs/lighter/crawl_summary.json`

## 実行
```bash
python crawlers/lighter/crawl_lighter_docs.py
```
