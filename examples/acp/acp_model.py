"""ACP (Agent Client Protocol) の概念モデル。

エディタ (Client) とコーディングエージェント (Agent) が、
お互いに相手の「窓口」を呼び合う双方向の関係をコードで表す。
実際の ACP は JSON-RPC 2.0 over stdio だが、ここでは普通のメソッド呼び出しで表現する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


# --8<-- [start:vocab]
StopReason = Literal["end_turn", "max_tokens", "max_turn_requests", "refusal", "cancelled"]
ToolKind = Literal["read", "edit", "delete", "move", "search",
                   "execute", "think", "fetch", "switch_mode", "other"]
ToolStatus = Literal["pending", "in_progress", "completed", "failed"]
PermissionKind = Literal["allow_once", "allow_always", "reject_once", "reject_always"]


@dataclass
class ClientCapabilities:
    """エディタが「これは任せていいよ」と申告する能力。"""

    read_text_file: bool = True
    write_text_file: bool = True
    terminal: bool = False


@dataclass
class PermissionOption:
    option_id: str
    name: str
    kind: PermissionKind
# --8<-- [end:vocab]


# --8<-- [start:updates]
@dataclass
class AgentMessageChunk:  # sessionUpdate = "agent_message_chunk"
    text: str


@dataclass
class Plan:  # sessionUpdate = "plan"
    entries: list[str]


@dataclass
class ToolCall:  # sessionUpdate = "tool_call"
    tool_call_id: str
    title: str
    kind: ToolKind
    status: ToolStatus = "pending"


@dataclass
class ToolCallUpdate:  # sessionUpdate = "tool_call_update"
    tool_call_id: str
    status: ToolStatus


SessionUpdate = AgentMessageChunk | Plan | ToolCall | ToolCallUpdate
# --8<-- [end:updates]


# --8<-- [start:protocols]
class Agent(Protocol):
    """エージェント側の窓口 (エディタが呼ぶ)。"""

    def initialize(self, protocol_version: int, caps: ClientCapabilities) -> int: ...
    def new_session(self, cwd: str) -> str: ...                 # session/new
    def prompt(self, session_id: str, text: str) -> StopReason: ...  # session/prompt
    def cancel(self, session_id: str) -> None: ...              # session/cancel (通知)


class Client(Protocol):
    """エディタ側の窓口 (エージェントが呼ぶ)。"""

    def session_update(self, session_id: str, update: SessionUpdate) -> None: ...  # 通知
    def request_permission(self, session_id: str, tool_call: ToolCall,
                           options: list[PermissionOption]) -> str | None: ...
    def read_text_file(self, session_id: str, path: str) -> str: ...   # fs/read_text_file
    def write_text_file(self, session_id: str, path: str, content: str) -> None: ...
# --8<-- [end:protocols]


# --8<-- [start:agent]
class ToyCodingAgent:
    """LLM の代わりに決め打ちで動く、おもちゃのエージェント。"""

    def __init__(self, client: Client) -> None:
        self.client = client  # ← 双方向: エージェントもエディタを呼べる
        self.caps = ClientCapabilities()

    def initialize(self, protocol_version: int, caps: ClientCapabilities) -> int:
        self.caps = caps
        return min(protocol_version, 1)  # 合意したバージョンを返す

    def new_session(self, cwd: str) -> str:
        return "sess_001"

    def cancel(self, session_id: str) -> None:
        pass

    def prompt(self, session_id: str, text: str) -> StopReason:
        c = self.client
        c.session_update(session_id, Plan(["main.py を読む", "バグを直す"]))
        src = c.read_text_file(session_id, "main.py")  # エディタ上の (未保存も含む) 内容
        c.session_update(session_id, AgentMessageChunk(f"{len(src)} 文字読みました。"))

        call = ToolCall("call_1", "main.py を編集", kind="edit")
        c.session_update(session_id, call)
        choice = c.request_permission(session_id, call, [
            PermissionOption("allow", "許可", "allow_once"),
            PermissionOption("reject", "拒否", "reject_once"),
        ])
        if choice != "allow":
            c.session_update(session_id, ToolCallUpdate("call_1", "failed"))
            return "end_turn"

        c.session_update(session_id, ToolCallUpdate("call_1", "in_progress"))
        c.write_text_file(session_id, "main.py", src.replace("pritn", "print"))
        c.session_update(session_id, ToolCallUpdate("call_1", "completed"))
        c.session_update(session_id, AgentMessageChunk("直しました!"))
        return "end_turn"
# --8<-- [end:agent]


# --8<-- [start:editor]
@dataclass
class MiniEditor:
    """エディタ (ACP Client) 役。ユーザーの代わりに自動で「許可」する。"""

    files: dict[str, str] = field(default_factory=lambda: {"main.py": "pritn('hi')"})
    auto_allow: bool = True

    def session_update(self, session_id: str, update: SessionUpdate) -> None:
        print(f"  UI <- {update}")

    def request_permission(self, session_id: str, tool_call: ToolCall,
                           options: list[PermissionOption]) -> str | None:
        print(f"  ダイアログ: 「{tool_call.title}」を許可しますか? {[o.name for o in options]}")
        return "allow" if self.auto_allow else "reject"

    def read_text_file(self, session_id: str, path: str) -> str:
        return self.files[path]

    def write_text_file(self, session_id: str, path: str, content: str) -> None:
        self.files[path] = content


editor = MiniEditor()
agent: Agent = ToyCodingAgent(client=editor)          # エディタがエージェントを起動
agent.initialize(1, ClientCapabilities())             # 1. initialize
sid = agent.new_session(cwd="/home/me/project")       # 2. session/new
reason = agent.prompt(sid, "バグを直して")              # 3. session/prompt
print("stopReason:", reason, "/ main.py =", editor.files["main.py"])
# --8<-- [end:editor]
