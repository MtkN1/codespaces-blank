# 1 ターンの流れ

<p class="oneliner">「バグを直して」と頼んでから、エージェントが「直しました」と言うまでに、裏で何が起きているかを追いかけます。</p>

## 全体の 3 段階

```mermaid
flowchart LR
    I["① 準備<br/>initialize"] --> S["② 会話を開く<br/>session/new"] --> P["③ 依頼する<br/>session/prompt"]
    P -->|"次の依頼"| P
    style P fill:#e8590c,color:#fff,stroke:#e8590c
```

### ① initialize: 自己紹介

```mermaid
sequenceDiagram
    participant E as エディタ
    participant A as エージェント
    E->>A: initialize (バージョン 1, 「ファイル読み書きと端末を貸せます」)
    A-->>E: (バージョン 1, 「画像も読めます・会話の再開もできます」)
```

お互いに**できること (capabilities)** を申告します。相手ができないことは頼みません。

### ② session/new: 会話を開く

```mermaid
sequenceDiagram
    participant E as エディタ
    participant A as エージェント
    E->>A: session/new (作業フォルダ, 使ってほしい MCP サーバー)
    A-->>E: sessionId = "sess_abc", モード一覧
```

1 つの接続で、**複数の会話 (セッション)** を同時に持てます。エディタに設定した MCP サーバーも、ここでエージェントに渡されます。

### ③ session/prompt: 依頼する (詳しい流れ)

```mermaid
sequenceDiagram
    autonumber
    actor U as あなた
    participant E as エディタ (Client)
    participant A as エージェント (Agent)
    participant L as LLM

    U->>E: 「バグを直して」
    E->>A: session/prompt
    A->>L: 考えて
    A--)E: session/update (plan: 計画)
    A->>E: fs/read_text_file (main.py)
    E-->>A: ファイルの中身
    A--)E: session/update (agent_message_chunk: 「読みました」)
    A--)E: session/update (tool_call: 「main.py を編集」pending)
    A->>E: session/request_permission
    E->>U: 許可ダイアログ
    U->>E: 許可
    E-->>A: allow_once
    A--)E: session/update (tool_call_update: in_progress)
    A->>E: fs/write_text_file
    A--)E: session/update (tool_call_update: completed)
    A--)E: session/update (agent_message_chunk: 「直しました!」)
    A-->>E: session/prompt の返事 (stopReason: end_turn)
```

!!! tip "見分け方"
    - **実線の矢印**は Request。返事を待ちます。
    - **点線で先が塗りつぶされた矢印**は、その Request への返事 (Response) です。
    - **点線で先が開いた矢印**は Notification。画面に流すだけで、返事はありません。
    - `session/prompt` の**返事はターンの最後**に来ます。途中経過は全部 `session/update` で届きます。

## 画面に届く「途中経過」の種類

`session/update` には種類があり、エディタはそれぞれを違う見た目で表示します。

| 種類 | 画面での見え方 | 例 |
|---|---|---|
| `agent_message_chunk` | 返答の文章が少しずつ出る | 「原因は…」 |
| `agent_thought_chunk` | 考えている内容 (折りたたみ) | 「まずテストを…」 |
| `plan` | チェックリスト | ☐ 読む ☐ 直す ☐ テスト |
| `tool_call` / `tool_call_update` | ツールの実行状況 | 📝 main.py を編集 … ✅ |
| `current_mode_update` | モード表示が変わる | ask → code |
| `usage_update` | 使ったトークン量・コスト | 12k / 200k |

ツール呼び出しは、次のように状態が移り変わります。

```mermaid
stateDiagram-v2
    direction LR
    [*] --> pending: tool_call
    pending --> in_progress: 許可された / 確認不要
    pending --> failed: 拒否された
    in_progress --> completed: 成功
    in_progress --> failed: エラー
    completed --> [*]
    failed --> [*]
```

## ターンの終わり方 (stopReason)

```mermaid
flowchart LR
    T(["ターン"]) --> e1["end_turn<br/>普通に完了"]
    T --> e2["max_tokens<br/>トークン上限"]
    T --> e3["max_turn_requests<br/>LLM 呼び出し回数の上限"]
    T --> e4["refusal<br/>エージェントが断った"]
    T --> e5["cancelled<br/>あなたが止めた"]
    style e1 fill:#2f9e44,color:#fff,stroke:#2f9e44
```

途中で止めたいときは、エディタが `session/cancel` (Notification) を送ります。エージェントは作業を止めて、`cancelled` で返事をします。

## コードで動かしてみる

上の図の流れを、そのまま Python にしたものです。**部品 (語彙) → エージェント → エディタと実行**の順に読んでください。

??? note "部品: 途中経過の型 (クリックで開く)"
    ```python
    --8<-- "acp/acp_model.py:vocab"
    ```

    ```python
    --8<-- "acp/acp_model.py:updates"
    ```

**エージェント側** (LLM の代わりに決め打ちで動きます)

```python
--8<-- "acp/acp_model.py:agent"
```

**エディタ側と実行**

```python
--8<-- "acp/acp_model.py:editor"
```

??? success "実行結果"
    ```text
      UI <- Plan(entries=['main.py を読む', 'バグを直す'])
      UI <- AgentMessageChunk(text='11 文字読みました。')
      UI <- ToolCall(tool_call_id='call_1', title='main.py を編集', kind='edit', status='pending')
      ダイアログ: 「main.py を編集」を許可しますか? ['許可', '拒否']
      UI <- ToolCallUpdate(tool_call_id='call_1', status='in_progress')
      UI <- ToolCallUpdate(tool_call_id='call_1', status='completed')
      UI <- AgentMessageChunk(text='直しました!')
    stopReason: end_turn / main.py = print('hi')
    ```

!!! question "考えてみよう"
    `MiniEditor(auto_allow=False)` にすると、何が起きるでしょうか? `main.py` の中身はどうなりますか?

    ??? success "答え"
        `request_permission` が `"reject"` を返すので、エージェントはツール呼び出しを `failed` にして、ファイルを書き換えずにターンを終えます。`main.py` は `pritn('hi')` のままです。
        **人が拒否すれば、エージェントは何も変えられない**。これが ACP の安全の要です。

[次へ: ACP を使ってみる :material-arrow-right:](hands-on.md){ .md-button .md-button--primary }
