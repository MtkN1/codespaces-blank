# Aster Docs Crawler 仕様

## 対象
- Exchange: Aster
- Seed URL: `https://asterdex.org/docs/`
- 許可ドメイン: `asterdex.org`
- 許可パス: `/docs`

## サイト構造の想定
- ブランド/LP配下の docs セクション
- ルーティングはSPA風になる可能性あり
- bot対策（Cloudflare）でHTTPクライアント単体は失敗しうる

## クロール方針
- Playwright でブラウザレンダリング後にリンク抽出
- docs配下のみ再帰巡回
- 生HTMLを保存（加工なし）

## 出力
- `outputs/aster/raw_html/*.html`
- `outputs/aster/metadata/*.json`
- `outputs/aster/url_index.jsonl`
- `outputs/aster/crawl_summary.json`

## 実行
```bash
python crawlers/aster/crawl_aster_docs.py
```
