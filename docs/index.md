# エージェントプロトコル入門

<p class="oneliner">AI エージェント同士、エージェントとエディタ、エージェントと画面をつなぐ「共通の約束」を、図とコードで学ぶサイトです。</p>

## このサイトで分かるようになること

<div class="cards" markdown>
<div class="acp" markdown>
<span class="badge acp">ACP</span> **Agent Client Protocol**

好きな**エディタ**から、好きな**コーディングエージェント**を使う
</div>
<div class="a2a" markdown>
<span class="badge a2a">A2A</span> **Agent2Agent Protocol**

自分のエージェントから、**他人のエージェント**に仕事を頼む
</div>
<div class="ahp" markdown>
<span class="badge ahp">AHP</span> **Agent Host Protocol**

1 つのセッションを、**複数の画面や端末**から同時に見て操作する
</div>
</div>

## 1 枚で見る全体像

<div class="figure">
<svg class="pd" viewBox="0 0 860 300" role="img" aria-label="あなたが画面からエージェントを使い、エージェントが他人のエージェントや道具とつながる全体像">
  <defs>
    <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" class="pd-head"/></marker>
    <marker id="ah-acp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" class="pd-head acp"/></marker>
    <marker id="ah-ahp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" class="pd-head ahp"/></marker>
    <marker id="ah-a2a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" class="pd-head a2a"/></marker>
    <marker id="ah-mcp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" class="pd-head mcp"/></marker>
  </defs>
  <rect class="pd-group" x="88" y="22" width="184" height="256" rx="10"/>
  <text class="pd-cap" x="180" y="42">画面 (クライアント)</text>
  <circle class="pd-box" cx="40" cy="150" r="30"/>
  <text class="pd-t" x="40" y="155">あなた</text>
  <rect class="pd-box" x="105" y="58" width="150" height="56" rx="6"/>
  <text class="pd-t" x="180" y="82">エディタ</text>
  <text class="pd-s" x="180" y="102">Zed / JetBrains</text>
  <rect class="pd-box" x="105" y="200" width="150" height="56" rx="6"/>
  <text class="pd-t" x="180" y="224">VS Code</text>
  <text class="pd-s" x="180" y="244">ブラウザ</text>
  <rect class="pd-box" x="330" y="200" width="150" height="56" rx="6"/>
  <text class="pd-t" x="405" y="233">エージェントホスト</text>
  <rect class="pd-box pd-strong" x="530" y="118" width="130" height="64" rx="6"/>
  <text class="pd-t" x="595" y="145">自分の</text>
  <text class="pd-t" x="595" y="166">エージェント</text>
  <rect class="pd-box" x="710" y="40" width="130" height="56" rx="6"/>
  <text class="pd-t" x="775" y="64">他人の</text>
  <text class="pd-t" x="775" y="84">エージェント</text>
  <rect class="pd-box" x="710" y="200" width="130" height="56" rx="6"/>
  <text class="pd-t" x="775" y="224">道具</text>
  <text class="pd-s" x="775" y="244">DB / API</text>

  <path class="pd-e" d="M68 138 L103 96" marker-end="url(#ah)"/>
  <path class="pd-e" d="M68 162 L103 210" marker-end="url(#ah)"/>
  <path class="pd-e acp" d="M255 86 C390 86 450 134 528 140" marker-end="url(#ah-acp)"/>
  <path class="pd-e ahp" d="M255 228 L328 228" marker-end="url(#ah-ahp)"/>
  <path class="pd-e acp dash" d="M480 222 C510 210 515 185 540 182" marker-end="url(#ah-acp)"/>
  <path class="pd-e a2a" d="M660 132 L708 80" marker-end="url(#ah-a2a)"/>
  <path class="pd-e mcp dash" d="M660 168 L708 214" marker-end="url(#ah-mcp)"/>

  <g class="pd-label acp"><rect x="370" y="94" width="48" height="22" rx="11"/><text x="394" y="110">ACP</text></g>
  <g class="pd-label ahp"><rect x="268" y="204" width="48" height="22" rx="11"/><text x="292" y="220">AHP</text></g>
  <g class="pd-label acp"><rect x="470" y="246" width="78" height="22" rx="11"/><text x="509" y="262">ACP など</text></g>
  <g class="pd-label a2a"><rect x="664" y="82" width="48" height="22" rx="11"/><text x="688" y="98">A2A</text></g>
  <g class="pd-label mcp"><rect x="664" y="200" width="48" height="22" rx="11"/><text x="688" y="216">MCP</text></g>
