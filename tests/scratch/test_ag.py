import asyncio
from google.antigravity import Agent, LocalAgentConfig, types

async def main():
    mcp_servers = [
        types.McpSseServer(
            url="http://localhost:8000/sse"
        )
    ]
    config = LocalAgentConfig(mcp_servers=mcp_servers)
    async with Agent(config) as agent:
        print("Agent initialized!")

if __name__ == "__main__":
    asyncio.run(main())
