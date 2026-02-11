"""
Poshmark Service - Browser automation for listing creation via Playwright.
"""
import json
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/poshmark/config.json"
BROWSER_STATE_PATH = Path.home() / ".openclaw/credentials/poshmark/browser_state.json"

POSH_CATEGORY_MAP = {
    "women's dresses": ("Women", "Dresses"),
    "women's sweaters": ("Women", "Sweaters"),
    "women's tops": ("Women", "Tops"),
    "women's jackets": ("Women", "Jackets & Coats"),
    "women's jeans": ("Women", "Jeans"),
    "women's pants": ("Women", "Pants & Jumpsuits"),
    "women's shorts": ("Women", "Shorts"),
    "women's skirts": ("Women", "Skirts"),
    "women's shoes": ("Women", "Shoes"),
    "women's bags": ("Women", "Bags"),
    "women's jewelry": ("Women", "Jewelry"),
    "women's accessories": ("Women", "Accessories"),
    "women's swim": ("Women", "Swim"),
    "men's shirts": ("Men", "Shirts"),
    "men's sweaters": ("Men", "Sweaters"),
    "men's jackets": ("Men", "Jackets & Coats"),
    "men's jeans": ("Men", "Jeans"),
    "men's pants": ("Men", "Pants"),
    "men's shoes": ("Men", "Shoes"),
    "men's accessories": ("Men", "Accessories"),
    "boys": ("Kids", "Boys"),
    "girls": ("Kids", "Girls"),
}

POSH_CONDITION_MAP = {
    "new with tags": "NWT",
    "new without tags": "NWOT",
    "pre-owned - excellent": "Good",
    "pre-owned - good": "Good",
    "pre-owned - fair": "Fair",
}

POSH_COLOR_MAP = {
    "black": "Black", "white": "White", "blue": "Blue", "navy": "Blue",
    "red": "Red", "pink": "Pink", "green": "Green", "yellow": "Yellow",
    "orange": "Orange", "purple": "Purple", "brown": "Brown", "tan": "Tan",
    "cream": "Cream", "gray": "Gray", "grey": "Gray", "gold": "Gold",
    "silver": "Silver",
}


def _resolve_photo_path(file_path: str) -> str:
    if file_path.startswith("/uploads/"):
        return str(Path(__file__).parent / file_path.lstrip("/"))
    return file_path


def _map_category(listing: dict) -> tuple[str, str]:
    posh_cat = listing.get("poshmark_category", "")
    if ">" in posh_cat:
        parts = [p.strip() for p in posh_cat.split(">")]
        return (parts[0], parts[1] if len(parts) > 1 else "")
    cat = (listing.get("category") or "").lower()
    for key, val in POSH_CATEGORY_MAP.items():
        if key in cat:
            return val
    dept = (listing.get("department") or "Women").strip()
    if dept in ("Women", "Men", "Kids"):
        return (dept, "")
    return ("Women", "")


