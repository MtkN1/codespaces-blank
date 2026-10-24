# AHP の概要

<p class="oneliner"><span class="badge ahp">AHP</span> <b>Agent Host Protocol</b> は、<b>1 つのエージェントセッションを、複数の画面や端末から同時に見て操作する</b>ための約束です。Microsoft が VS Code の Agent Host のために作り、公開しています。</p>

## どんな困りごとを解決するのか

<div class="flip" markdown>

<div class="flip-item" data-label="AHP が無いと" markdown>

```mermaid
flowchart LR
    W1["VS Code<br/>ウィンドウ 1"] --> A1["エージェント<br/>(ウィンドウの中で動く)"]
    W2["ブラウザ"] -. "見えない" .-> A1
    X["ウィンドウを閉じる"] --> D["💥 作業も止まる"]
```

- セッションは**それを始めた画面の中**で動いている
- 別の画面からは見えない。画面を閉じると止まる

</div>

<div class="flip-item" data-label="AHP が有ると" markdown>

```mermaid
flowchart LR
    W1["VS Code<br/>ウィンドウ 1"] <-->|AHP| H["Agent Host<br/>(独立したプロセス)<br/>セッションの正本"]
    W2["VS Code<br/>ウィンドウ 2"] <-->|AHP| H
    B["ブラウザ<br/>別の PC"] <-->|AHP| H
    H --> A["エージェント<br/>Copilot / Claude / …"]
    linkStyle 0,1,2 stroke:#2f9e44,stroke-width:3px
```

- セッションは**ホスト**が持っている。画面はそれを「見に行く」だけ
- 画面を閉じても作業は続く。別の画面から同じ作業を見て、承認や中断ができる

</div>

</div>

!!! example "身近な例: Google ドキュメントの共同編集"
    ドキュメントの本体はサーバーにあり、全員の画面に同じ内容が映ります。誰かが書き込むと、すぐに全員の画面に反映されます。
    AHP は、これを **AI エージェントのセッション**でやるための仕組みです。

## ACP との違い

ACP と AHP は似た位置にありますが、**解決する問題が違います**。

```mermaid
flowchart TB
    subgraph AHP_["AHP: N 対 1 の調整役"]
      C1["画面 A"] & C2["画面 B"] & C3["画面 C"] <-->|AHP| H["ホスト<br/>状態の正本 + 順番の整理"]
    end
    subgraph ACP_["ACP: 1 対 1 の会話"]
      H <-->|ACP| A1["Claude Code"]
      H <-->|ACP| A2["Goose"]
    end
    linkStyle 0,1,2 stroke:#2f9e44,stroke-width:3px
    linkStyle 3,4 stroke:#e8590c,stroke-width:3px
```

| | <span class="badge acp">ACP</span> | <span class="badge ahp">AHP</span> |
|---|---|---|
| 数の関係 | 1 つの画面 ⇄ 1 つのエージェント | **たくさんの画面** ⇄ 1 つのホスト |
| 状態を持つのは | エージェント | **ホスト** (全員の画面はその写し) |
| 再接続 | 決めていない | 決めている (見逃した分を後から受け取る) |
| エージェントの詳細 | 見える | 見えない (どのエージェントでも同じ見た目) |

!!! tip "公式の例え: 「AHP は ACP にかけるミューテックス」"
    ACP は 1 対 1 の会話です。そこに複数の人が同時に割り込むと混乱します。
    AHP は、その会話の前に**受付係 (ホスト)** を置いて、「今は誰の番か」「承認は誰が先に押したか」を整理します。

## AHP の 4 つの考え方

<div class="cards" markdown>
<div class="ahp" markdown>
**① チャンネル**

購読できる単位。URI で表す。`ahp-root://`、`ahp-session:/…`、`ahp-chat:/…`
</div>
<div class="ahp" markdown>
**② 状態**

チャンネルごとの**変更できない (イミュータブル) データの木**
</div>
<div class="ahp" markdown>
**③ アクション**

状態を変える**唯一の方法**。「ターン開始」「文字が届いた」など
</div>
<div class="ahp" markdown>
**④ リデューサー**

`(状態, アクション) → 新しい状態` の**純粋関数**。ホストでも画面でも同じものを使う
</div>
</div>

```mermaid
flowchart LR
    S0["状態 v1"] -->|"アクション:<br/>chat/turnStarted"| R1(("reduce")) --> S1["状態 v2"]
    S1 -->|"アクション:<br/>chat/delta"| R2(("reduce")) --> S2["状態 v3"]
```

!!! info "なぜこの形なの?"
    全員が**同じ初期状態**から**同じ順番で同じアクション**を**同じ関数**に通せば、必ず**同じ結果**になります。
    「画面ごとに表示がずれる」問題を、この仕組みで根本からなくしています。

## チャンネルの木

```mermaid
flowchart TB
    root["ahp-root://<br/>使えるエージェント一覧 など"]
    s1["ahp-session:/uuid-1<br/>セッション 1"]
    s2["ahp-session:/uuid-2<br/>セッション 2"]
    c1["ahp-chat:/c1<br/>チャット (ターン・ツール呼び出し)"]
    c2["ahp-chat:/c2"]
    t1["ahp-terminal:/t1<br/>ターミナル"]
    ch["ahp-changeset:/x<br/>変更セット"]
    root --> s1 & s2
    s1 --> c1 & c2 & t1
    c1 --> ch
```

画面は**必要なチャンネルだけ**を購読します。一覧画面ならルートだけ、チャットを開いたらそのチャットも、という具合です。

!!! abstract "このページのまとめ"
    - AHP = **N 個の画面 ⇄ 1 つのホスト**の約束。セッションの**正本はホスト**にある。
    - ACP とは**競合せず、重ねて使う**。ホストの下で ACP を話すことができる。
    - 仕組みは **チャンネル・状態・アクション・リデューサー** の 4 つ。

[次へ: 状態同期の仕組み :material-arrow-right:](sync.md){ .md-button .md-button--primary }
