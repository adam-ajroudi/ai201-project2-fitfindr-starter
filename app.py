"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""


import gradio as gr


from agent import run_agent
from utils.data_loader import (
    get_example_wardrobe,
    get_empty_wardrobe,
    load_style_profile,
    save_style_profile,
)


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(
    user_query: str,
    wardrobe_choice: str,
) -> tuple[str, str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:      The text the user typed into the search box.
        wardrobe_choice: One of "Example wardrobe", "Empty wardrobe (new user)",
                         or "Use saved profile".

    Returns:
        A tuple of four strings:
            (listing_text, outfit_suggestion, fit_card, price_comparison)
        Each string maps to one of the four output panels in the UI.
    """
    if not user_query or not user_query.strip():
        return "Please enter a search query.", "", "", ""

    if wardrobe_choice == "Example wardrobe":
        wardrobe = get_example_wardrobe()
    elif wardrobe_choice == "Use saved profile":
        profile = load_style_profile()
        wardrobe = profile.get("saved_wardrobe", get_empty_wardrobe())
        if not wardrobe.get("items"):
            wardrobe = get_example_wardrobe()
    else:
        wardrobe = get_empty_wardrobe()

    session = run_agent(user_query, wardrobe)

    # Persist the search to the style profile
    profile = load_style_profile()
    profile.setdefault("past_searches", []).append(user_query)
    # Keep only last 20 searches
    profile["past_searches"] = profile["past_searches"][-20:]
    save_style_profile(profile)

    if session.get("error"):
        return f"❌ {session['error']}", "", "", ""

    item = session["selected_item"]
    listing_text = f"👕 {item['title']}\n"
    listing_text += f"💰 ${item['price']:.2f} on {item['platform'].title()}\n"
    if item.get("size"):
        listing_text += f"📏 Size: {item['size']}\n"
    listing_text += f"🏷️ Condition: {item.get('condition', 'unknown').title()}\n"
    listing_text += f"\n{item['description']}"

    if session.get("fallback_message"):
        listing_text = f"⚠️ {session['fallback_message']}\n\n" + listing_text

    price_text = session.get("price_comparison") or ""

    return listing_text, session["outfit_suggestion"], session["fit_card"], price_text


def save_wardrobe_item(
    item_name: str,
    item_category: str,
    item_colors: str,
    item_style_tags: str,
) -> str:
    """Save a new item to the user's persistent style profile wardrobe."""
    if not item_name or not item_name.strip():
        return "⚠️ Please enter an item name."

    profile = load_style_profile()
    wardrobe = profile.get("saved_wardrobe", {"items": []})
    items = wardrobe.get("items", [])

    new_id = f"w_{len(items) + 1:03d}"
    colors = [c.strip() for c in item_colors.split(",") if c.strip()]
    tags = [t.strip() for t in item_style_tags.split(",") if t.strip()]

    new_item = {
        "id": new_id,
        "name": item_name.strip(),
        "category": item_category,
        "colors": colors,
        "style_tags": tags,
        "notes": None,
    }
    items.append(new_item)
    wardrobe["items"] = items
    profile["saved_wardrobe"] = wardrobe
    save_style_profile(profile)

    return f"✅ Added '{item_name}' to your saved wardrobe ({len(items)} items total)."


def view_saved_wardrobe() -> str:
    """Return a formatted view of the current saved wardrobe."""
    profile = load_style_profile()
    items = profile.get("saved_wardrobe", {}).get("items", [])
    if not items:
        return "Your saved wardrobe is empty. Add items below to get personalized outfit suggestions!"
    lines = [f"**Your Saved Wardrobe ({len(items)} items)**\n"]
    for item in items:
        colors = ", ".join(item.get("colors", []))
        tags = ", ".join(item.get("style_tags", []))
        lines.append(f"• **{item['name']}** ({item['category']}) — {colors} | _{tags}_")
    return "\n".join(lines)


def clear_saved_wardrobe() -> str:
    """Clear all items from the saved wardrobe."""
    profile = load_style_profile()
    profile["saved_wardrobe"] = {"items": []}
    save_style_profile(profile)
    return "🗑️ Saved wardrobe cleared."


def view_past_searches() -> str:
    """Return the user's recent search history."""
    profile = load_style_profile()
    searches = profile.get("past_searches", [])
    if not searches:
        return "No searches yet."
    recent = list(reversed(searches[-10:]))
    lines = ["**Recent Searches**\n"]
    for s in recent:
        lines.append(f"• {s}")
    return "\n".join(lines)


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]


