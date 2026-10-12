"""MCP server that gives an AI agent access to a small product catalogue.

The agent (Claude) can read products, sales and stock, read the brand guide,
check a draft listing against the rules, and save listings that pass.

Run by an MCP client (Claude Desktop or Claude Code) over stdio:
    .venv\\Scripts\\python.exe server.py
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from checker import check_listing

ROOT = Path(__file__).resolve().parent
PRODUCTS_FILE = ROOT / "data" / "products.json"
LISTINGS_FILE = ROOT / "data" / "listings.json"
BRAND_GUIDE = ROOT / "brand_guide.md"

mcp = MCPServer(
    name="product-agent",
    instructions=(
        "Tools for writing product listings for a children's brand shop. "
        "Before writing, read the brand guide with get_brand_guide and the facts with get_product. "
        "Run check_listing on every draft and fix all failed rules before calling save_listing."
    ),
)


def _products() -> list[dict]:
    return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))


def _product(sku: str) -> dict:
    for p in _products():
        if p["sku"].lower() == sku.strip().lower():
            return p
    raise ValueError(f"No product with SKU '{sku}'. Use list_products to see all SKUs.")


def _listings() -> dict:
    if LISTINGS_FILE.exists():
        return json.loads(LISTINGS_FILE.read_text(encoding="utf-8"))
    return {}


@mcp.tool()
def list_products(category: str = "") -> list[dict]:
    """List products (SKU, brand, name, category), optionally filtered by category.

    Also shows whether each product already has a saved listing.
    """
    saved = _listings()
    return [
        {"sku": p["sku"], "brand": p["brand"], "name": p["name"], "category": p["category"],
         "has_listing": p["sku"] in saved}
        for p in _products()
        if not category or category.lower() in p["category"].lower()
    ]


@mcp.tool()
def get_product(sku: str) -> dict:
    """Get every fact about one product: materials, age range, certifications, features, care, price."""
    p = _product(sku)
    return {k: v for k, v in p.items() if k not in ("stock", "sales_last_4_weeks")}


@mcp.tool()
def get_sales_and_stock(sku: str = "") -> list[dict]:
    """Sales for the last 4 weeks, current stock and weeks of stock left.

    Leave sku empty to get every product, sorted by fewest weeks of stock left.
    Useful for deciding which listings matter most and what to reorder.
    """
    rows = []
    for p in ([_product(sku)] if sku else _products()):
        weekly = p["sales_last_4_weeks"]
        avg = sum(weekly) / len(weekly)
        trend = "rising" if weekly[-1] > weekly[0] * 1.2 else "falling" if weekly[-1] < weekly[0] * 0.8 else "steady"
        rows.append({
            "sku": p["sku"], "name": f"{p['brand']} {p['name']}",
            "stock": p["stock"], "sales_last_4_weeks": weekly, "trend": trend,
            "weeks_of_stock_left": round(p["stock"] / avg, 1) if avg else None,
        })
    return sorted(rows, key=lambda r: r["weeks_of_stock_left"] if r["weeks_of_stock_left"] is not None else 999)


@mcp.tool()
def get_brand_guide() -> str:
    """The brand voice guide: tone, structure, length limits and words that must never be used."""
    return BRAND_GUIDE.read_text(encoding="utf-8")


@mcp.tool()
def check_listing_draft(sku: str, title: str, description: str, bullets: list[str]) -> dict:
    """Check a draft listing against the brand rules without saving it.

    Returns a score and every failed rule with a reason. Fix the failures and check again.
    """
    return check_listing(_product(sku), {"title": title, "description": description, "bullets": bullets})


@mcp.tool()
def save_listing(sku: str, title: str, description: str, bullets: list[str]) -> dict:
    """Save a listing. It is only saved if it passes every rule; otherwise the failures are returned."""
    product = _product(sku)
    listing = {"title": title, "description": description, "bullets": bullets}
    result = check_listing(product, listing)
    if not result["passed"]:
        return {"saved": False, **result}
    saved = _listings()
    saved[product["sku"]] = {**listing, "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    LISTINGS_FILE.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": True, **result}


@mcp.resource("guide://brand-voice", name="Brand voice guide", mime_type="text/markdown")
def brand_guide_resource() -> str:
    return BRAND_GUIDE.read_text(encoding="utf-8")


@mcp.prompt()
def write_listing(sku: str) -> str:
    """Ready-made instruction: write and save the listing for one product."""
    return (
        f"Write the product listing for SKU {sku}. Read the brand guide and the product facts first. "
        "Draft a title, a description and 3 to 5 bullets, run check_listing_draft, fix every failed rule, "
        "then save it with save_listing. Finish by showing me the saved listing and its score."
    )


if __name__ == "__main__":
    mcp.run()
