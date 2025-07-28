"""
MCP Elicitation Client - Simple Educational Implementation

This client demonstrates handling elicitation requests from the server
in a clear, educational way.
"""
import asyncio
from typing import Any

import mcp.types as types
from mcp import ClientSession
from mcp.shared.context import RequestContext
from mcp.client.streamable_http import streamablehttp_client

async def mock_elicitation(context: RequestContext["ClientSession", Any], params: types.ElicitRequestParams) -> types.ElicitResult | types.ErrorData: 
    print(f"<- Client: Received 'elicitation' request from server.")
    print(f"<- Client Parameters '{params}'.")
    print(f"<- Client Context '{context}'.")
    user_input = input(params.message).strip().lower()
    if user_input in ["no", "decline", "n"]:
        return types.ElicitResult(
            action="decline",
            content={"want_toppings": False}
        )
    elif user_input in ["yes", "accept", "y"]:
        toppings = input("What toppings would you like? ").strip()
        return types.ElicitResult(
            action="accept",
            content={"want_toppings": True, "toppings": toppings}
        )

   
        
async def main():
    """A simple client to demonstrate handling elicitation requests."""
    server_url = "http://localhost:8000/mcp/"
    print(f"🚀 Connecting to MCP server at {server_url}")

    try:
        async with streamablehttp_client(server_url) as (read_stream, write_stream, get_session_id):
            # Create session with elicitation capability

            async with ClientSession(read_stream, write_stream, elicitation_callback=mock_elicitation) as session:
                print("✅ Connected. Initializing session...")
                await session.initialize()
                print("🛠️ Session initialized.")

                print("\nSCENARIO 1: Accepting the elicitation")
                print("-" * 40)
                result = await session.call_tool("order_pizza", {"size": "large"})
                print(f"✅ Result: {result.content[0].text}")

                await asyncio.sleep(1)

                print("\nSCENARIO 2: Declining the elicitation")
                print("-" * 40)
                result = await session.call_tool("order_pizza", {"size": "medium"})
                print(f"✅ Result: {result.content[0].text}")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("💡 Make sure the server is running.")

    print("\n🎉 Demo finished.")

if __name__ == "__main__":
    asyncio.run(main())