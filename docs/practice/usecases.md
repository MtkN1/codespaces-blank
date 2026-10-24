# ユースケース集

<p class="oneliner">よくある「やりたいこと」を、どのプロトコルで実現するかを図で示します。自分の状況に近いものを探してみてください。</p>

## 1. 普段のエディタで、最新のエージェントを試したい

<span class="badge acp">ACP</span>

```mermaid
flowchart LR
    U(("開発者")) --> J["JetBrains IDE"]
    J -- "ACP" --> A1["Claude Code"]
    J -- "ACP" --> A2["Codex CLI"]
    J -- "ACP" --> A3["Gemini CLI"]
    linkStyle 1,2,3 stroke:#e8590c,stroke-width:3px
```

**やること**: ACP Registry からエージェントを入れて、チャット画面で切り替えるだけ。
**ポイント**: エディタを乗り換えずに、エージェントだけを比べられます。

---

## 2. 長い作業を任せて、外出先から様子を見たい

<span class="badge ahp">AHP</span> + <span class="badge acp">ACP</span>

```mermaid
flowchart LR
    subgraph office["開発機"]
      H["Agent Host<br/>code agent host"] --> A["エージェント"]
    end
    PC["💻 会社の VS Code"] -- "AHP" --> H
    B["🌐 自宅のブラウザ"] -- "AHP" --> H
    linkStyle 1,2 stroke:#2f9e44,stroke-width:3px
```

**やること**: 開発機で Agent Host を動かし、セッションを始める。外出先からはブラウザでつなぐ。
**ポイント**: 実行の承認が必要になったら、どの画面からでも答えられます。

---

## 3. 社内の専門エージェントを組み合わせたい

<span class="badge a2a">A2A</span>

```mermaid
flowchart LR
    U(("社員")) --> C["社内ポータルの<br/>窓口エージェント"]
    C -- "A2A" --> HR["人事部の<br/>休暇申請エージェント"]
    C -- "A2A" --> IT["情シスの<br/>PC 手配エージェント"]
    C -- "A2A" --> FIN["経理の<br/>経費精算エージェント"]
    linkStyle 1,2,3 stroke:#1c7ed6,stroke-width:3px
```

**やること**: 各部署がエージェントを A2A で公開し、窓口エージェントがスキルを見て振り分ける。
**ポイント**: 部署ごとに別の LLM・別のフレームワークで作られていても、名刺さえあれば連携できます。

---

## 4. 外部の専門サービスに一部の仕事を外注したい

<span class="badge a2a">A2A</span> + <span class="badge mcp">MCP</span>

```mermaid
flowchart LR
    Me["自分のリサーチ<br/>エージェント"] -- "MCP" --> DB[("社内 DB")]
    Me -- "A2A + OAuth" --> T["翻訳会社の<br/>翻訳エージェント"]
    Me -- "A2A + OAuth" --> L["法律事務所の<br/>契約チェックエージェント"]
    linkStyle 0 stroke:#6b7280,stroke-width:2px
    linkStyle 1,2 stroke:#1c7ed6,stroke-width:3px
```

**やること**: 相手の名刺の認証方式に従ってトークンを取り、A2A で依頼する。社内データは MCP で読む。
**ポイント**: 相手は opaque なので、**社内データの何を渡すか**は自分の側で決めて絞り込みます。

---

## 5. 何日もかかるバッチ処理を頼みたい

<span class="badge a2a">A2A</span> (プッシュ通知)

```mermaid
sequenceDiagram
    participant Me as 自分のシステム
    participant R as データ分析エージェント
    Me->>R: SendMessage + 通知先 Webhook
    R-->>Me: Task (WORKING)
    Note over Me,R: …数日後…
    R->>Me: Webhook: 完了しました
    Me->>R: GetTask → Artifact (分析レポート)
```

**やること**: 相手の名刺で `pushNotifications: true` を確認し、通知先を渡して依頼する。
**ポイント**: 接続を開いたまま待つ必要がありません。

---

## 6. チームで 1 つのエージェント作業を見守りたい

<span class="badge ahp">AHP</span>

```mermaid
flowchart LR
    A["Aさん<br/>(依頼した人)"] -- "AHP" --> H["共有の Agent Host"]
    B["Bさん<br/>(レビュー担当)"] -- "AHP" --> H
    C["承認ボット"] -- "AHP" --> H
    linkStyle 0,1,2 stroke:#2f9e44,stroke-width:3px
```

**やること**: 共有のホストにセッションを置き、全員がそのチャンネルを購読する。
**ポイント**: 誰が承認したか、どの順番で何が起きたかが、通し番号つきで全員に同じように見えます。

---

!!! question "自分のユースケースを整理するワーク"
    次の 4 つを紙に書き出してみましょう。

    1. **誰が** (人? システム?) 使うか
    2. **どの画面**から使うか (エディタ? ブラウザ? 複数?)
    3. **誰に**仕事をさせるか (自分のエージェント? 他人のエージェント?)
    4. **何を**道具として使わせるか (DB? API? ファイル?)

    2 → ACP / AHP、3 → A2A、4 → MCP と対応させれば、必要なプロトコルが揃います。

[次へ: 組み合わせる :material-arrow-right:](combine.md){ .md-button .md-button--primary }
