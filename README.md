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

## Example run

Prompt in Claude Code: *Write and save listings for every product that does not
have one yet.* The agent listed the catalogue, read the facts and the brand
guide for each product, checked every draft and saved all 8 listings
(`data/listings.json`). Two of them:

> **Moss & Pebble Silicone Teether Ring, BPA-free** (12/12)
>
> This teether ring gives your baby something to chew on when new teeth are
> coming through. It is made from food-grade silicone, is BPA-free and meets the
> EN 71 toy standard. The textured surface is made for sore gums, and the ring is
> easy for small hands to hold. You can cool it in the fridge before use. Choose
> Sage or Sand. It goes in the dishwasher on the top rack. Suitable for babies
> aged 3 months+.

> **Nordvik Kids Rain Jacket with Detachable Hood** (12/12)
>
> This rain jacket is made for wet walks to school and puddle days at the park.
> It is made from recycled polyester with a PU coating, and the seams are taped.
> The hood is detachable, and there are reflective details on the back and
> sleeves. Choose from Mustard or Navy. Machine wash at 30 °C and do not tumble
> dry. Suitable for children aged 2-8 years.

For the teether, the agent rewrote the product data's "dishwasher safe" as "goes
in the dishwasher on the top rack" and avoided "soothing", because the brand
guide bans safety and medical promises.

## What the first run showed

Every draft passed all 12 rules on the first check, so the agent never had to
fix anything. That sounds good, but the agent's own report pointed out phrases
that go beyond the product data and still passed: "keeps small hands warm",
"easy to put on", "help your child be seen".

The rules catch what can be counted or matched (length, materials, banned
words, certifications). They cannot tell whether a benefit is supported by the
facts. In a second run the agent rewrote those four listings without the
unsupported phrases (the rain jacket above is the revised version), but a
check for supported claims is still the next thing to build.

## Testing the checker itself

A deliberate test: asking the agent to save a teether listing that called it
"100% safe" and "the best teether ever". `save_listing` refused it (11/12, rule
"no banned claims") and nothing was written.

Probing further showed false alarms. The first checker matched banned phrases
anywhere in the text, so "small **imperfect**ions in the knit" was rejected for
`perfect`, and "the cuff se**cures** with a stud" for `cures`. Banned phrases
and certifications are now matched as whole words only, and both sentences are
in the test set so the false alarm cannot come back.

One case is kept as a known limit (`xfail` in the tests): "wash it **the best**
way for cotton" is advice, not a superlative, but uses the same words as "the
best romper". A word list cannot tell the two apart; that also needs a check
that understands meaning.

## Next steps

- A "supported claims" check: compare every sentence with the product facts
  (for example with a second model as a judge, tested on hand-labelled
  sentences) and flag benefits the data does not support.
- Read products from a real shop API (Shopify) instead of a JSON file.
- A second agent for purchasing that uses `get_sales_and_stock` to suggest orders.
- A coordinating agent that hands tasks to the listing and purchasing agents.
