"""
tools.py

The four FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
    compare_price(item, listings)                  → str   [stretch]
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    results = []

    for item in listings:
        if max_price is not None and item.get("price", 0) > max_price:
            continue
        if size is not None:
            item_size = str(item.get("size", ""))
            if size.lower() not in item_size.lower():
                continue

        text_to_search = f"{item.get('title', '')} {item.get('description', '')} {' '.join(item.get('style_tags', []))}".lower()
        keywords = set(description.lower().split())
        score = sum(1 for kw in keywords if kw in text_to_search)

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    items = wardrobe.get("items", [])
    client = _get_groq_client()

    if not items:
        prompt = f"The user just thrifted '{new_item.get('title')}' (Category: {new_item.get('category')}, Style: {', '.join(new_item.get('style_tags', []))}). Provide general styling advice, including what kinds of items pair well with it and what vibe it suits."
    else:
        wardrobe_list = "\n".join([f"- {item['name']} (Style: {', '.join(item.get('style_tags', []))})" for item in items])
        prompt = f"The user just thrifted '{new_item.get('title')}' (Category: {new_item.get('category')}, Style: {', '.join(new_item.get('style_tags', []))}).\n\nTheir current wardrobe includes:\n{wardrobe_list}\n\nSuggest 1-2 specific outfit combinations using this new item and pieces from their wardrobe."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Error: No outfit data provided to generate a fit card."

    client = _get_groq_client()
    prompt = f"Write a 2-4 sentence Instagram/TikTok caption for an OOTD post.\n\nThe item: {new_item.get('title')} (Price: ${new_item.get('price', 0)}, Platform: {new_item.get('platform')})\nOutfit details: {outfit}\n\nGuidelines:\n- Feel casual and authentic (not a product description).\n- Mention the item name, price, and platform naturally (once each).\n- Capture the outfit vibe in specific terms."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()


# ── Tool 4: compare_price (stretch) ──────────────────────────────────────────

def compare_price(item: dict, listings: list[dict]) -> str:
    """
    Estimate whether an item's price is fair by comparing it against other
    listings in the same category from the dataset.

    Args:
        item:     A listing dict (the item the user is considering buying).
                  Must contain at least 'price' (float) and 'category' (str).
        listings: The full list of listing dicts from load_listings().
                  Used to find comparable items in the same category.

    Returns:
        A human-readable string describing whether the price is a good deal,
        including the median price and price range for comparable items.
        Returns a graceful message string if no comparable listings are found —
        does NOT raise an exception.

    Comparison logic:
        1. Filter listings to the same category as the item (excluding itself).
        2. If fewer than 2 comparables exist, return a "not enough data" message.
        3. Compute median price of comparables.
        4. Classify item price as:
           - Great deal  (>20% below median)
           - Fair price  (within ±20% of median)
           - Pricey      (>20% above median)
        5. Return the verdict with the median and price range as supporting data.
    """
    item_price = item.get("price")
    item_category = item.get("category", "").lower()
    item_id = item.get("id", "")

    if item_price is None:
        return "Unable to assess price — no price data available for this listing."

    # Gather comparables: same category, not the same item
    comparables = [
        l["price"] for l in listings
        if l.get("category", "").lower() == item_category
        and l.get("id") != item_id
        and isinstance(l.get("price"), (int, float))
    ]

    if len(comparables) < 2:
        return (
            f"Not enough comparable listings in the '{item_category}' category "
            f"to assess pricing. Only {len(comparables)} similar item(s) found."
        )

    comparables_sorted = sorted(comparables)
    n = len(comparables_sorted)
    if n % 2 == 0:
        median = (comparables_sorted[n // 2 - 1] + comparables_sorted[n // 2]) / 2
    else:
        median = comparables_sorted[n // 2]

    low = comparables_sorted[0]
    high = comparables_sorted[-1]
    pct_diff = (item_price - median) / median * 100

    if pct_diff < -20:
        verdict = "🟢 Great deal"
        explanation = f"This is {abs(pct_diff):.0f}% below the median — a solid find."
    elif pct_diff <= 20:
        verdict = "🟡 Fair price"
        explanation = f"This is right in line with typical thrifted {item_category} prices."
    else:
        verdict = "🔴 Pricey"
        explanation = f"This is {pct_diff:.0f}% above the median — you might find better value."

    return (
        f"{verdict} — ${item_price:.2f}\n"
        f"{explanation}\n\n"
        f"Comparable thrifted {item_category} on resale:\n"
        f"  • Median price: ${median:.2f}\n"
        f"  • Range: ${low:.2f} – ${high:.2f}\n"
        f"  • Based on {n} similar listing(s)"
    )

