"""
AI Service - Claude Vision integration for photo grouping, listing generation,
market research, and stock photo discovery.
"""
import json
import base64
import re
import httpx
from pathlib import Path
from config import get_anthropic_key, get_ebay_config, EBAY_API_BASE

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


def _encode_image(path: str, max_dim: int = 1024) -> dict:
    """Encode image file to base64 for Claude API, resizing if needed."""
    from PIL import Image
    import io

    p = Path(path)
    img = Image.open(p)
    img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    data = base64.standard_b64encode(buf.getvalue()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


async def _call_claude(content: list, system: str = "", max_tokens: int = 4096) -> str:
    """Make a Claude API call and return the text response."""
    api_key = get_anthropic_key()
    if not api_key:
        raise ValueError("No Anthropic API key configured")

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            ANTHROPIC_URL,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        if resp.status_code != 200:
            print(f"Claude API error {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _get_ebay_app_token() -> str:
    """Get an eBay application token for API calls."""
    import urllib.parse
    config = get_ebay_config()
    creds = base64.b64encode(f"{config['app_id']}:{config['cert_id']}".encode()).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{EBAY_API_BASE}/identity/v1/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {creds}",
            },
            data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope",
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def search_ebay_sold(query: str, limit: int = 10) -> list:
    """Search eBay for recently sold/completed items to gauge market price."""
    try:
        token = await _get_ebay_app_token()
        async with httpx.AsyncClient(timeout=30) as client:
            # Search sold items via Browse API
            resp = await client.get(
                f"{EBAY_API_BASE}/buy/browse/v1/item_summary/search",
                params={
                    "q": query,
                    "filter": "buyingOptions:{FIXED_PRICE},conditions:{USED}",
                    "sort": "newlyListed",
                    "limit": str(limit),
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("itemSummaries", [])
                prices = []
                for item in items:
                    price = item.get("price", {})
                    if price.get("value"):
                        prices.append({
                            "title": item.get("title", ""),
                            "price": float(price["value"]),
                            "condition": item.get("condition", ""),
                        })
                return prices
    except Exception as e:
        print(f"eBay market research failed: {e}")
    return []


async def get_ebay_category_suggestion(title: str) -> dict:
    """Use eBay's category suggestion API to find the best category."""
    try:
        token = await _get_ebay_app_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{EBAY_API_BASE}/commerce/taxonomy/v1/category_tree/0/get_category_suggestions",
                params={"q": title},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                suggestions = data.get("categorySuggestions", [])
                if suggestions:
                    cat = suggestions[0].get("category", {})
                    return {
                        "id": cat.get("categoryId", ""),
                        "name": cat.get("categoryName", ""),
                    }
    except Exception as e:
        print(f"eBay category suggestion failed: {e}")
    return {"id": "", "name": ""}


async def search_stock_photos(query: str) -> list:
    """Search for stock/product photos of the item using web search."""
    try:
        api_key = get_anthropic_key()
        # Ask Claude to generate good search terms for finding stock photos
        # Then we'll use the eBay browse API to find listing photos of similar items
        token = await _get_ebay_app_token()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{EBAY_API_BASE}/buy/browse/v1/item_summary/search",
                params={
                    "q": query,
                    "filter": "conditions:{NEW}",
                    "sort": "bestMatch",
                    "limit": "5",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                photos = []
                for item in data.get("itemSummaries", []):
                    img = item.get("image", {})
                    url = img.get("imageUrl", "")
                    if url:
                        photos.append({
                            "url": url,
                            "title": item.get("title", ""),
                        })
                return photos[:3]
    except Exception as e:
        print(f"Stock photo search failed: {e}")
    return []


async def download_stock_photo(url: str, save_dir: Path, filename: str) -> str | None:
    """Download a stock photo and save it locally."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(resp.content))
                img = img.convert("RGB")
                save_path = save_dir / filename
                img.save(save_path, "JPEG", quality=90)
                # Make thumbnail
                thumb_dir = save_dir / "thumbs"
                thumb_dir.mkdir(exist_ok=True)
                thumb = img.copy()
                thumb.thumbnail((400, 400), Image.LANCZOS)
                thumb.save(thumb_dir / filename, "JPEG", quality=80)
                return str(save_path)
    except Exception as e:
        print(f"Stock photo download failed: {e}")
    return None


async def group_photos(photo_paths: list[str]) -> list[list[int]]:
    """Analyze photos and group them by item using Claude vision (two-pass)."""
    api_key = get_anthropic_key()
    if not api_key or len(photo_paths) <= 1:
        return [[i] for i in range(len(photo_paths))]

    # === PASS 1: Initial grouping ===
    print(f"  Grouping pass 1: analyzing {len(photo_paths)} photos...")
    content = []
    for i, path in enumerate(photo_paths):
        content.append({"type": "text", "text": f"Photo {i}:"})
        content.append(_encode_image(path))

    content.append({
        "type": "text",
        "text": """You are an expert at sorting photos of clothing items for resale listings. Multiple items were photographed and uploaded as a batch. Group photos that belong to the SAME item.

STEP 1 — INVENTORY: Before grouping, list every photo with a short description:
"Photo 0: Full front view of a BLACK wool coat"
"Photo 1: Close-up of tag on NAVY fabric"
...etc. Note the EXACT COLOR and GARMENT TYPE for each.

STEP 2 — GROUP BY STRICT MATCHING: Group photos only when ALL of these match:
  • EXACT COLOR — Black ≠ Navy ≠ Charcoal. Dark brown ≠ Black. Be precise about color.
  • GARMENT TYPE — Jacket ≠ Shirt ≠ Sweater ≠ Pants. Don't merge different garment types.
  • FABRIC/TEXTURE — Knit ≠ Woven ≠ Fleece. The texture must match.
  • BRAND — If two different brand tags are visible, they are DIFFERENT items. Period.

PHOTO TYPES AND HOW TO ASSIGN THEM:
  • Full-body shots: easiest to identify — match by color + type
  • Tag/label close-ups: look at the FABRIC visible around the tag. Match the color and texture of THAT fabric to a full-body shot. A tag on black knit fabric goes with the black knit item, NOT with a navy woven item.
  • Detail/texture shots: match the visible fabric color and weave to the closest full-body shot
  • If the SAME brand tag appears on visibly different colored fabrics, those are DIFFERENT items

CRITICAL COLOR RULES:
  • When in doubt about whether two dark items are the same color, they are DIFFERENT items. Split them.
  • Black, Navy, Charcoal, and Dark Brown are ALL different colors — never group them together.
  • If lighting makes it ambiguous, err on the side of SPLITTING into separate groups.
  • Two items of the same color but different garment types = DIFFERENT groups.

Each photo must appear in exactly one group.

Return your inventory list followed by a JSON array of groups. The JSON must be on the LAST line.
Example format:
Photo 0: Red plaid flannel shirt, full front
Photo 1: Tag close-up on red plaid fabric - matches Photo 0
Photo 2: Black puffy jacket, full front
Photo 3: Tag on black nylon fabric - matches Photo 2

[[0, 1], [2, 3]]"""
    })

    try:
        response = await _call_claude(content, max_tokens=4096)
        text = response.strip()
        # Extract JSON from the last line or code block
        json_text = text
        if "```" in text:
            json_text = text.split("```")[-2]
            if "\n" in json_text:
                json_text = json_text.split("\n", 1)[1].strip()
        else:
            # Find the last line that looks like JSON array
            for line in reversed(text.split("\n")):
                line = line.strip()
                if line.startswith("[[") or line.startswith("["):
                    json_text = line
                    break

        groups = json.loads(json_text)
        print(f"  Pass 1 result: {len(groups)} groups: {groups}")

        # Ensure all indices accounted for
        all_indices = set()
        for g in groups:
            all_indices.update(g)
        expected = set(range(len(photo_paths)))
        missing = expected - all_indices
        for idx in missing:
            groups.append([idx])

    except Exception as e:
        print(f"AI grouping pass 1 failed: {e}, falling back to individual groups")
        return [[i] for i in range(len(photo_paths))]

    # === PASS 2: Verify groups with >1 photo, split if needed ===
    # Only verify groups with 3+ photos (worth the API call)
    final_groups = []
    groups_to_verify = []
    for g in groups:
        if len(g) >= 3:
            groups_to_verify.append(g)
        else:
            final_groups.append(g)

    if not groups_to_verify:
        print(f"  Skipping pass 2: no large groups to verify")
        return groups

    print(f"  Grouping pass 2: verifying {len(groups_to_verify)} groups...")
    for group in groups_to_verify:
        if len(group) <= 2:
            final_groups.append(group)
            continue

        verify_content = []
        idx_map = {}  # local_idx -> global_idx
        for local_i, global_i in enumerate(group):
            idx_map[local_i] = global_i
            verify_content.append({"type": "text", "text": f"Photo {local_i}:"})
            verify_content.append(_encode_image(photo_paths[global_i]))

        verify_content.append({
            "type": "text",
            "text": f"""These {len(group)} photos were grouped together as the SAME clothing item. Verify this is correct.

CHECK CAREFULLY:
1. Are ALL photos the EXACT same color? (Black ≠ Navy ≠ Charcoal ≠ Dark Brown)
2. Are ALL photos the same garment type? (Don't mix jacket + shirt + pants)
3. Do ALL tag/label photos match the fabric of the main garment photos?
4. Are there photos of DIFFERENT brands mixed in?

If everything matches → return the single group: [[0, 1, 2, ...]]
If some photos don't belong → split into separate groups.

Return ONLY a JSON array of groups using the photo indices shown above (0 through {len(group)-1}).
JSON response only:"""
        })

        try:
            verify_response = await _call_claude(verify_content, max_tokens=1024)
            vtext = verify_response.strip()
            if vtext.startswith("```"):
                vtext = vtext.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            # Find JSON
            for line in reversed(vtext.split("\n")):
                line = line.strip()
                if line.startswith("["):
                    vtext = line
                    break
            sub_groups = json.loads(vtext)
            print(f"  Pass 2 verified group {group} -> {len(sub_groups)} sub-groups")

            # Map local indices back to global
            for sg in sub_groups:
                final_groups.append([idx_map[i] for i in sg if i in idx_map])

            # Check for missing indices within this group
            verified = set()
            for sg in sub_groups:
                verified.update(sg)
            for local_i in range(len(group)):
                if local_i not in verified:
                    final_groups.append([idx_map[local_i]])

        except Exception as e:
            print(f"  Pass 2 verification failed for group {group}: {e}, keeping original")
            final_groups.append(group)

    # === PASS 3: Merge orphan groups (1-2 photos) into best-matching larger group ===
    orphans = [g for g in final_groups if len(g) <= 2]
    keepers = [g for g in final_groups if len(g) > 2]

    if orphans and keepers:
        print(f"  Merging {len(orphans)} orphan groups into {len(keepers)} main groups...")
        # Build content with one representative photo per keeper + all orphan photos
        merge_content = []
        merge_content.append({"type": "text", "text": "MAIN GROUPS (one representative photo each):"})
        for gi, group in enumerate(keepers):
            merge_content.append({"type": "text", "text": f"Group {gi} (representative):"})
            merge_content.append(_encode_image(photo_paths[group[0]]))

        merge_content.append({"type": "text", "text": "\nORPHAN PHOTOS to assign to a main group:"})
        orphan_flat = []
        for g in orphans:
            for idx in g:
                orphan_flat.append(idx)
                merge_content.append({"type": "text", "text": f"Orphan photo (global index {idx}):"})
                merge_content.append(_encode_image(photo_paths[idx]))

        merge_content.append({
            "type": "text",
            "text": f"""Each orphan photo above was incorrectly separated from its group. Assign each orphan to the main group it most likely belongs to based on COLOR, GARMENT TYPE, and FABRIC.

There are {len(keepers)} main groups (Group 0 through Group {len(keepers)-1}).

Return ONLY a JSON object mapping each orphan global index to its target group number.
Example: {{"5": 0, "11": 2, "12": 1}}

JSON response only:"""
        })

        try:
            merge_response = await _call_claude(merge_content, max_tokens=1024)
            mtext = merge_response.strip()
            if mtext.startswith("```"):
                mtext = mtext.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            # Find JSON object
            for line in reversed(mtext.split("\n")):
                line = line.strip()
                if line.startswith("{"):
                    mtext = line
                    break
            assignments = json.loads(mtext)
            print(f"  Orphan assignments: {assignments}")

            for idx_str, group_num in assignments.items():
                idx = int(idx_str)
                gn = int(group_num)
                if 0 <= gn < len(keepers) and idx in orphan_flat:
                    keepers[gn].append(idx)
                    orphan_flat.remove(idx)

            # Any unassigned orphans go to the largest group as fallback
            if orphan_flat:
                largest = max(range(len(keepers)), key=lambda i: len(keepers[i]))
                for idx in orphan_flat:
                    keepers[largest].append(idx)
                print(f"  Fallback: {len(orphan_flat)} orphans merged into largest group")

            final_groups = keepers
        except Exception as e:
            print(f"  Orphan merge failed: {e}, keeping orphans as-is")
            final_groups = keepers + orphans
    elif orphans and not keepers:
        # All groups are small — just return as-is, nothing to merge into
        print(f"  All groups are small ({len(orphans)} groups), keeping as-is")
        final_groups = orphans

    print(f"  Final grouping: {len(final_groups)} groups")
    return final_groups


async def sequence_photos(photo_paths: list[str]) -> list[int]:
    """
    Given photos of a SINGLE item, return indices in optimal listing order.
    Separate AI call focused only on sequencing for better accuracy.
    """
    api_key = get_anthropic_key()
    if not api_key or len(photo_paths) <= 1:
        return list(range(len(photo_paths)))

    content = []
    for i, path in enumerate(photo_paths):
        content.append({"type": "text", "text": f"Photo {i}:"})
        content.append(_encode_image(path))

    content.append({
        "type": "text",
        "text": """These photos all show the SAME clothing item. Your job is to put them in the best order for an eBay listing.

RULES — follow strictly:
1. FIRST: The photo showing the ENTIRE item from the front. It must show the FULL garment from neckline/top to hem/bottom. This is the "hero" image a buyer sees first. If a photo cuts off part of the item, it is NOT the hero shot.
2. SECOND: Full item from back or alternate full-body angle (if available)
3. MIDDLE: Medium shots, styling details, fabric close-ups
4. LAST: Tags, brand labels, size labels, care instruction labels, and photos of any flaws/stains

The KEY rule: photos showing the COMPLETE item from edge to edge MUST come before any cropped, close-up, or detail shots.

Return ONLY a JSON array of photo indices in the correct order.
Example: [3, 1, 2, 0]

JSON response only:"""
    })

    try:
        response = await _call_claude(content)
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        order = json.loads(text)
        # Validate
        if set(order) == set(range(len(photo_paths))):
            return order
    except Exception as e:
        print(f"AI sequencing failed: {e}")

    return list(range(len(photo_paths)))


async def generate_listing(photo_paths: list[str]) -> dict:
    """Generate listing details from photos using Claude vision + market research."""
    api_key = get_anthropic_key()
    if not api_key:
        return _default_listing()

    content = []
    for path in photo_paths:
        content.append(_encode_image(path))

    content.append({
        "type": "text",
        "text": """You are an expert eBay/Poshmark resale listing creator for "Something to be Found" (somethingtobefound28).

Analyze these photos and create a complete listing. Return ONLY valid JSON:

{
  "title": "Brand Name Item Description Size Color Detail (max 80 chars, keyword-rich for eBay search)",
  "description": "Detailed HTML description. Use clean <p>, <ul>, <li> tags. Include: brand, style name if known, color, fabric/material, size, fit notes, condition details. IMPORTANT: Carefully note ANY flaws — stains, pilling, fading, holes, missing buttons, wear, alternate/outlet logos. Be honest and specific about condition. End with 'Please review all photos for the best representation of this item.'",
  "category": "Most specific eBay category name (e.g., 'Women's Dresses', 'Men's Casual Shirts')",
  "ebay_category_id": "",
  "condition": "One of: New with Tags|New without Tags|Pre-owned - Excellent|Pre-owned - Good|Pre-owned - Fair",
  "brand": "Brand name (MUST identify from labels/tags/style if visible)",
  "size": "Size (MUST identify from labels/tags if visible, e.g., 'S', 'M', '4', 'XS/S')",
  "color": "Primary color(s) (e.g., 'Black', 'Navy Blue', 'Red/White Stripe')",
  "material": "Fabric/material if visible on tags (e.g., '100% Cotton', 'Polyester Blend', 'Silk')",
  "style": "Style descriptor (e.g., 'Midi Dress', 'Button-Down Shirt', 'Moto Jacket')",
  "department": "One of: Women|Men|Girls|Boys|Unisex Adult|Baby (determine from item style, tags, and sizing — e.g., sizes S/M/L/XL with feminine cut = Women; sizes 16-18 youth = Boys)",
  "country_of_manufacture": "Country where item was made (read from tag if visible, e.g., 'China', 'Vietnam', 'USA', 'Korea'). Leave empty string if not visible on any tag.",
  "price": 0.00,
  "shipping_cost": 0.00,
  "shipping_weight_lbs": 0,
  "shipping_weight_oz": 0,
  "stock_photo_query": "Search query to find stock/product photos of this exact item (brand + item name + color)",
  "poshmark_category": "Poshmark category (e.g., 'Women > Dresses > Midi')",
  "poshmark_original_price": 0.00
}

PRICING GUIDANCE — BE CONSERVATIVE AND REALISTIC:
- This is a small resale shop selling pre-owned items, NOT a boutique
- Start with what similar USED items actually SELL for on eBay (not asking prices)
- REDUCE price significantly for: stains, pilling, fading, wear marks, missing buttons, alternate/outlet logos, non-original tags, any imperfections
- A stained or flawed item should be priced 40-60% below clean comparable items
- Mid-tier brands (Gap, Banana Republic, J.Crew): $8-20 used
- Premium brands (Patagonia, Lululemon, Theory): $15-45 used depending on condition
- Luxury brands (Gucci, Prada): $40-150+ used depending on condition
- If the item has ANY visible flaws, price at the LOW end of the range
- When in doubt, price LOWER — items that sell fast are better than items that sit

SHIPPING ESTIMATE (flat rate):
- Lightweight top/shirt: $5-6
- Dress/pants: $7-8
- Heavy jacket/coat: $9-12
- Shoes: $10-13
- Small accessory: $4-5
- Estimate conservatively to cover actual shipping costs

Fill in ALL fields. Do not leave any blank except ebay_category_id.
JSON response only:"""
    })

    try:
        system = "You are an expert clothing resale specialist with deep knowledge of fashion brands, pricing, and eBay/Poshmark best practices. You create compelling, accurate listings that sell. Every field must be filled out."
        response = await _call_claude(content, system=system)
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        listing = json.loads(text)

        # Market research for better pricing
        search_query = f"{listing.get('brand', '')} {listing.get('style', '')} {listing.get('size', '')}"
        if search_query.strip():
            market_prices = await search_ebay_sold(search_query.strip())
            if market_prices:
                prices = [p["price"] for p in market_prices]
                avg_price = sum(prices) / len(prices)
                median_price = sorted(prices)[len(prices) // 2]
                # Use median as a reference, but don't override if AI price is reasonable
                if listing.get("price", 0) == 0:
                    listing["price"] = round(median_price, 2)
                # Add market context to description
                print(f"  Market research: {len(prices)} comps, avg=${avg_price:.2f}, median=${median_price:.2f}")

        # Get eBay category suggestion — include department for accuracy
        if not listing.get("ebay_category_id"):
            dept_prefix = listing.get("department", "")
            cat_query = f"{dept_prefix} {listing.get('title', '')}".strip()
            cat = await get_ebay_category_suggestion(cat_query)
            if cat["id"]:
                listing["ebay_category_id"] = cat["id"]
                if not listing.get("category"):
                    listing["category"] = cat["name"]
                print(f"  eBay category: {cat['id']} ({cat['name']})")

        # Ensure defaults
        defaults = _default_listing()
        for key, val in defaults.items():
            if key not in listing or listing[key] is None or listing[key] == "":
                listing[key] = val

        # Ensure best_offer is on
        listing["best_offer"] = 1
        listing["format_type"] = "Buy It Now"
        listing["quantity"] = 1

        # Default shipping if not set
        if not listing.get("shipping_cost") or listing["shipping_cost"] == 0:
            listing["shipping_cost"] = 7.99
        if not listing.get("shipping_policy"):
            listing["shipping_policy"] = "Flat Rate"

        return listing
    except Exception as e:
        print(f"AI listing generation failed: {e}")
        return _default_listing()


def _default_listing():
    return {
        "title": "Draft Listing - Edit Me",
        "description": "AI generation unavailable.",
        "category": "Clothing, Shoes & Accessories",
        "ebay_category_id": "",
        "condition": "Pre-owned - Good",
        "brand": "",
        "size": "",
        "color": "",
        "material": "",
        "style": "",
        "price": 25.00,
        "shipping_cost": 7.99,
        "shipping_policy": "Flat Rate",
        "shipping_weight_lbs": 0,
        "shipping_weight_oz": 0,
        "best_offer": 1,
        "format_type": "Buy It Now",
        "quantity": 1,
        "stock_photo_query": "",
        "poshmark_category": "",
        "poshmark_original_price": 0,
    }
