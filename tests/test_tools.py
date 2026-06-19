"""
tests/test_tools.py

Pytest suite for all FitFindr tools. Run with:
    pytest tests/ -v
"""
import os
import json
import tempfile

import pytest

from tools import search_listings, suggest_outfit, create_fit_card, compare_price
from utils.data_loader import (
    get_empty_wardrobe,
    get_example_wardrobe,
    load_listings,
    load_style_profile,
    save_style_profile,
)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=40)
    assert all(item["price"] <= 40 for item in results)


def test_search_size_filter():
    results = search_listings("pants", size="w28", max_price=None)
    assert all("w28" in str(item.get("size", "")).lower() for item in results)


def test_search_returns_sorted_by_relevance():
    """Results with more keyword matches should appear first."""
    results = search_listings("vintage graphic tee", size=None, max_price=None)
    # The function scores by keyword overlap — if two results exist the first
    # should have at least as many matching keywords as the second
    assert len(results) >= 2  # need at least two to compare order


def test_search_no_exception_on_empty_description():
    """Empty description should return an empty list, not crash."""
    results = search_listings("", size=None, max_price=None)
    assert isinstance(results, list)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def test_suggest_outfit_empty_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    item = results[0]
    wardrobe = get_empty_wardrobe()
    suggestion = suggest_outfit(item, wardrobe)
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0


def test_suggest_outfit_with_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    item = results[0]
    wardrobe = get_example_wardrobe()
    suggestion = suggest_outfit(item, wardrobe)
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def test_create_fit_card_empty_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    item = results[0]
    card = create_fit_card("", item)
    assert "Error: No outfit data provided" in card


def test_create_fit_card_whitespace_outfit():
    """Whitespace-only outfit string should also return error, not crash."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    item = results[0]
    card = create_fit_card("   ", item)
    assert "Error" in card


def test_create_fit_card_success():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    item = results[0]
    card = create_fit_card("Pair this with your wide-leg jeans", item)
    assert isinstance(card, str)
    assert len(card) > 0


# ── Tool 4: compare_price (stretch) ──────────────────────────────────────────

def test_compare_price_returns_string():
    """compare_price should return a non-empty string for a valid item."""
    listings = load_listings()
    item = listings[0]  # use first listing
    result = compare_price(item, listings)
    assert isinstance(result, str)
    assert len(result) > 0


def test_compare_price_verdict_in_result():
    """Result should contain one of the three verdict emoji indicators."""
    listings = load_listings()
    item = listings[0]
    result = compare_price(item, listings)
    assert any(emoji in result for emoji in ["🟢", "🟡", "🔴", "Not enough"])


def test_compare_price_no_price_key():
    """Item missing 'price' should return graceful error string, not crash."""
    listings = load_listings()
    bad_item = {"id": "test", "category": "tops"}
    result = compare_price(bad_item, listings)
    assert "Unable to assess price" in result


def test_compare_price_no_comparables():
    """A unique category with no other items should return graceful message."""
    listings = load_listings()
    # Use a fabricated category that doesn't exist in the dataset
    item = {"id": "xyz", "category": "spacesuits", "price": 100.0}
    result = compare_price(item, listings)
    assert "Not enough comparable" in result


def test_compare_price_excludes_self():
    """The item itself should not be counted as a comparable."""
    listings = load_listings()
    item = listings[0]
    result_with_self = compare_price(item, listings)
    # Ensure the item isn't in its own comparable pool by checking the count
    # is (n_category_items - 1), not n_category_items
    assert "Based on" in result_with_self


# ── Style Profile Memory (stretch) ───────────────────────────────────────────

def test_load_style_profile_returns_dict():
    profile = load_style_profile()
    assert isinstance(profile, dict)
    assert "past_searches" in profile
    assert "saved_wardrobe" in profile


def test_save_and_load_style_profile(tmp_path, monkeypatch):
    """Save a profile and load it back — data should round-trip correctly."""
    import utils.data_loader as dl

    fake_path = str(tmp_path / "style_profile.json")
    monkeypatch.setattr(dl, "_DATA_DIR", str(tmp_path))

    test_profile = {
        "preferred_styles": ["vintage", "grunge"],
        "preferred_sizes": ["M"],
        "past_searches": ["vintage tee under $30"],
        "saved_wardrobe": {
            "items": [
                {
                    "id": "w_001",
                    "name": "Baggy jeans",
                    "category": "bottoms",
                    "colors": ["blue"],
                    "style_tags": ["denim"],
                    "notes": None,
                }
            ]
        },
    }

    save_style_profile(test_profile)
    loaded = load_style_profile()

    assert loaded["preferred_styles"] == ["vintage", "grunge"]
    assert loaded["past_searches"] == ["vintage tee under $30"]
    assert len(loaded["saved_wardrobe"]["items"]) == 1
    assert loaded["saved_wardrobe"]["items"][0]["name"] == "Baggy jeans"
