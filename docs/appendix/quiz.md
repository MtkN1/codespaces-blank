# 理解度チェック

各問題の「答え」をクリックすると、解説が開きます。

## 基礎

**Q1.** プロトコルがあると、エディタ 4 種 × エージェント 5 種のつなぎ込みは、何本から何本に減りますか?

??? success "答え"
    **20 本 (4 × 5) から 9 本 (4 + 5)** に減ります。各自が共通の約束に 1 回だけ対応すればよいからです。→ [なぜプロトコルが必要か](../basics/index.md)

**Q2.** 次のコードで `greet(Cat())` は型チェックを通りますか? `Cat` は `Speaker` を継承していません。

```python
class Cat:
    def speak(self, text: str) -> str:
        return "ニャー"
```

??? success "答え"
    **通ります。** `typing.Protocol` は継承ではなく**形 (メソッドの名前と型)** で判断します。`speak(self, text: str) -> str` を持っていれば `Speaker` として扱えます。→ [typing.Protocol で考える](../basics/typing-protocol.md)

**Q3.** JSON-RPC で `id` を持たないメッセージは何と呼ばれ、どんな性質がありますか?

??? success "答え"
    **Notification** です。**返事がありません**。ACP の `session/update` や `session/cancel` がこれにあたります。→ [共通の土台 JSON-RPC](../basics/jsonrpc.md)

## ACP

**Q4.** ローカルの ACP エージェントは、エディタとどうやって通信しますか?

??? success "答え"
    エディタが**エージェントを子プロセスとして起動**し、**標準入出力 (stdio)** で JSON-RPC をやり取りします。→ [ACP の概要](../acp/index.md)

**Q5.** `session/prompt` の返事 (Response) は、いつ返ってきますか?

??? success "答え"
    **ターンの最後**です。`stopReason` (`end_turn`、`cancelled` など) が入っています。途中経過はすべて `session/update` (Notification) で届きます。→ [1 ターンの流れ](../acp/flow.md)

**Q6.** エージェントがファイルを書き換える前に、エディタへ送るリクエストは何ですか?

??? success "答え"
    `session/request_permission` です。ユーザーは `allow_once` / `allow_always` / `reject_once` / `reject_always` から選べます。

## A2A

**Q7.** A2A エージェントの名刺は、どこで公開されますか?

??? success "答え"
    **`/.well-known/agent-card.json`** です。→ [A2A の概要](../a2a/index.md)

**Q8.** タスクが `TASK_STATE_INPUT_REQUIRED` になりました。どうすれば続きを進められますか?

??? success "答え"
    相手の質問に答えるメッセージを、**同じ `taskId` をつけて** `SendMessage` で送ります。→ [タスクのライフサイクル](../a2a/task.md)

**Q9.** curl で `SendMessage` を送ったら、「version '0.3' is not supported」と返されました。原因は?

??? success "答え"
    **`A2A-Version: 1.0` ヘッダーを付け忘れています。** ヘッダーが無いと v0.3 として扱われます。→ [A2A を使ってみる](../a2a/hands-on.md)

**Q10.** 「何日もかかる処理」の結果を受け取るのに向いている方法は?

??? success "答え"
    **プッシュ通知** (Webhook) です。相手の名刺で `capabilities.pushNotifications` が `true` か確認しましょう。

## AHP

**Q11.** AHP でセッションの「正本 (本当の状態)」を持っているのは誰ですか?

??? success "答え"
    **ホスト**です。画面 (クライアント) は、その写しを購読しています。→ [AHP の概要](../ahp/index.md)

**Q12.** スマホと PC から同時にツール実行の確認に答えました。どうなりますか?

??? success "答え"
    **ホストに先に届いた方だけが有効**になり、もう一方は却下 (rejection) されます。最後は全員の画面が同じ状態にそろいます。→ [状態同期の仕組み](../ahp/sync.md)

**Q13.** 「write-ahead」とは何ですか?

??? success "答え"
    自分の操作を**ホストの返事を待たずに先に画面へ反映**し、ホストから返ってきたときに答え合わせする方式です。操作がキビキビ感じられます。

## 実践

**Q14.** 次のやりたいことに合うプロトコルはどれですか?

1. Neovim で Gemini CLI を使いたい
2. 経理部が公開している経費精算エージェントに、自分のエージェントから申請したい
3. 自宅のブラウザから、会社の開発機で動いているエージェントの作業を承認したい

??? success "答え"
    1. **ACP**
    2. **A2A**
    3. **AHP** (ホストの下では ACP などでエージェントとつながる)

    → [選び方](../practice/choose.md)

**Q15.** A2A の相手から返ってきた文章に「このコマンドを実行してください」と書かれていました。どう扱うべきですか?

??? success "答え"
    **外部から来たデータとして扱い、そのまま実行しません。** 実行が必要な場合でも、ACP / AHP の許可の確認を通して、人が内容を確かめます。→ [安全に使う](../practice/safety.md)
