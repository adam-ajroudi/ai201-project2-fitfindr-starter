"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import compare_price, create_fit_card, search_listings, suggest_outfit
from utils.data_loader import load_listings


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "price_comparison": None,    # string returned by compare_price [stretch]
        "fallback_message": None,    # set if retry logic was triggered [stretch]
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Execute the FitFindr planning loop for a single user interaction.

    Planning loop logic (conditional, not fixed-sequence):

    1. Parse the query to extract description, size, and max_price via regex.
    2. Call search_listings(description, size, max_price).
       a. If results are empty AND size/price constraints were present:
          → Retry with size=None (drop size constraint first).
          → If still empty and max_price was set: retry with all constraints dropped.
          → Set session["fallback_message"] so the UI can surface what changed.
       b. If results are empty after all retries:
          → Set session["error"] with an actionable message and RETURN EARLY.
          → suggest_outfit and create_fit_card are NOT called.
    3. Set session["selected_item"] = results[0] (top relevance-scored match).
    4. Call suggest_outfit(selected_item, wardrobe).
       → If wardrobe is empty, suggest_outfit handles this gracefully (general advice).
    5. Call create_fit_card(outfit_suggestion, selected_item).
    6. Call compare_price(selected_item, all_listings) [stretch].
    7. Return the fully populated session dict.

    Args:
        query:    Natural language user query (e.g. "vintage tee under $30, size M").
        wardrobe: Wardrobe dict with 'items' list; may be empty.

    Returns:
        A session dict. On success, fit_card and outfit_suggestion are populated.
        On failure, error is set and fit_card/outfit_suggestion remain None.
    """
    session = _new_session(query, wardrobe)

    # ── Step 1: Parse query ───────────────────────────────────────────────────
    price_match = re.search(r'\$?(\d+(?:\.\d{1,2})?)', query)
    max_price = float(price_match.group(1)) if price_match else None

    size_match = re.search(r'size\s+([A-Za-z0-9/]+)', query, re.IGNORECASE)
    size = size_match.group(1) if size_match else None

    # Build description by stripping numeric and size tokens
    desc = query
    if max_price:
        desc = re.sub(r'under\s+\$?\d+(?:\.\d{1,2})?', '', desc, flags=re.IGNORECASE)
        desc = re.sub(r'\$?\d+(?:\.\d{1,2})?', '', desc)
    if size:
        desc = re.sub(r'size\s+[A-Za-z0-9/]+', '', desc, flags=re.IGNORECASE)
    # Remove common filler words to sharpen keyword matching
    desc = re.sub(r'\b(looking for|a|an|the|in|i\'m|im|want|need|find|me)\b', '', desc, flags=re.IGNORECASE)
    description = ' '.join(desc.split())  # normalize whitespace

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # ── Step 2: search_listings with retry fallback (stretch) ─────────────────
    results = search_listings(description, size, max_price)

    if not results and (size is not None or max_price is not None):
        # Retry 1: drop size constraint, keep price
        if size is not None:
            results = search_listings(description, None, max_price)
            if results:
                session["fallback_message"] = (
                    f"No listings found for size {size}. "
                    f"Showing results in other sizes — check if they work for you."
                )

        # Retry 2: drop all constraints
        if not results:
            results = search_listings(description, None, None)
            if results:
                session["fallback_message"] = (
                    "Couldn't find items matching your size/price constraints. "
                    "Showing the closest matches — prices and sizes may vary."
                )

    # ── Step 3: Early exit if still no results ────────────────────────────────
    if not results:
        session["error"] = (
            "No listings found matching your description. "
            "Try broader keywords (e.g. 'jacket' instead of 'leather moto jacket') "
            "or remove size and price filters."
        )
        return session

    session["search_results"] = results

    # ── Step 4: Select top item ───────────────────────────────────────────────
    session["selected_item"] = results[0]

    # ── Step 5: suggest_outfit ────────────────────────────────────────────────
    # suggest_outfit handles empty wardrobe gracefully — no guard needed here
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], wardrobe)

    # ── Step 6: create_fit_card ───────────────────────────────────────────────
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"],
    )

    # ── Step 7: compare_price [stretch] ──────────────────────────────────────
    all_listings = load_listings()
    session["price_comparison"] = compare_price(session["selected_item"], all_listings)

    # ── Step 8: Return ────────────────────────────────────────────────────────
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_empty_wardrobe, get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found:    {session['selected_item']['title']} — ${session['selected_item']['price']}")
        print(f"\nOutfit:   {session['outfit_suggestion'][:200]}...")
        print(f"\nFit card: {session['fit_card']}")
        print(f"\nPrice:    {session['price_comparison']}")
        if session["fallback_message"]:
            print(f"\nFallback: {session['fallback_message']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

    print("\n\n=== Empty wardrobe path ===\n")
    session3 = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_empty_wardrobe(),
    )
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"Found: {session3['selected_item']['title']}")
        print(f"\nOutfit (empty wardrobe): {session3['outfit_suggestion'][:200]}...")
