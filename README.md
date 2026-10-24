# エージェントプロトコル入門

A2A・AHP・ACP をゼロから学び、ユーザーとして自分のユースケースで使えるようになるための図解学習サイトです。[Zensical](https://zensical.org/) で作っています。

## ビルド

```bash
python -m venv .venv
.venv/bin/pip install zensical mypy   # Node.js と Playwright (Chromium) も必要
PATH=$PWD/.venv/bin:$PATH ./build.sh   # site/ に出力
```

`build.sh` は、サイトに載せている `examples/` のコードを実行し、`mypy --strict` で型チェックしてからビルドします。

## 構成

- `docs/`: ページ (Markdown)
- `examples/`: ページに埋め込む `typing.Protocol` の概念コード (`--8<--` で読み込み)
- `tools/mermaid-to-svg.js`: ビルド後に Mermaid 図を静的 SVG (ライト用・ダーク用) に変換する
- `zensical.toml`: サイト設定
