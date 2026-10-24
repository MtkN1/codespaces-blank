#!/usr/bin/env bash
# サイトをビルドし、アーティファクトとして公開できる形に整える。
set -euo pipefail
cd "$(dirname "$0")"

# 載せているコードが動き、型チェックを通ることを確認する
for f in examples/basics/*.py examples/acp/*.py examples/a2a/a2a_model.py examples/ahp/*.py examples/practice/*.py; do
  python "$f" > /dev/null
done
mypy --strict --ignore-missing-imports examples/

rm -rf site
zensical build

# Mermaid 図をビルド時に静的な SVG にする (閲覧時に JavaScript や CDN を使わない)
(cd tools && npm ci --silent --no-audit --no-fund)
node tools/mermaid-to-svg.js site
! grep -rq '<pre class="mermaid">' site
