import asyncio
from mcp.server.sse import SseServerTransport


async def test():
    sse = SseServerTransport("/messages")
    print("Endpoint internally:", sse._endpoint)


asyncio.run(test())
