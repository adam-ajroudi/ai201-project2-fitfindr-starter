"""
Utility functions for loading the mock listings dataset and wardrobe schema.
Use these in your tool implementations to access the data without re-reading
the files each time.
"""

import json
import os
from typing import Optional


# Resolve the path to the data directory relative to this file
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_listings() -> list[dict]:
    """
    Load all mock listings from the dataset.

    Returns:
        A list of listing dictionaries. Each listing has the following fields:
        - id (str)
        - title (str)
        - description (str)
        - category (str): one of tops, bottoms, outerwear, shoes, accessories
        - style_tags (list[str])
        - size (str)
        - condition (str): excellent, good, or fair
        - price (float)
        - colors (list[str])
        - brand (str or None)
        - platform (str): depop, thredUp, or poshmark
    """
    path = os.path.join(_DATA_DIR, "listings.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_wardrobe_schema() -> dict:
    """
    Load the wardrobe schema, including the example wardrobe and empty template.

    Returns:
        A dictionary containing:
        - schema: the field definitions for a wardrobe item
        - example_wardrobe: a sample wardrobe with 10 items
        - empty_wardrobe: a starting template for a new user
    """
    path = os.path.join(_DATA_DIR, "wardrobe_schema.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_example_wardrobe() -> dict:
    """
    Convenience function — returns just the example wardrobe items list.

    Returns:
        A wardrobe dict with an 'items' key containing a list of wardrobe items.
    """
    schema = load_wardrobe_schema()
    return schema["example_wardrobe"]


def get_empty_wardrobe() -> dict:
    """
    Convenience function — returns an empty wardrobe template.

    Returns:
        A wardrobe dict with an empty 'items' list.
    """
    schema = load_wardrobe_schema()
    return schema["empty_wardrobe"]


_DEFAULT_PROFILE = {
    "preferred_styles": [],
    "preferred_sizes": [],
    "past_searches": [],
    "saved_wardrobe": {"items": []},
}


def load_style_profile() -> dict:
    """
    Load the user's persistent style profile from disk.

    The profile is stored at data/style_profile.json. If the file does not
    exist yet (first-time user), a default empty profile is returned.

    Returns:
        A dict with keys:
        - preferred_styles (list[str]): style tags the user gravitates toward
        - preferred_sizes (list[str]): their usual sizes
        - past_searches (list[str]): last 20 queries the user ran
        - saved_wardrobe (dict): a wardrobe dict with an 'items' list
    """
    path = os.path.join(_DATA_DIR, "style_profile.json")
    if not os.path.exists(path):
        return dict(_DEFAULT_PROFILE)
    with open(path, "r", encoding="utf-8") as f:
        profile = json.load(f)
    # Ensure all expected keys exist even if the file is from an older version
    for key, default in _DEFAULT_PROFILE.items():
        profile.setdefault(key, default)
    return profile


def save_style_profile(profile: dict) -> None:
    """
    Persist the user's style profile to data/style_profile.json.

    Args:
        profile: The profile dict (same structure as returned by load_style_profile).
    """
    path = os.path.join(_DATA_DIR, "style_profile.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


# --- Quick sanity check ---
if __name__ == "__main__":
    listings = load_listings()
    print(f"Loaded {len(listings)} listings.")
    print(f"First listing: {listings[0]['title']} — ${listings[0]['price']}")

    wardrobe = get_example_wardrobe()
    print(f"\nExample wardrobe has {len(wardrobe['items'])} items.")
    print(f"First item: {wardrobe['items'][0]['name']}")

    profile = load_style_profile()
    print(f"\nStyle profile loaded. Past searches: {len(profile['past_searches'])}")

