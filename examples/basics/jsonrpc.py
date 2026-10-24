"""JSON-RPC 2.0 と「運び方 (Transport)」の概念モデル。

A2A・ACP・AHP はどれも JSON-RPC 2.0 を土台にしている。
"""

from __future__ import annotations

import json
from typing import Any, Callable, NotRequired, Protocol, TypedDict


# --8<-- [start:messages]
class Request(TypedDict):
    """返事が欲しい呼び出し。id で返事と対応づける。"""

    jsonrpc: str  # 常に "2.0"
    id: int | str
    method: str
    params: NotRequired[dict[str, Any]]


class Notification(TypedDict):
    """返事のいらない一方通行のお知らせ。id が無い。"""

    jsonrpc: str
    method: str
    params: NotRequired[dict[str, Any]]


class Response(TypedDict):
    """Request への返事。result か error のどちらか。"""

    jsonrpc: str
    id: int | str
    result: NotRequired[Any]
    error: NotRequired[dict[str, Any]]
# --8<-- [end:messages]


# --8<-- [start:transport]
class Transport(Protocol):
    """メッセージの「運び方」。中身 (JSON-RPC) とは独立している。

    stdio / HTTP / SSE / WebSocket など、実体は何でもよい。
    """

    def send(self, message: str) -> None: ...
    def receive(self) -> str: ...
# --8<-- [end:transport]


# --8<-- [start:loopback]
class LoopbackTransport:
    """テスト用: 送ったものを相手側のハンドラが即座に処理して返す。"""

    def __init__(self, handler: Callable[[Request], Response]) -> None:
        self._handler = handler
        self._inbox: list[str] = []

    def send(self, message: str) -> None:
        req: Request = json.loads(message)
        self._inbox.append(json.dumps(self._handler(req)))

    def receive(self) -> str:
        return self._inbox.pop(0)


def call(t: Transport, id: int, method: str, **params: Any) -> Any:
    req: Request = {"jsonrpc": "2.0", "id": id, "method": method, "params": params}
    t.send(json.dumps(req))
    res: Response = json.loads(t.receive())
    return res.get("result")


def server(req: Request) -> Response:
    if req["method"] == "add":
        p = req.get("params", {})
        return {"jsonrpc": "2.0", "id": req["id"], "result": p["a"] + p["b"]}
    return {"jsonrpc": "2.0", "id": req["id"],
            "error": {"code": -32601, "message": "Method not found"}}


print(call(LoopbackTransport(server), 1, "add", a=2, b=3))  # 5
# --8<-- [end:loopback]
