# チートシート

## 3 つを 1 枚で

<div class="cards" markdown>
<div class="acp" markdown>
<span class="badge acp">ACP</span> **Agent Client Protocol**

- **つなぐ**: エディタ ⇄ エージェント (1 対 1)
- **運び方**: stdio (子プロセス)
- **中心**: セッションとターン
- **流れ**: `initialize` → `session/new` → `session/prompt` ⇄ `session/update`
- **止め方**: `session/cancel`
- **確認**: `session/request_permission`
</div>
<div class="a2a" markdown>
<span class="badge a2a">A2A</span> **Agent2Agent Protocol**

- **つなぐ**: エージェント ⇄ エージェント (対等)
- **運び方**: HTTPS (JSON-RPC / gRPC / REST)、SSE
- **中心**: タスクと成果物
- **流れ**: 名刺を取得 → `SendMessage` → `GetTask`
- **止め方**: `CancelTask`
- **名刺**: `/.well-known/agent-card.json`
</div>
<div class="ahp" markdown>
<span class="badge ahp">AHP</span> **Agent Host Protocol**

- **つなぐ**: 複数の画面 ⇄ ホスト (N 対 1)
- **運び方**: WebSocket / MessagePort
- **中心**: 状態とアクション
- **流れ**: `initialize` → `subscribe` → スナップショット → `action` …
- **操作**: `dispatchAction`
- **代表例**: VS Code の Agent Host
</div>
</div>

## ACP の早見表

| やりたいこと | メソッド | 向き |
|---|---|---|
| 接続して能力を交換 | `initialize` | エディタ → エージェント |
| 新しい会話 / 再開 | `session/new` / `session/load` | エディタ → エージェント |
| 依頼する | `session/prompt` | エディタ → エージェント |
| 中断する | `session/cancel` (通知) | エディタ → エージェント |
| 途中経過を見せる | `session/update` (通知) | エージェント → エディタ |
| 許可を取る | `session/request_permission` | エージェント → エディタ |
| ファイルを読む / 書く | `fs/read_text_file` / `fs/write_text_file` | エージェント → エディタ |
| 端末を使う | `terminal/create` ほか | エージェント → エディタ |

**stopReason**: `end_turn` / `max_tokens` / `max_turn_requests` / `refusal` / `cancelled`

## A2A の早見表

| やりたいこと | 操作 (v1.0) | v0.3 の名前 |
|---|---|---|
| 依頼する | `SendMessage` | `message/send` |
| 依頼して途中経過を受け取る | `SendStreamingMessage` | `message/stream` |
| 状態を見る | `GetTask` | `tasks/get` |
| 一覧を見る | `ListTasks` | (なし) |
| 取り消す | `CancelTask` | `tasks/cancel` |
| 途中経過を再購読 | `SubscribeToTask` | `tasks/resubscribe` |
| 詳しい名刺 | `GetExtendedAgentCard` | `agent/getAuthenticatedExtendedCard` |

**TaskState**: `SUBMITTED` → `WORKING` → (`INPUT_REQUIRED` / `AUTH_REQUIRED`) → `COMPLETED` / `FAILED` / `CANCELED` / `REJECTED` (すべて `TASK_STATE_` で始まる)

```bash title="最小の curl"
curl -s $URL -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":
       {"role":"ROLE_USER","messageId":"m1","parts":[{"text":"hello"}]}}}'
```

## AHP の早見表

| 用語 | 意味 |
|---|---|
| `ahp-root://` | ルート (エージェント一覧など) |
| `ahp-session:/<uuid>` | セッション |
| `ahp-chat:/<id>` | チャット (ターン・ツール呼び出し) |
| `serverSeq` | ホストがつける通し番号 |
| `clientSeq` | 画面がつける自分の操作番号 |
| `chat/turnStarted` → `chat/delta` → `chat/turnComplete` | 1 ターンの基本のアクション |
| `chat/toolCallReady` → `chat/toolCallConfirmed` | ツール実行の確認 |

```bash title="VS Code の Agent Host を単独で起動"
code agent host
```
