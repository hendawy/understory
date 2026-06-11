import asyncio
from typing import Dict, List, Optional
import ollama
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("understory")

# State
conversations: Dict[str, List[Dict[str, str]]] = {}
ollama_client = ollama.AsyncClient()


@mcp.tool()
async def ask_ollama(model: str, prompt: str) -> str:
    """Send a stateless prompt to an Ollama model."""
    try:
        response = await ollama_client.chat(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"


@mcp.tool()
async def chat_with_ollama(
    conversation_id: str, model: str, prompt: str, system_prompt: Optional[str] = None
) -> str:
    """Send a stateful prompt to an Ollama model, maintaining conversation history."""
    try:
        if conversation_id not in conversations:
            conversations[conversation_id] = []
            if system_prompt:
                conversations[conversation_id].append(
                    {"role": "system", "content": system_prompt}
                )

        conversations[conversation_id].append({"role": "user", "content": prompt})
        response = await ollama_client.chat(
            model=model, messages=conversations[conversation_id]
        )

        assistant_msg = response["message"]["content"]
        conversations[conversation_id].append(
            {"role": "assistant", "content": assistant_msg}
        )
        return assistant_msg
    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"


@mcp.tool()
def clear_ollama_chat(conversation_id: str) -> str:
    """Clear the conversation history for a specific conversation ID."""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return f"Conversation '{conversation_id}' cleared."
    return f"Conversation '{conversation_id}' not found."


@mcp.tool()
async def list_ollama_models() -> str:
    """List all available models installed in your local Ollama instance."""
    try:
        models_info = await ollama_client.list()
        models = [m["model"] for m in models_info.get("models", [])]
        return f"Available models: {', '.join(models)}"
    except Exception as e:
        return f"Error listing models: {str(e)}"


# Expose the ASGI app for uvicorn
app = mcp.sse_app

if __name__ == "__main__":
    mcp.run()
