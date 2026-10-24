"""どのプロトコルを使うか: 判断を関数として書いてみる。"""

from dataclasses import dataclass
from typing import Literal

# --8<-- [start:choose]
Proto = Literal["MCP", "ACP", "A2A", "AHP"]


@dataclass
class Need:
    connect_tool_or_data: bool = False        # DB・API・ファイルなどを道具として使わせたい
    use_agent_from_my_editor: bool = False    # 好きなエディタで好きなコーディングエージェントを使いたい
    delegate_to_other_agent: bool = False     # 別チーム/別会社のエージェントに仕事を頼みたい
    share_session_across_devices: bool = False  # 同じセッションを複数の画面・端末から見たい


def choose(need: Need) -> list[Proto]:
    picks: list[Proto] = []
    if need.connect_tool_or_data:
        picks.append("MCP")   # エージェント ⇄ 道具
    if need.use_agent_from_my_editor:
        picks.append("ACP")   # エディタ ⇄ エージェント (1 対 1)
    if need.delegate_to_other_agent:
        picks.append("A2A")   # エージェント ⇄ エージェント
    if need.share_session_across_devices:
        picks.append("AHP")   # たくさんの画面 ⇄ ホスト (N 対 1)
    return picks


print(choose(Need(use_agent_from_my_editor=True)))                       # ['ACP']
print(choose(Need(delegate_to_other_agent=True, connect_tool_or_data=True)))  # ['MCP', 'A2A']
# --8<-- [end:choose]
