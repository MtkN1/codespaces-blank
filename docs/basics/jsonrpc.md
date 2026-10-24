# 共通の土台 JSON-RPC

<p class="oneliner">A2A・ACP・AHP は、どれも <b>JSON-RPC 2.0</b> という同じ「話し方」を使っています。ここを押さえると、3 つとも読めるようになります。</p>

## 「中身」と「運び方」は別物

```mermaid
flowchart TB
    subgraph content["中身: JSON-RPC 2.0 (共通)"]
      M["{ jsonrpc: '2.0', id: 1, method: 'session/prompt', params: {...} }"]
    end
    subgraph transport["運び方: プロトコルごとに違う"]
      direction LR
      T1["標準入出力 (stdio)<br/>ACP"]
      T2["HTTP / SSE<br/>A2A"]
      T3["WebSocket<br/>AHP"]
    end
    content --> transport
    style T1 fill:#e8590c,color:#fff,stroke:#e8590c
    style T2 fill:#1c7ed6,color:#fff,stroke:#1c7ed6
    style T3 fill:#2f9e44,color:#fff,stroke:#2f9e44
```

手紙に例えると、**JSON-RPC が便箋の書式**で、**stdio / HTTP / WebSocket が郵便・宅配便・バイク便**です。

## メッセージは 3 種類だけ

```mermaid
sequenceDiagram
    participant A as 呼ぶ側
    participant B as 呼ばれる側
    A->>B: Request (id: 1, method: "add")
    B-->>A: Response (id: 1, result: 5)
    Note over A,B: id で「どの質問への答えか」を対応づける
    B--)A: Notification (id 無し, method: "progress")
    Note over A,B: 返事のいらない一方通行のお知らせ
```

| 種類 | id | 返事 | 使いどころ |
|---|---|---|---|
| **Request** | あり | 必要 | 「これをして、結果を教えて」 |
| **Response** | Request と同じ | — | 結果 (`result`) か失敗 (`error`) |
| **Notification** | なし | 不要 | 途中経過の連絡、キャンセルなど |

!!! tip "これだけ覚えると仕様が読める"
    各プロトコルの仕様書は、ほぼ「**どんな `method` があり、`params` に何を入れ、何が返るか**」の一覧です。
    - ACP: `session/prompt` (Request)、`session/update` (Notification)
    - A2A: `SendMessage` (Request)
    - AHP: `subscribe` (Request)、`dispatchAction` (Notification)

## コードで見る

**メッセージの形** (`TypedDict` で JSON の形を表しています)

```python
--8<-- "basics/jsonrpc.py:messages"
```

**運び方は Protocol で差し替えられる**

```python
--8<-- "basics/jsonrpc.py:transport"
```

**試しに足し算サーバーを呼んでみる**

```python
--8<-- "basics/jsonrpc.py:loopback"
```

`call()` は `Transport` という**形**しか知りません。`LoopbackTransport` を、stdio や WebSocket の実装に入れ替えても、そのまま動きます。

## 双方向という大事な性質

JSON-RPC では、**どちらの側からも** Request を送れます。これが特に ACP と AHP で効いてきます。

```mermaid
sequenceDiagram
    participant E as エディタ
    participant A as エージェント
    E->>A: Request: session/prompt「バグを直して」
    A--)E: Notification: session/update「考え中…」
    A->>E: Request: session/request_permission「ファイルを書き換えていい?」
    E-->>A: Response: 「許可」
    A-->>E: Response: stopReason = end_turn
```

普通の Web API は「クライアントが聞いてサーバーが答える」一方向です。エージェントのプロトコルでは、**エージェントの側から人間に確認を求める**ことがよくあるので、双方向が重要になります。

[次へ: 全体地図 :material-arrow-right:](map.md){ .md-button .md-button--primary }
