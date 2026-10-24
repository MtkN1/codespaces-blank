# 参考リンク

このサイトの内容は、以下の公式資料をもとにしています (2026 年 10 月時点)。

## ACP (Agent Client Protocol)

- [公式サイト agentclientprotocol.com](https://agentclientprotocol.com/): 概要・仕様 (v1 安定版 / v2 ドラフト)
- [GitHub: agentclientprotocol/agent-client-protocol](https://github.com/agentclientprotocol/agent-client-protocol)
- [ACP Registry](https://agentclientprotocol.com/get-started/registry): 対応エージェントのカタログ
- [Zed: External Agents](https://zed.dev/docs/ai/external-agents): Zed での設定方法
- [JetBrains: ACP](https://www.jetbrains.com/help/ai-assistant/acp.html): JetBrains IDE での設定方法

## A2A (Agent2Agent Protocol)

- [公式サイト a2a-protocol.org](https://a2a-protocol.org/latest/): 概要・チュートリアル
- [仕様書 (v1.0)](https://a2a-protocol.org/latest/specification/)
- [What's New in v1.0](https://a2a-protocol.org/latest/whats-new-v1/): v0.3 からの変更点
- [GitHub: a2aproject/A2A](https://github.com/a2aproject/A2A)
- [GitHub: a2aproject/a2a-python](https://github.com/a2aproject/a2a-python): Python SDK (`pip install a2a-sdk`)
- [GitHub: a2aproject/a2a-inspector](https://github.com/a2aproject/a2a-inspector): 動作確認用のツール

## AHP (Agent Host Protocol)

- [公式ドキュメント](https://microsoft.github.io/agent-host-protocol/)
- [GitHub: microsoft/agent-host-protocol](https://github.com/microsoft/agent-host-protocol)
- [AHP and the Agent Client Protocol](https://microsoft.github.io/agent-host-protocol/guide/ahp-and-acp): ACP との関係
- [VS Code ブログ: Introducing the Agent Host](https://code.visualstudio.com/blogs/2026/08/26/agent-host-architecture)

## 関連

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Python: typing.Protocol](https://docs.python.org/ja/3/library/typing.html#typing.Protocol)

## このサイトのコード

サイトに載せている Python コードは、すべて実際に動き、`mypy --strict` の型チェックを通ることを確認しています。Python 3.11 以上で動きます。
