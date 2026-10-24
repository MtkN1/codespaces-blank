"""A2A (Agent2Agent) v1.0 の概念モデル。

「中身の見えない (opaque) 他人のエージェント」に仕事を頼み、
Task という伝票で進み具合を追いかける関係をコードで表す。
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterator, Literal, Protocol


# --8<-- [start:card]
@dataclass
class AgentSkill:
    id: str
    name: str
    description: str
    examples: list[str] = field(default_factory=list)


@dataclass
class AgentInterface:
    url: str
    protocol_binding: Literal["JSONRPC", "GRPC", "HTTP+JSON"]
    protocol_version: str = "1.0"


@dataclass
class AgentCard:
    """/.well-known/agent-card.json で公開される「名刺」。"""

    name: str
    description: str
    version: str
    supported_interfaces: list[AgentInterface]
    skills: list[AgentSkill]
    streaming: bool = False           # capabilities.streaming
    push_notifications: bool = False  # capabilities.pushNotifications
# --8<-- [end:card]


# --8<-- [start:task]
class TaskState(StrEnum):
    SUBMITTED = "TASK_STATE_SUBMITTED"
    WORKING = "TASK_STATE_WORKING"
    INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"  # 追加の質問がある
    AUTH_REQUIRED = "TASK_STATE_AUTH_REQUIRED"    # 認可が必要
    COMPLETED = "TASK_STATE_COMPLETED"
    FAILED = "TASK_STATE_FAILED"
    CANCELED = "TASK_STATE_CANCELED"
    REJECTED = "TASK_STATE_REJECTED"


TERMINAL = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED, TaskState.REJECTED}
INTERRUPTED = {TaskState.INPUT_REQUIRED, TaskState.AUTH_REQUIRED}


@dataclass
class Part:
    """中身の最小単位。text / url / data のどれか 1 つを持つ。"""

    text: str | None = None
    url: str | None = None
    data: dict[str, Any] | None = None
    media_type: str | None = None


@dataclass
class Message:
    role: Literal["ROLE_USER", "ROLE_AGENT"]
    parts: list[Part]
    message_id: str
    context_id: str | None = None  # 会話のまとまり
    task_id: str | None = None     # 続きの返事ならタスクを指定


@dataclass
class Artifact:
    """タスクの「成果物」。会話 (Message) とは区別される。"""

    artifact_id: str
    name: str
    parts: list[Part]


@dataclass
class Task:
    id: str
    context_id: str
    state: TaskState
    status_message: Message | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    history: list[Message] = field(default_factory=list)
# --8<-- [end:task]


# --8<-- [start:protocols]
@dataclass
class StatusUpdate:  # TaskStatusUpdateEvent
    task_id: str
    state: TaskState


@dataclass
class ArtifactUpdate:  # TaskArtifactUpdateEvent
    task_id: str
    artifact: Artifact


StreamEvent = Task | Message | StatusUpdate | ArtifactUpdate


class CardResolver(Protocol):
    def get_agent_card(self, base_url: str) -> AgentCard: ...


class A2AServer(Protocol):
    """リモートエージェントの窓口 (v1.0 の操作名に対応)。"""

    def send_message(self, message: Message) -> Task | Message: ...       # SendMessage
    def send_streaming_message(self, message: Message) -> Iterator[StreamEvent]: ...
    def get_task(self, task_id: str) -> Task: ...                          # GetTask
    def cancel_task(self, task_id: str) -> Task: ...                       # CancelTask
# --8<-- [end:protocols]


# --8<-- [start:remote]
_ids = itertools.count(1)


class TravelAgent:
    """出張手配エージェント (相手側)。中身はブラックボックスという想定。"""

    card = AgentCard(
        name="Travel Agent",
        description="出張の航空券とホテルを手配します",
        version="1.2.0",
        supported_interfaces=[AgentInterface("https://travel.example.com/a2a", "JSONRPC")],
        skills=[AgentSkill("book-trip", "出張手配", "行き先と日付から手配",
                           examples=["来週の大阪出張を手配して"])],
        streaming=True,
    )

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def send_message(self, message: Message) -> Task | Message:
        text = message.parts[0].text or ""
        if "こんにちは" in text:  # すぐ答えられるものは Message で即答
            return Message("ROLE_AGENT", [Part(text="こんにちは!")], f"m{next(_ids)}")

        if message.task_id is None:  # 新しい依頼 → 日付が足りないので質問する
            task = Task(f"task-{next(_ids)}", f"ctx-{next(_ids)}", TaskState.INPUT_REQUIRED,
                        status_message=Message("ROLE_AGENT", [Part(text="日付はいつですか?")],
                                               f"m{next(_ids)}"))
            self.tasks[task.id] = task
        else:  # 同じ task_id で返事が来た → 仕事を完了させる
            task = self.tasks[message.task_id]
            task.artifacts.append(Artifact("a1", "itinerary", [Part(data={
                "flight": "NH21 08:00 HND→ITM", "hotel": "梅田ホテル 1泊", "date": text})]))
            task.state = TaskState.COMPLETED
        task.history.append(message)
        return task

    def send_streaming_message(self, message: Message) -> Iterator[StreamEvent]:
        task = Task(f"task-{next(_ids)}", f"ctx-{next(_ids)}", TaskState.SUBMITTED)
        yield task                                   # 最初に Task が来る
        yield StatusUpdate(task.id, TaskState.WORKING)
        yield ArtifactUpdate(task.id, Artifact("a1", "report", [Part(text="調査結果...")]))
        yield StatusUpdate(task.id, TaskState.COMPLETED)  # 終端状態でストリームが閉じる

    def get_task(self, task_id: str) -> Task:
        return self.tasks[task_id]

    def cancel_task(self, task_id: str) -> Task:
        self.tasks[task_id].state = TaskState.CANCELED
        return self.tasks[task_id]
# --8<-- [end:remote]


# --8<-- [start:client]
def ask(server: A2AServer, text: str, task_id: str | None = None) -> Task | Message:
    msg = Message("ROLE_USER", [Part(text=text)], f"m{next(_ids)}", task_id=task_id)
    return server.send_message(msg)


remote: A2AServer = TravelAgent()

res = ask(remote, "来週の大阪出張を手配して")
while isinstance(res, Task) and res.state not in TERMINAL:
    if res.state is TaskState.INPUT_REQUIRED and res.status_message:
        print("相手からの質問:", res.status_message.parts[0].text)
        res = ask(remote, "10月30日", task_id=res.id)  # 同じ task_id で続きを話す

assert isinstance(res, Task)
print(res.state, "→", res.artifacts[0].parts[0].data)

for event in remote.send_streaming_message(
        Message("ROLE_USER", [Part(text="市場調査して")], "m-s")):
    print("stream:", type(event).__name__)
# --8<-- [end:client]
