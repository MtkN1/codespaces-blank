# typing.Protocol で考える

<p class="oneliner">「形が合っていれば、相手が何者でも使える」。これがプロトコルの考え方であり、Python の <code>typing.Protocol</code> の考え方でもあります。</p>

## 継承 (名前で判断) と Protocol (形で判断)

```mermaid
flowchart LR
    subgraph nominal["継承: 「親が誰か」で判断"]
      direction TB
      B["class Animal"] --> D1["class Dog(Animal)"]
      X["class Robot"] -. "Animal を継承していないので ×" .-> B
    end
    subgraph structural["Protocol: 「何ができるか」で判断"]
      direction TB
      P{{"Speaker<br/>speak(text) -> str"}}
      D2["Dog<br/>speak() がある"] -- "○" --> P
      R2["Robot<br/>speak() がある"] -- "○" --> P
      S2["Stone<br/>speak() が無い"] -. "×" .-> P
    end
```

## コードで確認

**1. 約束 (窓口の形) を書く**

```python
--8<-- "basics/protocol_intro.py:protocol"
```

**2. 約束を知らない人たちが実装する** (継承していません)

```python
--8<-- "basics/protocol_intro.py:impls"
```

**3. 使う側は約束だけを見る**

```python
--8<-- "basics/protocol_intro.py:use"
```

## エージェントプロトコルに置き換えると

```mermaid
flowchart LR
    subgraph py["Python"]
      direction TB
      p1["class Speaker(Protocol)"]
      p2["Dog / Robot"]
      p3["greet(s: Speaker)"]
    end
    subgraph ag["エージェントプロトコル"]
      direction TB
      a1["仕様書 (A2A / ACP / AHP)"]
      a2["Claude Code / Gemini CLI / 他社のエージェント"]
      a3["エディタ / 自分のエージェント"]
    end
    p1 -. "約束" .- a1
    p2 -. "実装する側" .- a2
    p3 -. "使う側" .- a3
```

| Python | エージェントプロトコル |
|---|---|
| `Protocol` クラスのメソッド | 仕様書で決められた操作 (`session/prompt`, `SendMessage` など) |
| 引数・戻り値の型 | JSON メッセージの形 |
| 実装クラス | 各社のエージェントやエディタ |
| mypy の型チェック | 仕様への準拠 (互換性) |

!!! tip "このサイトのコードの読み方"
    各章には、次のようなコードが出てきます。

    ```python
    class Agent(Protocol):
        def prompt(self, session_id: str, text: str) -> StopReason: ...
    ```

    これは「**エージェントには `prompt` という窓口があり、セッション ID と文章を渡すと、止まった理由が返ってくる**」と読みます。
    本物は JSON-RPC のメッセージとして送られますが、意味は同じです。メソッド名の横のコメント (`# session/prompt` など) が、本物の操作名です。

!!! abstract "このページのまとめ"
    - プロトコル = **窓口の形**の約束。中身は問わない。
    - `typing.Protocol` = 継承ではなく**形**で判断する型。
    - この 2 つは同じ考え方なので、以降はコードで窓口を説明します。

[次へ: 共通の土台 JSON-RPC :material-arrow-right:](jsonrpc.md){ .md-button .md-button--primary }
