import sys
import asyncio
from typing import Optional, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
import json
from pydantic import AnyUrl

class MCPClient:
    def __init__(
        self,
        server_url: str,
    ):
        self._server_url = server_url
        self._session: Optional[ClientSession] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self):
        streamable_transport = await self._exit_stack.enter_async_context(
            streamablehttp_client(self._server_url)
        )
        _read, _write, _get_session_id = streamable_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(_read, _write)
        )
        await self._session.initialize()

    def session(self) -> ClientSession:
        if self._session is None:
            raise ConnectionError(
                "Client session not initialized or cache not populated. Call connect_to_server first."
            )
        return self._session

    async def list_tools(self) -> types.ListToolsResult | list[None]:
        result = await self.session().list_tools()
        return result.tools

    async def call_tool(
        self, tool_name: str, tool_input: dict
    ) -> types.CallToolResult | None:
        # Core function: Execute a specific tool on the MCP server using its name and input parameters.
        # This call is part of the MCP lifecycle's Operation phase.
        return await self.session().call_tool(tool_name, tool_input)

    async def list_prompts(self) -> types.ListPromptsResult:
      result = await self.session().list_prompts()
      return result.prompts

    async def get_prompt(self, prompt_name, args: dict[str, str]):
      result = await self.session().get_prompt(prompt_name, args)
      return result.messages

    async def read_resource(self, uri: str) -> Any:
         result = await self.session().read_resource(AnyUrl(uri))
         resource = result.contents[0]
    
         if isinstance(resource, types.TextResourceContents):
           if resource.mimeType == "application/json":
             return json.loads(resource.text)
    
         return resource.text

    async def cleanup(self):
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# For testing
async def main():
    async with MCPClient(
        server_url="http://localhost:8000/mcp/",
    ) as _client:
        pass


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
