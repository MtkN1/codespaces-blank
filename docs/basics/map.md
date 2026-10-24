# 全体地図

<p class="oneliner">4 つのプロトコルは競合関係ではありません。担当する「つなぎ目」が違うので、<b>組み合わせて使う</b>ものです。</p>

## 向きで覚える

```mermaid
flowchart TB
    subgraph top["上: 人の側"]
      S1["画面 1"] & S2["画面 2"] & S3["画面 3"]
    end
    H["ホスト"]
    ED["エディタ"]
    A["エージェント"]
    R1["他のエージェント"]
    R2["他のエージェント"]
    subgraph bottom["下: 道具の側"]
      T1[("DB")] & T2[("API")]
    end

    S1 & S2 & S3 <-->|AHP| H
    H <-->|ACP| A
    ED <-->|ACP| A
    A <-->|A2A| R1
    A <-->|A2A| R2
    A -->|MCP| T1 & T2
```

- **縦 (上)**: 人が触る画面とエージェントをつなぐ → <span class="badge acp">ACP</span> <span class="badge ahp">AHP</span>
- **横**: エージェント同士をつなぐ → <span class="badge a2a">A2A</span>
- **縦 (下)**: エージェントに道具を持たせる → <span class="badge mcp">MCP</span>

## 4 つを並べて比べる

| | <span class="badge acp">ACP</span> | <span class="badge a2a">A2A</span> | <span class="badge ahp">AHP</span> | <span class="badge mcp">MCP</span> |
|---|---|---|---|---|
| 正式名 | Agent Client Protocol | Agent2Agent Protocol | Agent Host Protocol | Model Context Protocol |
| つなぐもの | エディタ ⇄ エージェント | エージェント ⇄ エージェント | 複数のクライアント ⇄ ホスト | エージェント ⇄ 道具 |
| 数の関係 | 1 対 1 | 対等 (多対多) | N 対 1 | 1 対 多 |
| 相手の中身 | 信頼して任せる | **見えない (opaque)** | ホストが代表する | 道具として見える |
| 主な運び方 | stdio (ローカル) | HTTP(S) / SSE / gRPC | WebSocket / MessagePort | stdio / HTTP |
| 中心になる概念 | セッションとターン | **タスク**と成果物 | **状態**とアクション | ツールとリソース |
| 主な推進者 | Zed, JetBrains ほか | Linux Foundation (旧 Google) | Microsoft (VS Code) | Anthropic → Linux Foundation |
| 似ているもの | LSP | 外注・業務委託 | Google ドキュメントの共同編集 | USB ポート |

## 時系列で見る

```mermaid
timeline
    title エージェントプロトコルの歩み
    2024-11 : MCP 公開
    2025-04 : A2A 公開 (Google)
    2025-06 : A2A が Linux Foundation へ
    2025-08 : ACP (Zed) 公開 : IBM の ACP が A2A に合流
    2026-01 : ACP Registry 開始
    2026-03 : A2A v1.0 確定
    2026-07 : ACP v2 ドラフト : VS Code に Agent Host 登場
    2026-10 : AHP 1.0.0
```

!!! danger "名前の衝突に注意: 「ACP」は 2 つある"
    | | Agent **Client** Protocol | Agent **Communication** Protocol |
    |---|---|---|
    | 作ったところ | Zed など | IBM (BeeAI) |
    | 目的 | エディタ ⇄ エージェント | エージェント ⇄ エージェント |
    | 現在 | **活発に開発中** (このサイトの ACP) | 2025 年 8 月に **A2A へ合流**して開発終了 |

    2025 年前半の記事で「ACP」とあれば、IBM の方を指していることが多いです。
    このサイトの「ACP」は、すべて **Agent Client Protocol** を指します。

## 判断に迷ったら

```mermaid
flowchart TD
    Q{"何をつなぎたい?"}
    Q -->|"エディタと<br/>コーディングエージェント"| ACP["ACP"]
    Q -->|"自分のエージェントと<br/>他人のエージェント"| A2A["A2A"]
    Q -->|"1 つのセッションと<br/>複数の画面"| AHP["AHP"]
    Q -->|"エージェントと<br/>DB や API"| MCP["MCP"]
    style ACP fill:#e8590c,color:#fff,stroke:#e8590c
    style A2A fill:#1c7ed6,color:#fff,stroke:#1c7ed6
    style AHP fill:#2f9e44,color:#fff,stroke:#2f9e44
    style MCP fill:#6b7280,color:#fff,stroke:#6b7280
```

詳しい選び方は [第 5 章 選び方](../practice/choose.md) で扱います。まずは身近な ACP から見ていきましょう。

[次へ: 第 2 章 ACP :material-arrow-right:](../acp/index.md){ .md-button .md-button--primary }
