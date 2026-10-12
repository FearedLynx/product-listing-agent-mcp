# Product listing agent (MCP)

A small AI agent that writes product listings for a children's brand shop.
Claude is the agent; an MCP server gives it access to the product catalogue,
sales and stock, the brand voice guide, and a checker that grades every draft.

The products and brands in `data/products.json` are made up for this demo.

## How it works

```
Claude (Claude Code / Claude Desktop)
   │  MCP over stdio
   ▼
server.py ── list_products        what is in the catalogue, and what has a listing
          ── get_product          every fact about one product
          ── get_sales_and_stock  4-week sales, trend, weeks of stock left
          ── get_brand_guide      tone, structure and banned claims
          ── check_listing_draft  grades a draft against the rules, returns what failed
          ── save_listing         saves only when every rule passes
```

The agent loop is: read the guide and the facts, write a draft, check it, fix
what failed, check again, save. `save_listing` refuses anything that fails, so a
bad listing can never reach the shop.

## Why it is built this way

- **Rules are tested, not hoped for.** `checker.py` turns the measurable parts of
  `brand_guide.md` into 12 rules: length limits, materials and age range
  mentioned, no invented certifications, no safety promises, no hype.
- **The checker itself has a fixed test set** (`tests/test_checker.py`): one
  good listing that must pass and a bad listing for every rule that must fail.
  When the rules change, the tests show whether they still catch what they
  should.
- **Facts only come from the data.** A certification is allowed only if the
  product lists it, so the agent cannot invent "OEKO-TEX" or "hypoallergenic".

## Run it

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python tests\smoke_client.py
```

`smoke_client.py` starts the server as a real MCP server and calls its tools over
the protocol, the same way Claude does. GitHub Actions runs both on every push.

**With Claude Code:** register the server once (use your own full path), then
start Claude in this folder:

```bash
claude mcp add product-agent -- C:/path/to/product-agent-mcp/.venv/Scripts/python.exe C:/path/to/product-agent-mcp/server.py
claude
```

Then try:

- `Which products are running low on stock, and which of them still need a listing?`
- `Write and save listings for every product that does not have one yet.`
- `/mcp__product-agent__write_listing LF-1003`

**With Claude Desktop:** add this to `%APPDATA%\Claude\claude_desktop_config.json`
and restart Claude Desktop:

```json
{
  "mcpServers": {
    "product-agent": {
      "command": "C:/path/to/product-agent-mcp/.venv/Scripts/python.exe",
      "args": ["C:/path/to/product-agent-mcp/server.py"]
    }
  }
}
```

## Next steps

- Read products from a real shop API (Shopify) instead of a JSON file.
- A second agent for purchasing that uses `get_sales_and_stock` to suggest orders.
- A coordinating agent that hands tasks to the listing and purchasing agents.
