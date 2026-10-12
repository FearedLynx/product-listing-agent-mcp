"""Checks a product listing against the measurable rules in brand_guide.md.

A listing is a dict with "title", "description" and "bullets" (a list of strings).
check_listing() returns every rule with pass/fail and a reason, so an agent can
read the result and fix its own text.
"""
import re

TITLE_MAX = 70
DESCRIPTION_WORDS = (50, 110)
BULLETS_COUNT = (3, 5)
BULLET_MAX = 90

BANNED_PHRASES = [
    "100% safe", "completely safe", "totally safe", "guaranteed", "prevents", "cures",
    "the best", "best ever", "perfect", "number one", "world-class", "must-have",
]
# Claims that are only allowed when the product data lists them.
KNOWN_CERTIFICATIONS = ["GOTS", "OEKO-TEX", "EN 71", "BPA-free", "FSC", "hypoallergenic"]


def _words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _age_variants(age_range: str) -> list[str]:
    """'0-12 months' -> ['0-12 months', '0 to 12 months']; '12 months+' -> ['12 months']."""
    variants = [age_range, age_range.rstrip("+").strip()]
    m = re.match(r"(\d+)-(\d+)\s+(\w+)", age_range)
    if m:
        variants.append(f"{m.group(1)} to {m.group(2)} {m.group(3)}")
    return [v.lower() for v in variants]


def check_listing(product: dict, listing: dict) -> dict:
    title = (listing.get("title") or "").strip()
    description = (listing.get("description") or "").strip()
    bullets = [b.strip() for b in (listing.get("bullets") or []) if b.strip()]
    everything = " ".join([title, description, *bullets])
    lower = everything.lower()
    results = []

    def rule(name: str, ok: bool, detail: str = ""):
        results.append({"rule": name, "passed": bool(ok), "detail": "" if ok else detail})

    rule("title length", 0 < len(title) <= TITLE_MAX,
         f"Title is {len(title)} characters; the limit is {TITLE_MAX}.")
    rule("title has brand", product["brand"].lower() in title.lower(),
         f"Put the brand '{product['brand']}' in the title.")

    n = _words(description)
    rule("description length", DESCRIPTION_WORDS[0] <= n <= DESCRIPTION_WORDS[1],
         f"Description is {n} words; it must be {DESCRIPTION_WORDS[0]} to {DESCRIPTION_WORDS[1]}.")

    rule("bullet count", BULLETS_COUNT[0] <= len(bullets) <= BULLETS_COUNT[1],
         f"There are {len(bullets)} bullets; use {BULLETS_COUNT[0]} to {BULLETS_COUNT[1]}.")
    long_bullets = [b for b in bullets if len(b) > BULLET_MAX]
    rule("bullet length", not long_bullets,
         f"{len(long_bullets)} bullet(s) are over {BULLET_MAX} characters: {long_bullets}")

    missing = [m for m in product["materials"] if m.lower() not in lower]
    rule("materials mentioned", not missing, f"Mention these materials: {missing}")

    rule("age range mentioned", any(v in lower for v in _age_variants(product["age_range"])),
         f"Mention the age range '{product['age_range']}'.")

    found_banned = [p for p in BANNED_PHRASES if p in lower]
    rule("no banned claims", not found_banned, f"Remove: {found_banned}")

    allowed = {c.lower() for c in product.get("certifications", [])}
    invented = [c for c in KNOWN_CERTIFICATIONS if c.lower() in lower and c.lower() not in allowed]
    rule("no invented certifications", not invented,
         f"The product data does not list {invented}; remove them.")

    rule("no exclamation marks", "!" not in everything, "Remove exclamation marks.")
    rule("no long dashes", "—" not in everything and "–" not in everything,
         "Replace long dashes (— or –) with a full stop, comma or colon.")
    rule("no emoji", not re.search(r"[\U0001F000-\U0001FFFF☀-➿]", everything),
         "Remove emoji.")

    passed = sum(r["passed"] for r in results)
    return {
        "sku": product["sku"],
        "passed": passed == len(results),
        "score": f"{passed}/{len(results)}",
        "failed_rules": [r for r in results if not r["passed"]],
    }
