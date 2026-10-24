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

```mermaid
flowchart LR
    U(("あなた"))
    subgraph screens["画面 (クライアント)"]
      E["エディタ<br/>Zed / JetBrains"]
      W["VS Code<br/>ブラウザ"]
    end
    H["エージェントホスト"]
    A["自分の<br/>エージェント"]
    R["他人の<br/>エージェント"]
    T[("道具<br/>DB / API")]

    U --> E & W
    E -- "ACP" --> A
    W -- "AHP" --> H
    H -- "ACP など" --> A
    A -- "A2A" --> R
    A -- "MCP" --> T

    linkStyle 2 stroke:#e8590c,stroke-width:3px
    linkStyle 3 stroke:#2f9e44,stroke-width:3px
    linkStyle 5 stroke:#1c7ed6,stroke-width:3px
    linkStyle 6 stroke:#6b7280,stroke-width:2px,stroke-dasharray:4
```

!!! tip "まずはここだけ覚えれば OK"
    | プロトコル | つなぐもの | 関係 | ひとことで |
    |---|---|---|---|
    | <span class="badge acp">ACP</span> | エディタ ⇄ エージェント | 1 対 1 | エージェント版の LSP |
    | <span class="badge a2a">A2A</span> | エージェント ⇄ エージェント | 対等 | 他社の同僚に頼む窓口 |
    | <span class="badge ahp">AHP</span> | 複数の画面 ⇄ ホスト | N 対 1 | セッションの共有ノート |
    | <span class="badge mcp">MCP</span> (参考) | エージェント ⇄ 道具 | 1 対 多 | 道具箱の差込口 |

## 学習ロードマップ

```mermaid
flowchart LR
    B["第 1 章<br/>基礎<br/><small>なぜ必要? / 共通の土台</small>"] --> ACP["第 2 章<br/>ACP"]
    ACP --> A2A["第 3 章<br/>A2A"]
    A2A --> AHP["第 4 章<br/>AHP"]
    AHP --> P["第 5 章<br/>実践<br/><small>選び方 / 組み合わせ / 安全</small>"]
    P --> Q["付録<br/>理解度チェック"]

    style ACP fill:#e8590c,color:#fff,stroke:#e8590c
    style A2A fill:#1c7ed6,color:#fff,stroke:#1c7ed6
    style AHP fill:#2f9e44,color:#fff,stroke:#2f9e44
```

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
