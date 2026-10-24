"""公式 Python SDK (a2a-sdk 1.x) で、既にあるエージェントを呼び出す。

    pip install a2a-sdk
    python real_client.py http://127.0.0.1:9999
"""

import asyncio
import sys

# --8<-- [start:client]
import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest


async def main(base_url: str) -> None:
    # 1. 名刺 (Agent Card) を取ってきて中身を確認する
    async with httpx.AsyncClient() as http:
        card = await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()
    print("相手:", card.name, "/ スキル:", [s.name for s in card.skills])

    # 2. 名刺の情報からクライアントを作る (接続先・方式は名刺が教えてくれる)
    client = await create_client(agent=card, client_config=ClientConfig(streaming=True))

    # 3. メッセージを送り、届いたイベントを順に見る
    request = SendMessageRequest(message=new_text_message("こんにちは", role=Role.ROLE_USER))
    async for event in client.send_message(request):
        print(event)
    await client.close()


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9999"))
# --8<-- [end:client]
