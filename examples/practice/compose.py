"""4 つのプロトコルを重ねると何が起きるか: 1 つの依頼が層を降りていく様子。"""

from typing import Protocol


# --8<-- [start:layers]
class McpTool(Protocol):            # MCP: エージェントが使う「道具」
    def call(self, name: str, args: dict[str, str]) -> str: ...


class RemoteAgent(Protocol):        # A2A: 中身の見えない「同僚」
    def send_message(self, text: str) -> str: ...


class CodingAgent(Protocol):        # ACP: エディタ/ホストから見た「エージェント」
    def prompt(self, text: str) -> str: ...


class SessionHost(Protocol):        # AHP: 複数の画面から見た「セッションの置き場」
    def start_turn(self, client_id: str, text: str) -> None: ...
# --8<-- [end:layers]


# --8<-- [start:impl]
class Db:
    def call(self, name: str, args: dict[str, str]) -> str:
        return f"{args['table']} の行数は 42"


class TranslatorAgent:
    def send_message(self, text: str) -> str:
        return f"[英訳] {text}"


class MyCodingAgent:
    def __init__(self, tool: McpTool, colleague: RemoteAgent) -> None:
        self.tool, self.colleague = tool, colleague

    def prompt(self, text: str) -> str:
        fact = self.tool.call("query", {"table": "users"})   # MCP で道具を使う
        return self.colleague.send_message(fact)             # A2A で同僚に頼む


class Host:
    def __init__(self, agent: CodingAgent) -> None:
        self.agent, self.screens = agent, ["laptop", "browser"]

    def start_turn(self, client_id: str, text: str) -> None:
        answer = self.agent.prompt(text)                     # ACP でエージェントに渡す
        for s in self.screens:                               # AHP で全画面に配る
            print(f"{s} <- {answer}  (依頼者: {client_id})")


host: SessionHost = Host(MyCodingAgent(Db(), TranslatorAgent()))
host.start_turn("laptop", "ユーザー数を英語でレポートして")
# --8<-- [end:impl]
