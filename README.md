# a2a-claude-agent

Claude Agent SDK（Python）で動くエージェントを、公式 [a2a-sdk](https://github.com/a2aproject/a2a-python)（1.x、A2A 仕様 1.0）の `AgentExecutor` として実装し、A2A サーバーとして公開するパッケージです。

```
A2A クライアント ──JSON-RPC / HTTP+JSON──▶ a2a-sdk（ルート・DefaultRequestHandler・InMemoryTaskStore）
                                              │ execute() / cancel()
                                              ▼
                                     ClaudeAgentExecutor   ← このパッケージ
                                       ├─ SessionStore（contextId → session_id）
                                       ├─ EventMapper（SDK メッセージ → A2A イベント）
                                       └─ ClaudeRunner（ClaudeSDKClient の薄いラッパー）
                                              │
                                              ▼
                                     Claude Agent SDK → 同梱の Claude CLI（サブプロセス）
```

a2a-sdk はプロトコルの配管だけを担い、推論・ツール実行・文脈管理のループは Claude Agent SDK が担います。このパッケージはその間の翻訳層で、A2A のタスク状態と Agent SDK のセッション・実行を対応づけます。

- 対応範囲（MVP）: テキストの入出力、静的なツール許可、単一プロセス。マルチターン、ストリーミング、キャンセルに対応
- 検証したバージョン: Python 3.13、a2a-sdk 1.2.3、claude-agent-sdk 0.2.174（同梱 CLI 2.1.310）

## 起動方法

```bash
uv sync
uv run a2a-claude-agent            # または uv run python -m a2a_claude_agent
```

既定では `http://127.0.0.1:41241` で待ち受け、次のパスを公開します。

| パス | 内容 |
| --- | --- |
| `/.well-known/agent-card.json` | Agent Card |
| `/a2a/jsonrpc` | JSON-RPC（必須トランスポート、Agent Card で優先） |
| `/a2a/rest` | HTTP+JSON（`A2A_CLAUDE_ENABLE_REST=false` で無効化） |

公式クライアントからの呼び出し例:

```python
import asyncio, uuid
import httpx
from a2a.client import ClientConfig, create_client
from a2a.types import Message, Part, Role, SendMessageRequest

async def main():
    async with httpx.AsyncClient(timeout=120) as http:
        client = await create_client("http://127.0.0.1:41241", client_config=ClientConfig(httpx_client=http))
        request = SendMessageRequest(message=Message(
            role=Role.ROLE_USER, message_id=str(uuid.uuid4()), parts=[Part(text="2+3 は？数字だけで")]))
        async for event in client.send_message(request):
            print(event)
        await client.close()

asyncio.run(main())
```

同じ `contextId` を付けて送ると、前の会話の続きとして処理されます（タスクはメッセージごとに新しく作られます）。

### 認証

Agent SDK は同梱の Claude CLI の認証をそのまま使います。本番では `ANTHROPIC_API_KEY`、または Amazon Bedrock / Google Vertex AI / Microsoft Foundry 経由（`CLAUDE_CODE_USE_BEDROCK=1` など）で認証してください。Anthropic は、事前の承認なしに Agent SDK で作ったプロダクトで claude.ai のログインを使わせることを認めていません。

## 環境変数

すべて `A2A_CLAUDE_` で始まります（カレントディレクトリの `.env` も読みます）。リストは `Read,Glob` のようなカンマ区切りか JSON 配列で書けます。

| 変数 | 既定値 | 内容 |
| --- | --- | --- |
| `A2A_CLAUDE_MODEL` | `haiku` | モデルのエイリアスか正式な ID。必ず Agent SDK に明示的に渡す |
| `A2A_CLAUDE_TOOLS` | `Read,Glob,Grep` | エージェントが使える組み込みツール。ここにないツールは存在しない扱い |
| `A2A_CLAUDE_ALLOWED_TOOLS` | （空） | 確認なしで実行してよい追加の許可ルール。例: `Read(//srv/docs/**)` |
| `A2A_CLAUDE_DISALLOWED_TOOLS` | `Bash,Write,Edit,NotebookEdit,WebFetch,WebSearch,Agent,Task` | 常に禁止するツール。`TOOLS` や `ALLOWED_TOOLS` より優先 |
| `A2A_CLAUDE_CWD` | `workspace` | エージェントの作業ディレクトリ。起動時に作成する。専用のディレクトリを指定すること |
| `A2A_CLAUDE_MAX_TURNS` | `10` | 1 リクエストあたりの最大ターン数 |
| `A2A_CLAUDE_MAX_BUDGET_USD` | （なし） | 1 リクエストあたりの予算上限（USD） |
| `A2A_CLAUDE_SYSTEM_PROMPT` | 短い既定文 | システムプロンプト |
| `A2A_CLAUDE_PERMISSION_MODE` | `dontAsk` | `dontAsk`（未許可のツールは即拒否）か `plan`（ツールを実行しない） |
| `A2A_CLAUDE_HOST` | `127.0.0.1` | バインド先 |
| `A2A_CLAUDE_PORT` | `41241` | ポート |
| `A2A_CLAUDE_PUBLIC_URL` | `http://{HOST}:{PORT}` | Agent Card に載せるベース URL（リバースプロキシの後ろに置くとき） |
| `A2A_CLAUDE_ENABLE_REST` | `true` | HTTP+JSON トランスポートを公開するか |
| `A2A_CLAUDE_AGENT_NAME` / `_AGENT_DESCRIPTION` / `_AGENT_VERSION` | | Agent Card の名前・説明・バージョン |
| `A2A_CLAUDE_SKILLS` | 汎用スキル 1 件 | Agent Card のスキル。JSON 配列（`id`, `name`, `description`, `tags`, `examples`） |

プログラムから組み込む場合は `create_app(Settings(...), runner=..., session_store=...)` で Starlette アプリを作れます。`ClaudeRunner` と `SessionStore` は差し替え可能なインターフェースです。

## 既定のツール制限

既定のエージェントは「作業ディレクトリの中を読むだけ」です。次の挙動は実モデル（Haiku）で確認しました。

- 使えるツールは `Read` / `Glob` / `Grep` だけ（Agent SDK の `tools`）。`Bash`・`Write`・`Edit` などは `disallowed_tools` でも明示的に禁止しています。Bash を頼んでも、ツールが存在しないので実行されず、処理はそのまま終わります（統合テスト 6）
- `permission_mode="dontAsk"` で、許可ルールに当たらないツール呼び出しは許可待ちで止まらず即座に拒否されます。参考までに、`can_use_tool` を渡さない Agent SDK では `default` モードでも拒否され、止まりませんでした
- 読み取りは作業ディレクトリの中だけです。Claude Code は作業ディレクトリ内の読み取りを確認なしで許可し、外は `dontAsk` で拒否します（統合テスト 6b）。`allowed_tools` に素の `"Read"` を入れると作業ディレクトリの外（`~/.claude.json` など）まで読めてしまうため、既定では許可ルールを付けていません。ほかの場所を読ませたいときは `Read(//abs/path/**)` のようにパスで絞ってください
- `setting_sources=[]` で `~/.claude` や `.claude/` の設定を読み込ませず、モデル・権限・hooks が外から上書きされないようにしています。MCP サーバー（`strict_mcp_config`）、スキル（`skills=[]`）、サブエージェント（`agents={}`）も無効です
- `verbatim_prompts=True` で、受け取ったテキストをそのまま Claude に渡します。これがないと、メッセージ中の `@/絶対パス` という記法でツールの権限を通らずにファイルが読み込まれてしまいます（作業ディレクトリ外のファイルが読めることを確認済み。統合テスト 6c で防げていることを確認）。先頭の `/` もスラッシュコマンドとして解釈されません

## セキュリティ上の注意

- 受信リクエストの認証はありません。既定のバインド先は `127.0.0.1` です。外部に公開するときは、必ず認証付きのリバースプロキシの後ろに置いてください
- エージェントの CLI はサーバープロセスの環境変数を引き継ぎます。Bash を禁止しているので直接は読めませんが、ツールを広げるときは環境変数に秘密情報を置かないでください
- 作業ディレクトリには、A2A の呼び出し元に読まれてよいファイルだけを置いてください
- ステータスメッセージにはツール名だけを載せ、ツールの入力値や結果（ファイルの中身）は載せません

## 設計

### execute の流れ

1. `context.current_task` がなければ `Task`（SUBMITTED）を最初に enqueue する。ストリーミングは常に「Task が先」のパターン
2. 同じ `contextId` のロックを取る（同じ文脈への同時リクエストは直列化、別の文脈同士は並行）
3. `TaskUpdater` で WORKING にする
4. `contextId` から `session_id` を引き、あれば `resume` で再開、なければ新規に始める
5. Agent SDK のメッセージを順に A2A イベントへ変換する。届いた `session_id` はすぐ `SessionStore` に保存する（完了を通知する前に保存されるので、次のメッセージが確実に続きから始まる）
6. 結果メッセージで終える。成功なら最終テキストを Artifact にして COMPLETED、エラーなら FAILED

テキスト以外の入力（ファイルやデータの Part だけ）は REJECTED にします。

### イベント変換（`event_mapper.py`）

| Agent SDK | A2A |
| --- | --- |
| アシスタントのテキスト（後にツール呼び出しが続くもの） | WORKING の状態更新メッセージ |
| アシスタントのテキスト（最終回答） | Artifact `response`（1 チャンク、`append=False`, `last_chunk=True`） |
| ツール呼び出し | WORKING「Running tool: Read」（メタデータに `tool_name`）。入力値は載せない |
| 結果メッセージ（成功） | COMPLETED。usage・コスト・モデル別内訳をタスクの `metadata.claude` に入れる |
| 結果メッセージ（エラー、`max_turns` 到達など） | FAILED（理由をメッセージに入れる） |
| 結果メッセージなしでストリームが終わる / 例外 | FAILED |

テキストは「次のメッセージが来るまで」保留し、続きがツール呼び出しなら途中経過、結果メッセージなら最終回答として扱います。これで同じ文章が途中経過と Artifact に二重に出ません。最終回答はまとめて 1 チャンクで出します（部分ストリーミング `include_partial_messages` は使っていません）。終了状態にした後はイベントを出しません。

### Agent SDK の使い方

リクエストごとに `ClaudeSDKClient` を 1 つ作り（CLI サブプロセス 1 つ）、`connect` → `query` → `receive_response` → `disconnect` を同じ asyncio タスクの中で行います（SDK の制約）。`query()` 関数ではなく `ClaudeSDKClient` を選んだのは `interrupt()` を使うためです。会話の継続は CLI がディスクに保存するセッションを `resume` で再開して行います。

### キャンセル

a2a-sdk 1.2.3 の `DefaultRequestHandler`（= `DefaultRequestHandlerV2`）は、docstring と違い **先に `cancel()` を呼び、その後で `execute()` のタスクをキャンセル** します。どちらの順序でも動くように、`cancel()` は次のようにしています。

1. 実行中の対応表（task_id → 実行状態）から対象を引き、以後 `execute()` がイベントを出さないよう印を付ける
2. `interrupt()` を送り、`execute()` が CLI を切断し終わるまで待つ（上限 15 秒）。interrupt が失敗した場合は読み取りを打ち切って切断させる
3. CANCELED を出す。中断された実行の usage があれば metadata に付ける

`execute()` が先にキャンセルされた場合も、`finally` で CLI を切断してから `cancel()` が CANCELED を出します。統合テスト 7 で、CANCELED の後に CLI のサブプロセスが残っていないことを確認しています。

### Opus を使わないための対策

- `model` を常に明示し、`fallback_model=None`、サブエージェント用の `CLAUDE_CODE_SUBAGENT_MODEL` も同じモデルに固定
- サブエージェントを起動する `Agent` / `Task` ツールは禁止、`agents={}`、`setting_sources=[]`
- 統合テストは設定するモデル名に `opus` が含まれていたら即失敗し、各タスクの `metadata.claude.model_usage`（モデル別内訳）にも Opus がないことをアサートする

## テスト

```bash
uv run pytest                    # ユニットテスト（ネットワーク不要、57 件）
uv run pytest -m integration     # 統合テスト（実モデル。CLI が未認証ならモデルを使うテストは skip）
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy                      # src を --strict で検査
```

- ユニットテストはフェイクのランナー（`tests/fakes.py`）で、イベント変換、SessionStore、Agent Card、設定、executor の状態遷移（成功・失敗・キャンセル・直列化）、a2a-sdk のハンドラーとルートを通した送受信を確認します
- 統合テストは uvicorn を空きポートで起動し、公式 a2a-sdk クライアントで操作します。Haiku が基本で、ツール使用のシナリオだけ Sonnet です。`A2A_TEST_HAIKU_MODEL` / `A2A_TEST_SONNET_MODEL` でモデル ID を変えられます。終了時にモデル別の usage とコストを表示し、`A2A_TEST_USAGE_FILE` を指定すると JSON でも保存します

| # | シナリオ | モデル |
| --- | --- | --- |
| 1 | Agent Card 取得 | なし |
| 2 | 非ストリーミング送信（「2+3 は？」→ 5） | Haiku |
| 3 | ストリーミング送信（Task → WORKING → Artifact → COMPLETED、終了後にイベントなし） | Haiku |
| 4 | マルチターン（合言葉「みかん」） | Haiku |
| 5 | ツール使用（Read で作業ディレクトリのファイルを読む） | Sonnet |
| 6 | 不許可ツール（Bash が実行されず、処理が止まらない） | Haiku |
| 6b | 作業ディレクトリ外の Read が拒否される | Haiku |
| 6c | `@/path` 記法でファイルが読み込まれない | Haiku |
| 7 | キャンセル（CANCELED、サブプロセスが残らない） | Haiku |
| 8 | エラー（ランナーの例外 / 作れない作業ディレクトリ → FAILED） | なし |

## 既知の制約

- セッションの対応表はメモリ上にあり、再起動で消えます（CLI のセッションファイルは `~/.claude/projects/` に残り続け、掃除はしません）。対応表も文脈ごとに増え続けます
- 最終回答は完了時にまとめて 1 チャンクで届きます。トークン単位のストリーミングはしていません
- 1 リクエストごとに CLI サブプロセスを起動するため、応答の前に 1〜2 秒の起動時間がかかります
- 完了（COMPLETED）を通知した後に CLI の終了処理が走るので、通知の直後は数秒間サブプロセスが残ることがあります
- `resume` に失敗した場合（セッションファイルが消えたなど）はそのリクエストを FAILED にし、対応表から消して次は新しいセッションで始めます

## 対象外の項目（設計メモ）

### `can_use_tool` と INPUT_REQUIRED の橋渡し（方針案）

ツール実行の許可を A2A の呼び出し元に問う仕組みです。

1. `permission_mode="default"` にして `can_use_tool` コールバックを渡す。コールバックは許可が必要な呼び出しでだけ呼ばれる
2. コールバックの中で、ツール名と（必要なら要約した）入力を載せたメッセージで INPUT_REQUIRED の状態更新を出し、`asyncio.Future` で返事を待つ
3. A2A の契約では INPUT_REQUIRED を出したら `execute()` は return し、次の入力で `execute()` が再度呼ばれる。一方 Agent SDK のコールバックは CLI を止めたまま待つので、**CLI のクライアントを `execute()` の外（task_id をキーにした対応表）に持ち、`execute()` の寿命と切り離す** 必要がある。最初の `execute()` は INPUT_REQUIRED を出して return し、続きのメッセージで呼ばれた `execute()` は返事（「許可」「拒否」など）を Future に渡して、同じクライアントからのメッセージの受信を再開する
4. 待っている間のタイムアウト（拒否扱い）、キャンセル（Future を拒否で解決して interrupt）、サーバー停止時の後始末が要る。A2A の `TaskUpdater.requires_input()` と、Agent SDK の `PermissionResultAllow` / `PermissionResultDeny` で表現できる
5. 返事の形式は、テキストの「yes / no」より DataPart（`{"decision": "allow"}`）を推奨。a2acode が同じ方向の実装をしているので参考になる

### そのほか

- **複数レプリカ**: `SessionStore` を Redis などの共有ストアで実装し、CLI のセッションファイルも共有する必要がある。Agent SDK の `session_store` オプション（トランスクリプトを外部ストアにミラーし、`resume` 時に復元する）が使える。a2a-sdk 側は cluster mode（`VersionedTaskStore` と event stream）か、同じタスクを同じレプリカに振り分けるスティッキールーティングが要る
- **DB のタスクストア**: a2a-sdk の `DatabaseTaskStore`（`a2a-sdk[postgresql]` など）に差し替えるだけで済む
- **受信リクエストの認証**: Starlette のミドルウェアか、`create_jsonrpc_routes` の `context_builder` で `ServerCallContext.user` を設定する。Agent Card の `security_schemes` も合わせて宣言する
- **テキスト以外の Part**: ファイルは作業ディレクトリ（リクエストごとのサブディレクトリ）に保存してパスを伝える、画像は Agent SDK のストリーミング入力で content block として渡す、などが考えられる
- **gRPC / A2A 0.3 互換 / プッシュ通知**: a2a-sdk の `GrpcHandler`、`enable_v0_3_compat=True`、`push_config_store` / `push_sender` で追加できる。executor 側の変更は不要
