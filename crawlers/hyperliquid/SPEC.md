# Hyperliquid Docs Crawler 仕様

## 対象
- Exchange: Hyperliquid
- Seed URL: `https://hyperliquid.gitbook.io/hyperliquid-docs`
- 許可ドメイン: `hyperliquid.gitbook.io`
- 許可パス: `/hyperliquid-docs`

## サイト構造の想定
- GitBook ベース（クライアントサイド描画を含む）
- 左ナビから多数ページへ内部リンク展開
- 一部でクエリ付きURLやアンカーリンクが出る

## クロール方針
- Playwright Chromium で `networkidle` まで待機
- `a[href]` を再帰収集（同一ドメイン・許可パスのみ）
- URLフラグメント（`#...`）は除去して重複防止
- 生HTMLをそのまま保存（正規化なし）

## 出力
- `outputs/hyperliquid/raw_html/*.html` 生HTML
- `outputs/hyperliquid/metadata/*.json` ページごとのメタ
- `outputs/hyperliquid/url_index.jsonl` 取得ログ
- `outputs/hyperliquid/crawl_summary.json` サマリ

## 実行
```bash
python crawlers/hyperliquid/crawl_hyperliquid_docs.py
```
