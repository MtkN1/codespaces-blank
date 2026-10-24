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

# Mermaid の読み込み先を正確なバージョンに固定する (CDN の範囲指定を避ける)
sed -i 's#unpkg.com/mermaid@11/#unpkg.com/mermaid@11.4.1/#g' site/assets/javascripts/bundle.*.min.js
! grep -rq 'mermaid@11/' site
