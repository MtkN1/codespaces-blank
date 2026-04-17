# GRVT Docs Crawler 仕様

## 対象
- Exchange: GRVT
- Seed URL: `https://docs.grvt.io/`
- 許可ドメイン: `docs.grvt.io`
- 許可パス: `/`

## サイト構造の想定
- docs専用サブドメイン
- JSレンダリング + ナビゲーションリンク
- 環境によってbot対策で変動の可能性

## クロール方針
- Playwrightブラウザによるページ取得
- `a[href]` から同一ドメインリンクを再帰取得
- 取得失敗はログ化して継続

## 出力
- `outputs/grvt/raw_html/*.html`
- `outputs/grvt/metadata/*.json`
- `outputs/grvt/url_index.jsonl`
- `outputs/grvt/crawl_summary.json`

## 実行
```bash
python crawlers/grvt/crawl_grvt_docs.py
```