def _strip_html(html: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'</li>', '\n', text)
    text = re.sub(r'<li>', '• ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def _get_browser_context(playwright):
    browser = await playwright.chromium.launch(headless=True)
    if BROWSER_STATE_PATH.exists():
        context = await browser.new_context(storage_state=str(BROWSER_STATE_PATH))
    else:
        context = await browser.new_context()
    return browser, context


async def _ensure_logged_in(page) -> bool:
    await page.goto("https://poshmark.com/closet")
    await page.wait_for_load_state("networkidle", timeout=15000)
    return "/login" not in page.url


async def _save_state(context):
    await context.storage_state(path=str(BROWSER_STATE_PATH))


async def _safe_click_dropdown(page, dd_index: int, option_selector: str, label: str):
    """Safely click a Poshmark dropdown option. Returns True if successful."""
    try:
        dd = page.locator('.dropdown__selector').nth(dd_index)
        await dd.click()
        await asyncio.sleep(1)
        option = page.locator(option_selector).first
        if await option.count() > 0 and await option.is_visible():
            await option.click()
            await asyncio.sleep(0.5)
            print(f"  Poshmark: {label} ✓")
            return True
        else:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            print(f"  Poshmark: {label} — not found, skipped")
            return False
    except Exception as e:
        print(f"  Poshmark: {label} — error: {e}")
        try:
            await page.keyboard.press("Escape")
        except:
            pass
        return False


async def publish_listing(listing: dict, photos: list[dict]) -> dict:
    """
    Semi-automated Poshmark listing: uploads photos, fills title/description/brand/price,
    then returns a draft URL for Katie to finish (category, size, condition, color) manually.
    Vue.js custom dropdowns resist all automation approaches.
    """
    async with async_playwright() as pw:
        browser, context = await _get_browser_context(pw)
        page = await context.new_page()
        page.set_default_timeout(8000)

        try:
            if not await _ensure_logged_in(page):
                await browser.close()
                return {"success": False, "error": "Not logged into Poshmark. Session expired."}

            print("  Poshmark: Logged in, navigating to listing form...")
            await page.goto("https://poshmark.com/create-listing")
            await page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(2)

            # === 1. PHOTOS ===
            real_photos = [p for p in photos if not p.get("is_stock")][:16]
            if not real_photos:
                real_photos = photos[:16]

            photo_paths = []
            for p in real_photos:
                abs_path = _resolve_photo_path(p["file_path"])
                if Path(abs_path).exists():
                    photo_paths.append(abs_path)

            if not photo_paths:
                await browser.close()
                return {"success": False, "error": "No valid photo files found"}

            file_input = page.locator('input[type="file"][name="img-file-input"]').first
            print(f"  Poshmark: Uploading {len(photo_paths)} photos...")
            await file_input.set_input_files(photo_paths)
            await asyncio.sleep(3)

            # Dismiss covershot modal
            for _ in range(10):
                apply_btn = page.locator('button:has-text("Apply")')
                if await apply_btn.count() > 0 and await apply_btn.first.is_visible():
                    print("  Poshmark: Dismissing covershot modal...")
                    await apply_btn.first.click()
                    await asyncio.sleep(2)
                    break
                await asyncio.sleep(0.5)

            # === 2. TITLE ===
            title_input = page.locator('input[data-vv-name="title"]').first
            await title_input.fill(listing.get("title", "")[:80])
            print(f"  Poshmark: Title filled")

            # === 3. DESCRIPTION ===
            desc_input = page.locator('textarea[data-vv-name="description"]').first
            await desc_input.fill(_strip_html(listing.get("description", ""))[:1500])
            print("  Poshmark: Description filled")

            # === 4. BRAND (text input, not a Vue dropdown) ===
            brand = listing.get("brand", "")
            if brand:
                try:
                    brand_input = page.locator('input[placeholder*="Brand"]').first
                    await brand_input.click()
                    await brand_input.fill(brand)
                    await asyncio.sleep(2)
                    suggestion = page.locator('.dropdown__menu a.dropdown__menu__item').first
                    if await suggestion.count() > 0 and await suggestion.is_visible():
                        await suggestion.click()
                        print(f"  Poshmark: Brand: {brand} ✓")
                    else:
                        await brand_input.press("Enter")
                        print(f"  Poshmark: Brand: {brand} (typed)")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"  Poshmark: Brand failed: {e}")

            # === 5. ORIGINAL PRICE ===
            try:
                orig_price_input = page.locator('input[data-vv-name="originalPrice"]').first
                if await orig_price_input.count() > 0 and await orig_price_input.is_visible():
                    op = listing.get("poshmark_original_price") or int(float(listing.get("price", 25)) * 3)
                    await orig_price_input.fill(str(int(op)))
                    print(f"  Poshmark: Original price: ${int(op)}")
            except:
                pass

            # === 6. LISTING PRICE ===
            try:
                price_input = page.locator('input[data-vv-name="listingPrice"]').first
                if await price_input.count() > 0 and await price_input.is_visible():
                    await price_input.fill(str(int(float(listing.get("price", 25)))))
                    print(f"  Poshmark: Price: ${listing.get('price')}")
            except:
                pass

            # Skip Vue dropdowns (category, subcategory, size, condition, color)
            # — they resist all automation. Katie will finish these manually.
            top_cat, sub_cat = _map_category(listing)
            condition = listing.get("condition", "")
            posh_cond = "Good"
            for key, val in POSH_CONDITION_MAP.items():
                if key in condition.lower():
                    posh_cond = val
                    break
            color = (listing.get("color") or "").split(",")[0].split("/")[0].strip()
            size = listing.get("size", "")

            print(f"  Poshmark: Draft ready — Katie needs to set: Category={top_cat}>{sub_cat}, Size={size}, Condition={posh_cond}, Color={color}")

            await page.screenshot(path="/tmp/posh_draft.png")
            await _save_state(context)
            await browser.close()

            return {
                "success": True,
                "draft": True,
                "url": "https://poshmark.com/create-listing",
                "message": f"Draft started on Poshmark! Photos, title, description, brand, and price are filled in. Katie needs to finish: Category ({top_cat} > {sub_cat}), Size ({size}), Condition ({posh_cond}), and Color ({color}).",
                "remaining_fields": {
                    "category": top_cat,
                    "subcategory": sub_cat,
                    "size": size,
                    "condition": posh_cond,
                    "color": color,
                }
            }

        except Exception as e:
            print(f"  Poshmark error: {e}")
            try:
                await page.screenshot(path="/tmp/posh_error.png")
                await _save_state(context)
            except:
                pass
            await browser.close()
            return {"success": False, "error": str(e)}


async def check_session() -> bool:
    try:
        async with async_playwright() as pw:
            browser, context = await _get_browser_context(pw)
            page = await context.new_page()
            logged_in = await _ensure_logged_in(page)
            await _save_state(context)
            await browser.close()
            return logged_in
    except:
        return False