</svg>
</div>

!!! tip "まずはここだけ覚えれば OK"
    | プロトコル | つなぐもの | 関係 | ひとことで |
    |---|---|---|---|
    | <span class="badge acp">ACP</span> | エディタ ⇄ エージェント | 1 対 1 | エージェント版の LSP |
    | <span class="badge a2a">A2A</span> | エージェント ⇄ エージェント | 対等 | 他社の同僚に頼む窓口 |
    | <span class="badge ahp">AHP</span> | 複数の画面 ⇄ ホスト | N 対 1 | セッションの共有ノート |
    | <span class="badge mcp">MCP</span> (参考) | エージェント ⇄ 道具 | 1 対 多 | 道具箱の差込口 |

## 学習ロードマップ

<ol class="roadmap">
  <li><a href="basics/index.html"><b>第 1 章 基礎</b><span>なぜ必要? / 共通の土台</span></a></li>
  <li class="acp"><a href="acp/index.html"><b>第 2 章 ACP</b><span>エディタ ⇄ エージェント</span></a></li>
  <li class="a2a"><a href="a2a/index.html"><b>第 3 章 A2A</b><span>エージェント ⇄ エージェント</span></a></li>
  <li class="ahp"><a href="ahp/index.html"><b>第 4 章 AHP</b><span>複数の画面 ⇄ ホスト</span></a></li>
  <li><a href="practice/choose.html"><b>第 5 章 実践</b><span>選び方 / 組み合わせ / 安全</span></a></li>
  <li><a href="appendix/quiz.html"><b>付録</b><span>理解度チェック</span></a></li>
</ol>

各章は同じ並びになっています。

1. **概要**: 何のためのものか、誰と誰をつなぐか
2. **仕組み**: シーケンス図と `typing.Protocol` のコードで、やり取りを追う
3. **使ってみる**: ユーザーとして使い始める手順と、つまずきやすい点

## このサイトの読み方

!!! info "対象読者とゴール"
    - **前提知識**: Python を少し読める。JSON を見たことがある。プロトコルの知識はゼロで OK。
    - **ゴール**: 各プロトコルの役割と動きを説明でき、**自分のやりたいことに合うものを選んで使い始められる**こと。
    - **扱わないこと**: プロトコルそのものの実装者や SDK 開発者になるための詳細 (全メソッドの仕様、ワイヤーフォーマットの細部など) は扱いません。

??? question "なぜ Python の `typing.Protocol` で説明するの?"
    プロトコルの本質は「**相手が何者かは知らなくていい。この形の窓口さえあれば話せる**」という約束です。
    これは Python の `typing.Protocol` (構造的部分型) の考え方とまったく同じです。
    窓口の形をコードにすると、長い説明文よりも正確に、短く伝えられます。詳しくは [typing.Protocol で考える](basics/typing-protocol.md) で説明します。

    サイト内のコードはすべて実際に動き、`mypy --strict` の型チェックも通ることを確認しています。

!!! warning "情報の時点"
    内容は **2026 年 10 月時点** の公式資料に基づいています。

    - A2A **v1.0** (2026 年 3 月に確定)
    - ACP **v1** (安定版。v2 は 2026 年 7 月にドラフト公開)
    - AHP **1.0.0** (2026 年 10 月 2 日リリース)

    どれも動きの速い分野です。実際に使う前に [参考リンク](appendix/links.md) の公式ドキュメントも確認してください。
