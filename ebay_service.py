import base64
import json
import httpx
from config import get_ebay_config, get_ebay_tokens, save_ebay_tokens, EBAY_TOKEN_URL, EBAY_API_BASE

async def refresh_token():
    cfg = get_ebay_config()
    tokens = get_ebay_tokens()
    if not cfg or not tokens:
        raise Exception("eBay credentials not configured")
    
    creds = base64.b64encode(f"{cfg['app_id']}:{cfg['cert_id']}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            EBAY_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {creds}"
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "scope": tokens.get("scope", "https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account")
            }
        )
        resp.raise_for_status()
        new_tokens = resp.json()
        tokens["access_token"] = new_tokens["access_token"]
        if "refresh_token" in new_tokens:
            tokens["refresh_token"] = new_tokens["refresh_token"]
        save_ebay_tokens(tokens)
        return tokens["access_token"]

async def get_access_token():
    tokens = get_ebay_tokens()
    if not tokens or not tokens.get("access_token"):
        return await refresh_token()
    return tokens["access_token"]

async def _ebay_request(method, path, json_data=None, retry=True):
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"{EBAY_API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Content-Language": "en-US"
            },
            json=json_data,
            timeout=30
        )
        if resp.status_code == 401 and retry:
            await refresh_token()
            return await _ebay_request(method, path, json_data, retry=False)
        return resp

async def create_inventory_item(sku, item_data):
    """Create or replace an inventory item."""
    return await _ebay_request("PUT", f"/sell/inventory/v1/inventory_item/{sku}", item_data)

async def create_offer(offer_data):
    """Create an offer for an inventory item."""
    resp = await _ebay_request("POST", "/sell/inventory/v1/offer", offer_data)
    if resp.status_code not in (200, 201):
        raise Exception(f"Failed to create offer: {resp.text}")
    return resp.json()

async def publish_offer(offer_id):
    """Publish an offer to make it live."""
    resp = await _ebay_request("POST", f"/sell/inventory/v1/offer/{offer_id}/publish")
    if resp.status_code not in (200, 201):
        raise Exception(f"Failed to publish offer: {resp.text}")
    return resp.json()

async def publish_listing(listing, photos):
    """Full publish flow: inventory item → offer → publish."""
    import uuid
    sku = f"STBF-{listing['id']}-{uuid.uuid4().hex[:8]}"
    
    # Build item specifics from listing fields
    aspects = {}
    if listing.get("brand"): aspects["Brand"] = [listing["brand"]]
    if listing.get("size"): aspects["Size"] = [str(listing["size"])]
    if listing.get("color"): aspects["Color"] = [listing["color"]]
    if listing.get("material"):
        # Split materials like "55% Ramie, 45% Cotton" into individual materials
        mat = listing["material"]
        materials = [m.strip().split('%')[-1].strip() for m in mat.split(',') if m.strip()]
        if not materials:
            materials = [mat]
        aspects["Material"] = materials
    if listing.get("style"): aspects["Style"] = [listing["style"]]
    # Department: prefer AI-generated, fall back to category text parsing
    dept = listing.get("department", "")
    if not dept:
        cat_text = (listing.get("category") or "").lower()
        if "women" in cat_text: dept = "Women"
        elif "men" in cat_text: dept = "Men"
        elif "boy" in cat_text: dept = "Boys"
        elif "girl" in cat_text: dept = "Girls"
        else: dept = "Unisex Adult"

    # Country of manufacture from AI tag reading
    if listing.get("country_of_manufacture"):
        aspects["Country/Region of Manufacture"] = [listing["country_of_manufacture"]]

    # Standard required aspects for clothing
    aspects.setdefault("Size Type", ["Regular"])
    aspects.setdefault("Department", [dept])
    aspects.setdefault("Type", [listing.get("style") or "Regular"])

    # Build inventory item
    item_data = {
        "availability": {"shipToLocationAvailability": {"quantity": 1}},
        "condition": _map_condition(listing["condition"]),
        "product": {
            "title": listing["title"],
            "description": listing["description"],
            "imageUrls": [f"https://plato-surfacepro7.tail48e093.ts.net{p['file_path']}" for p in photos[:12]],
            "aspects": aspects,
        }
    }
    
    print(f"  eBay publish: SKU={sku}, condition={item_data['condition']}, images={len(item_data['product']['imageUrls'])}")
    print(f"  Image URLs: {item_data['product']['imageUrls'][:2]}...")
    
    resp = await create_inventory_item(sku, item_data)
    if resp.status_code not in (200, 201, 204):
        raise Exception(f"Failed to create inventory item: {resp.text}")
    
    print(f"  Inventory item created: {resp.status_code}")
    
    # Create offer
    category_id = listing.get("ebay_category_id") or "11450"
    offer_data = {
        "sku": sku,
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "listingDescription": listing["description"],
        "availableQuantity": 1,
        "categoryId": str(category_id),
        "merchantLocationKey": "stbf-home",
        "pricingSummary": {
            "price": {"value": str(listing["price"]), "currency": "USD"},
        },
        "listingPolicies": {
            "returnPolicyId": "254751264024",
            "fulfillmentPolicyId": "254751265024",
            "bestOfferTerms": {
                "bestOfferEnabled": True,
            },
        }
    }
    
    offer_resp = await create_offer(offer_data)
    offer_id = offer_resp["offerId"]
    
    # Publish
    pub_resp = await publish_offer(offer_id)
    return pub_resp.get("listingId", offer_id)

def _map_condition(condition_str):
    """Map our condition labels to eBay conditionEnum values."""
    s = (condition_str or "").lower().strip()
    mapping = {
        "new with tags": "NEW_WITH_TAGS",
        "new without tags": "NEW_WITHOUT_TAGS",
        "new": "NEW",
        "pre-owned - excellent": "USED_EXCELLENT",
        "pre-owned - good": "USED_GOOD",
        "pre-owned - fair": "USED_ACCEPTABLE",
        "pre-owned": "USED_GOOD",
    }
    for key, val in mapping.items():
        if key in s:
            return val
    return "USED_GOOD"
