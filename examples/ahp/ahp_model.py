"""AHP (Agent Host Protocol) の概念モデル。

1 つのホストが「正本の状態」を持ち、複数のクライアントが
同じセッションを同時に見る・操作する仕組みをコードで表す。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Literal, Protocol


# --8<-- [start:state]
@dataclass(frozen=True)
class ChatState:
    """チャットチャンネル (ahp-chat:/<id>) の状態。イミュータブル。"""

    text: str = ""
    active_turn: str | None = None
    tool: Literal["none", "pending-confirmation", "running", "done", "denied"] = "none"


@dataclass(frozen=True)
class TurnStarted:  # chat/turnStarted
    turn_id: str
    message: str


@dataclass(frozen=True)
class Delta:  # chat/delta
    turn_id: str
    content: str


@dataclass(frozen=True)
class ToolCallReady:  # chat/toolCallReady (確認待ちになる)
    turn_id: str


@dataclass(frozen=True)
class ToolCallConfirmed:  # chat/toolCallConfirmed
    turn_id: str
    approved: bool


@dataclass(frozen=True)
class TurnComplete:  # chat/turnComplete
    turn_id: str


Action = TurnStarted | Delta | ToolCallReady | ToolCallConfirmed | TurnComplete
# --8<-- [end:state]


# --8<-- [start:reducer]
def reduce(state: ChatState, action: Action) -> ChatState:
    """純粋関数: (今の状態, アクション) → 新しい状態。ホストでもクライアントでも同じものを使う。"""
    match action:
        case TurnStarted(turn_id, message):
            return replace(state, active_turn=turn_id, text=state.text + f"\n> {message}\n")
        case Delta(_, content):
            return replace(state, text=state.text + content)
        case ToolCallReady():
            return replace(state, tool="pending-confirmation")
        case ToolCallConfirmed(_, approved):
            return replace(state, tool="running" if approved else "denied")
        case TurnComplete():
            return replace(state, active_turn=None,
                           tool="done" if state.tool == "running" else state.tool)
# --8<-- [end:reducer]


# --8<-- [start:protocols]
@dataclass(frozen=True)
class ActionEnvelope:
    """ホストが全員に配る「通し番号つき」のアクション。"""

    channel: str
    action: Action
    server_seq: int
    origin_client: str | None = None   # None ならホスト (エージェント) 発
    client_seq: int | None = None
    rejection_reason: str | None = None


class AhpClient(Protocol):
    client_id: str
    def on_action(self, env: ActionEnvelope) -> None: ...


class AhpHost(Protocol):
    def subscribe(self, channel: str, client: AhpClient) -> tuple[ChatState, int]: ...
    def dispatch_action(self, channel: str, client_id: str,
                        client_seq: int, action: Action) -> None: ...
# --8<-- [end:protocols]


# --8<-- [start:host]
class ToyHost:
    """正本の状態を持ち、全アクションに通し番号を振って配る。"""

    def __init__(self) -> None:
        self.state: dict[str, ChatState] = {}
        self.seq = 0
        self.subs: dict[str, list[AhpClient]] = {}

    def subscribe(self, channel: str, client: AhpClient) -> tuple[ChatState, int]:
        self.subs.setdefault(channel, []).append(client)
        return self.state.setdefault(channel, ChatState()), self.seq  # スナップショット

    def _broadcast(self, env: ActionEnvelope) -> None:
        for c in self.subs.get(env.channel, []):
            c.on_action(env)

    def dispatch_action(self, channel: str, client_id: str,
                        client_seq: int, action: Action) -> None:
        self.seq += 1
        s = self.state[channel]
        # 確認は「先着 1 名」だけ有効。2 人目以降は却下 (rejection) として返す。
        if isinstance(action, ToolCallConfirmed) and s.tool != "pending-confirmation":
            self._broadcast(ActionEnvelope(channel, action, self.seq, client_id,
                                           client_seq, rejection_reason="already resolved"))
            return
        self.state[channel] = reduce(s, action)
        self._broadcast(ActionEnvelope(channel, action, self.seq, client_id, client_seq))

    def agent_emits(self, channel: str, action: Action) -> None:
        """エージェント (ACP などの裏側) から来た出来事を、アクションとして配る。"""
        self.seq += 1
        self.state[channel] = reduce(self.state[channel], action)
        self._broadcast(ActionEnvelope(channel, action, self.seq))
# --8<-- [end:host]


# --8<-- [start:client]
@dataclass
class ToyClient:
    """先に自分の画面へ反映 (write-ahead) し、ホストの返送で答え合わせする。"""

    client_id: str
    host: AhpHost
    channel: str = "ahp-chat:/c1"
    confirmed: ChatState = field(default_factory=ChatState)
    pending: list[tuple[int, Action]] = field(default_factory=list)
    _next: int = 0
    log: Callable[[str], None] = print

    def __post_init__(self) -> None:
        self.confirmed, _ = self.host.subscribe(self.channel, self)

    @property
    def view(self) -> ChatState:
        """画面に出すのは「確定状態 + 未確定の自分の操作」。"""
        s = self.confirmed
        for _, a in self.pending:
            s = reduce(s, a)
        return s

    def do(self, action: Action) -> None:
        self._next += 1
        self.pending.append((self._next, action))  # まず楽観的に反映
        self.host.dispatch_action(self.channel, self.client_id, self._next, action)

    def on_action(self, env: ActionEnvelope) -> None:
        mine = env.origin_client == self.client_id
        if mine:  # 自分の操作が返ってきた → 未確定リストから外す
            self.pending = [p for p in self.pending if p[0] != env.client_seq]
        if env.rejection_reason:
            if mine:
                self.log(f"[{self.client_id}] 却下されました: {env.rejection_reason}")
            return
        self.confirmed = reduce(self.confirmed, env.action)
# --8<-- [end:client]


# --8<-- [start:demo]
host = ToyHost()
laptop = ToyClient("laptop", host)   # 例: VS Code のウィンドウ
phone = ToyClient("phone", host)     # 例: ブラウザ / スマホ

laptop.do(TurnStarted("t1", "テストを直して"))
host.agent_emits("ahp-chat:/c1", Delta("t1", "原因を調べます…"))
host.agent_emits("ahp-chat:/c1", ToolCallReady("t1"))  # 「実行していい?」

phone.do(ToolCallConfirmed("t1", approved=True))     # スマホが先に承認
laptop.do(ToolCallConfirmed("t1", approved=False))   # PC の遅れた操作は却下される

host.agent_emits("ahp-chat:/c1", TurnComplete("t1"))
assert laptop.view == phone.view == host.state["ahp-chat:/c1"]  # 全員が同じ状態に収束
print(phone.view)
# --8<-- [end:demo]
