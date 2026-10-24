# 状態同期の仕組み

<p class="oneliner">複数の画面が同時に操作しても、最後は全員が同じ状態になる。その仕組みを、図とコードで追いかけます。</p>

## 基本の流れ: 購読 → スナップショット → アクション

```mermaid
sequenceDiagram
    participant C as 画面 (クライアント)
    participant H as ホスト
    C->>H: initialize (使えるバージョン一覧, clientId)
    H-->>C: (決まったバージョン, serverSeq)
    C->>H: subscribe (channel: ahp-chat:/c1)
    H-->>C: スナップショット (今の状態まるごと)
    loop 以後ずっと
      H--)C: action (serverSeq: 6, chat/delta …)
      H--)C: action (serverSeq: 7, chat/delta …)
    end
```

- 最初に**今の状態をまるごと**もらう (スナップショット)
- その後は**差分 (アクション)** だけが、**通し番号 (`serverSeq`)** つきで届く
- 接続が切れても、「最後に見た番号」を伝えれば**見逃した分**を受け取れる

## 状態とアクションをコードで

```python
--8<-- "ahp/ahp_model.py:state"
```

リデューサーは、状態とアクションから新しい状態を作る**だけ**の関数です。

```python
--8<-- "ahp/ahp_model.py:reducer"
```

## 先に画面へ反映する: write-ahead

自分の操作を**ホストの返事を待たずに**画面に出し、あとで答え合わせします。これで操作がキビキビ感じられます。

```mermaid
flowchart LR
    conf["確定した状態<br/>(ホストが認めた分)"] --> p1["+ 未確定の操作 1"] --> p2["+ 未確定の操作 2"] --> view["画面に出す状態"]
    style view fill:#2f9e44,color:#fff,stroke:#2f9e44
```

ホストからアクションが届いたときの処理は、3 通りだけです。

| 届いたもの | 画面のやること |
|---|---|
| **自分の操作**が返ってきた | 未確定リストから外し、確定状態に入れる |
| **他人 (や AI) の操作** | 確定状態に入れる。未確定の操作はその上に積み直す |
| **却下された自分の操作** | 未確定リストから外す (画面から消える) |

## 同時に押したらどうなる?

ツールの実行確認に、スマホと PC から**ほぼ同時に**答えた場合です。

```mermaid
sequenceDiagram
    participant P as 📱 スマホ
    participant H as ホスト
    participant L as 💻 PC
    H--)P: toolCallReady (seq 3)「実行していい?」
    H--)L: toolCallReady (seq 3)
    P->>H: toolCallConfirmed (承認)
    L->>H: toolCallConfirmed (拒否)
    Note over H: 先着順。スマホの承認が先に届いた
    H--)P: seq 4: 承認 ✅
    H--)L: seq 4: 承認 ✅
    H--)L: seq 5: あなたの拒否は却下 (already resolved)
    Note over P,L: 両方の画面が「承認済み・実行中」にそろう
```

ホストと画面のコードは次のとおりです。

??? note "窓口の定義 (クリックで開く)"
    ```python
    --8<-- "ahp/ahp_model.py:protocols"
    ```

??? note "ホスト (クリックで開く)"
    ```python
    --8<-- "ahp/ahp_model.py:host"
    ```

**画面 (クライアント)**: `view` は「確定状態 + 自分の未確定の操作」です。

```python
--8<-- "ahp/ahp_model.py:client"
```

**動かしてみる**

```python
--8<-- "ahp/ahp_model.py:demo"
```

??? success "実行結果"
    ```text
    [laptop] 却下されました: already resolved
    ChatState(text='\n> テストを直して\n原因を調べます…', active_turn=None, tool='done')
    ```

    PC の遅れた「拒否」は却下され、最後の `assert` で **PC・スマホ・ホストの状態が完全に一致**していることを確かめています。

## ACP とつながるところ

ホストは、上 (画面) には AHP を、下 (エージェント) には ACP などを話す**通訳**です。

```mermaid
sequenceDiagram
    participant C as 画面
    participant H as ホスト
    participant A as エージェント (ACP)
    C->>H: AHP: chat/turnStarted「直して」
    H--)C: 全画面へ配る (seq 10)
    H->>A: ACP: session/prompt
    A--)H: ACP: session/update (agent_message_chunk)
    H--)C: AHP: chat/delta (seq 11)
    A->>H: ACP: session/request_permission
    H--)C: AHP: chat/toolCallReady (seq 12)
    C->>H: AHP: chat/toolCallConfirmed
    H-->>A: ACP: allow_once
    A-->>H: ACP: stopReason end_turn
    H--)C: AHP: chat/turnComplete (seq 13)
```

!!! abstract "このページのまとめ"
    - 最初に**スナップショット**、その後は**通し番号つきのアクション**が届く。
    - 自分の操作は**先に画面へ反映 (write-ahead)** し、ホストの返送で答え合わせする。
    - 承認のような取り合いは**ホストが先着順で決める**。全員が同じ状態にそろう。

[次へ: AHP を使ってみる :material-arrow-right:](hands-on.md){ .md-button .md-button--primary }