def build_interface():
    with gr.Blocks(
        title="FitFindr",
        theme=gr.themes.Soft(primary_hue="violet", secondary_hue="purple"),
    ) as demo:
        gr.Markdown("""
# 🛍️ FitFindr
**Find secondhand pieces and get outfit ideas based on your wardrobe.**
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Tabs():
            # ── Main Search Tab ──────────────────────────────────────────────
            with gr.Tab("🔍 Search"):
                with gr.Row():
                    query_input = gr.Textbox(
                        label="What are you looking for?",
                        placeholder="e.g. vintage graphic tee under $30, size M",
                        lines=2,
                        scale=3,
                    )
                    wardrobe_choice = gr.Radio(
                        choices=[
                            "Example wardrobe",
                            "Empty wardrobe (new user)",
                            "Use saved profile",
                        ],
                        value="Example wardrobe",
                        label="Wardrobe",
                        scale=1,
                    )

                submit_btn = gr.Button("Find it ✨", variant="primary", size="lg")

                with gr.Row():
                    listing_output = gr.Textbox(
                        label="🛍️ Top listing found",
                        lines=8,
                        interactive=False,
                    )
                    outfit_output = gr.Textbox(
                        label="👗 Outfit idea",
                        lines=8,
                        interactive=False,
                    )

                with gr.Row():
                    fitcard_output = gr.Textbox(
                        label="✨ Your fit card",
                        lines=6,
                        interactive=False,
                    )
                    price_output = gr.Textbox(
                        label="💰 Price check",
                        lines=6,
                        interactive=False,
                    )

                gr.Examples(
                    examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
                    inputs=[query_input, wardrobe_choice],
                    label="Try these queries",
                )

                submit_btn.click(
                    fn=handle_query,
                    inputs=[query_input, wardrobe_choice],
                    outputs=[listing_output, outfit_output, fitcard_output, price_output],
                )
                query_input.submit(
                    fn=handle_query,
                    inputs=[query_input, wardrobe_choice],
                    outputs=[listing_output, outfit_output, fitcard_output, price_output],
                )

            # ── Style Profile Tab ────────────────────────────────────────────
            with gr.Tab("👤 My Style Profile"):
                gr.Markdown("""
### Your Saved Wardrobe
Items you add here will be remembered across sessions.
Select **"Use saved profile"** on the Search tab to use them.
                """)

                wardrobe_display = gr.Markdown(
                    value=view_saved_wardrobe(),
                    label="Current wardrobe",
                )

                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh", size="sm")
                    clear_btn = gr.Button("🗑️ Clear wardrobe", size="sm", variant="stop")

                gr.Markdown("### ➕ Add a wardrobe item")

                with gr.Row():
                    item_name_input = gr.Textbox(
                        label="Item name",
                        placeholder="e.g. Baggy straight-leg jeans",
                    )
                    item_category_input = gr.Dropdown(
                        choices=["tops", "bottoms", "outerwear", "shoes", "accessories"],
                        label="Category",
                        value="tops",
                    )

                with gr.Row():
                    item_colors_input = gr.Textbox(
                        label="Colors (comma-separated)",
                        placeholder="e.g. dark blue, indigo",
                    )
                    item_tags_input = gr.Textbox(
                        label="Style tags (comma-separated)",
                        placeholder="e.g. streetwear, baggy, denim",
                    )

                add_btn = gr.Button("Add to wardrobe", variant="primary")
                add_status = gr.Textbox(label="Status", interactive=False, lines=1)

                add_btn.click(
                    fn=save_wardrobe_item,
                    inputs=[
                        item_name_input,
                        item_category_input,
                        item_colors_input,
                        item_tags_input,
                    ],
                    outputs=[add_status],
                )
                add_btn.click(
                    fn=view_saved_wardrobe,
                    inputs=[],
                    outputs=[wardrobe_display],
                )
                refresh_btn.click(
                    fn=view_saved_wardrobe,
                    inputs=[],
                    outputs=[wardrobe_display],
                )
                clear_btn.click(
                    fn=clear_saved_wardrobe,
                    inputs=[],
                    outputs=[add_status],
                )
                clear_btn.click(
                    fn=view_saved_wardrobe,
                    inputs=[],
                    outputs=[wardrobe_display],
                )

                gr.Markdown("### 🕐 Recent Searches")
                searches_display = gr.Markdown(value=view_past_searches())
                refresh_searches_btn = gr.Button("🔄 Refresh searches", size="sm")
                refresh_searches_btn.click(
                    fn=view_past_searches,
                    inputs=[],
                    outputs=[searches_display],
                )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
