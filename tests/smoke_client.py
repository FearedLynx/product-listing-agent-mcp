"""End-to-end check over the real MCP protocol.

Starts server.py as an MCP server over stdio, the same way Claude Desktop or
Claude Code does, and calls its tools. Exits with an error if anything is off.
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {"list_products", "get_product", "get_sales_and_stock",
                  "get_brand_guide", "check_listing_draft", "save_listing"}


def as_json(result):
    """Tool result as Python data: structured content if the server sent it, else the text blocks."""
    if result.structured_content is not None:
        data = result.structured_content
        return data["result"] if set(data) == {"result"} else data
    blocks = [json.loads(c.text) for c in result.content if getattr(c, "text", None)]
    return blocks[0] if len(blocks) == 1 else blocks


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = {t.name for t in (await session.list_tools()).tools}
            assert tools == EXPECTED_TOOLS, f"unexpected tools: {tools}"
            print("tools:", sorted(tools))

            prompts = {p.name for p in (await session.list_prompts()).prompts}
            assert "write_listing" in prompts
            print("prompts:", sorted(prompts))

            rows = as_json(await session.call_tool("get_sales_and_stock", {}))
            print("lowest stock:", rows[0]["name"], rows[0]["weeks_of_stock_left"], "weeks")

            bad = {"sku": "NK-3001", "title": "Rain jacket", "description": "The best jacket! 100% safe.", "bullets": ["Warm"]}
            saved = as_json(await session.call_tool("save_listing", bad))
            assert saved["saved"] is False, "a failing listing was saved"
            print("bad listing refused, score", saved["score"])

    print("smoke test passed")


asyncio.run(main())
