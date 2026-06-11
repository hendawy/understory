import asyncio
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
import httpx


async def combined_sse(scope, receive, send):
    if scope["type"] == "http":
        if scope["method"] == "GET":
            response = JSONResponse({"method": "GET"})
            await response(scope, receive, send)
        elif scope["method"] == "POST":
            response = JSONResponse({"method": "POST"})
            await response(scope, receive, send)
        else:
            response = JSONResponse({"method": scope["method"]}, status_code=405)
            await response(scope, receive, send)
    else:
        pass  # not http


app = Starlette(
    routes=[
        Route("/sse", endpoint=combined_sse, methods=["GET", "POST", "DELETE"]),
    ]
)


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/sse")
        print("GET", r1.status_code, r1.json())
        r2 = await client.post("/sse?session_id=123")
        print("POST", r2.status_code, r2.json())


asyncio.run(main())
