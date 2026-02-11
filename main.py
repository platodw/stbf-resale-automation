import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException
from PIL import Image as PILImage
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

def make_thumbnail(src_path: Path, max_dim=400, quality=80):
    """Generate a thumbnail and return its path."""
    thumb_dir = src_path.parent / "thumbs"
    thumb_dir.mkdir(exist_ok=True)
    thumb_path = thumb_dir / src_path.name
    if not thumb_path.exists():
        img = PILImage.open(src_path)
        img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
        img.convert("RGB").save(thumb_path, "JPEG", quality=quality)
    return thumb_path
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from database import get_db, init_db
from config import UPLOAD_DIR
import ai_service
import ebay_service
import poshmark_service

app = FastAPI(title="STBF Listing Manager")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

def thumb_url(path: str) -> str:
    """Convert /uploads/3/img.jpg to /uploads/3/thumbs/img.jpg"""
    parts = path.rsplit("/", 1)
    if len(parts) == 2:
        return f"{parts[0]}/thumbs/{parts[1]}"
    return path

templates.env.filters["thumb"] = thumb_url

@app.on_event("startup")
def startup():
    init_db()

# --- Pages ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "active": "upload"})

@app.get("/dashboard")
async def dashboard(request: Request):
    db = get_db()
    
    # Count items ready for review
    items_ready = db.execute("SELECT COUNT(*) FROM listings WHERE status = 'ready_for_review'").fetchone()[0]
    
    # Count items by status
    status_counts = {}
    status_data = db.execute("SELECT status, COUNT(*) FROM listings GROUP BY status").fetchall()
    for status, count in status_data:
        status_counts[status] = count
    
    db.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "active": "dashboard",
        "items_ready": items_ready,
        "status_counts": status_counts
    })

@app.get("/groups/{batch_id}")
async def groups_page(request: Request, batch_id: int):
    db = get_db()
    batch = db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    if not batch:
        raise HTTPException(404)
    groups = db.execute("SELECT * FROM item_groups WHERE batch_id=? ORDER BY id", (batch_id,)).fetchall()
    ungrouped = db.execute("SELECT * FROM photos WHERE batch_id=? AND item_group_id IS NULL", (batch_id,)).fetchall()
    group_data = []
    for g in groups:
        photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (g["id"],)).fetchall()
        group_data.append({"group": dict(g), "photos": [dict(p) for p in photos]})
    db.close()
    return templates.TemplateResponse("groups.html", {
        "request": request, "active": "groups", "batch": dict(batch),
        "groups": group_data, "ungrouped": [dict(p) for p in ungrouped]
    })

@app.get("/review")
async def review_page(request: Request):
    db = get_db()
    listings = db.execute("""
        SELECT l.*, ig.batch_id FROM listings l 
        JOIN item_groups ig ON l.item_group_id = ig.id
        WHERE l.status IN ('drafting','ready_for_review','approved','published')
        ORDER BY l.created_at DESC
    """).fetchall()
    listing_data = []
    for l in listings:
        photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (l["item_group_id"],)).fetchall()
        listing_data.append({"listing": dict(l), "photos": [dict(p) for p in photos]})
    db.close()
    return templates.TemplateResponse("review.html", {
        "request": request, "active": "review", "listings": listing_data
    })

@app.get("/listing/{listing_id}")
async def edit_page(request: Request, listing_id: int):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not listing:
        raise HTTPException(404)
    photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (listing["item_group_id"],)).fetchall()
    # Get prev/next for navigation
    all_listings = db.execute(
        "SELECT id FROM listings WHERE status IN ('drafting','ready_for_review','approved','published') ORDER BY id"
    ).fetchall()
    ids = [r["id"] for r in all_listings]
    current_idx = ids.index(listing_id) if listing_id in ids else 0
    prev_id = ids[current_idx - 1] if current_idx > 0 else None
    next_id = ids[current_idx + 1] if current_idx < len(ids) - 1 else None
    db.close()
    return templates.TemplateResponse("edit.html", {
        "request": request, "active": "review",
        "listing": dict(listing), "photos": [dict(p) for p in photos],
        "prev_id": prev_id, "next_id": next_id,
        "listing_index": current_idx + 1, "listing_total": len(ids),
    })

@app.get("/published")
async def published_page(request: Request):
    db = get_db()
    listings = db.execute("""
        SELECT l.* FROM listings l 
        WHERE l.ebay_listing_id IS NOT NULL OR l.poshmark_listing_id IS NOT NULL
        ORDER BY l.published_at DESC
    """).fetchall()
    listing_data = []
    for l in listings:
        photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (l["item_group_id"],)).fetchall()
        listing_data.append({"listing": dict(l), "photos": [dict(p) for p in photos]})
    db.close()
    return templates.TemplateResponse("published.html", {
        "request": request, "active": "published", "listings": listing_data
    })

# --- API ---

@app.post("/api/upload")
async def upload_photos(files: list[UploadFile] = File(...)):
    db = get_db()
    db.execute("INSERT INTO batches DEFAULT VALUES")
    batch_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    batch_dir = UPLOAD_DIR / str(batch_id)
    batch_dir.mkdir(exist_ok=True)
    
    photo_paths = []
    for f in files:
        ext = Path(f.filename).suffix.lower() or ".jpg"
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = batch_dir / fname
        with open(fpath, "wb") as out:
            shutil.copyfileobj(f.file, out)
        
        # Convert HEIC/HEIF to JPEG for browser compatibility
        if ext in ('.heic', '.heif'):
            try:
                img = Image.open(fpath)
                jpeg_fname = fpath.stem + ".jpg"
                jpeg_path = batch_dir / jpeg_fname
                img.convert("RGB").save(jpeg_path, "JPEG", quality=90)
                os.remove(fpath)
                fpath = jpeg_path
                fname = jpeg_fname
            except Exception as e:
                print(f"HEIC conversion failed for {f.filename}: {e}")
        
        # Generate thumbnail
        try:
            make_thumbnail(fpath)
        except Exception as e:
            print(f"Thumbnail failed for {fname}: {e}")
        
        rel_path = f"/uploads/{batch_id}/{fname}"
        db.execute("INSERT INTO photos (batch_id, file_path) VALUES (?,?)", (batch_id, rel_path))
        photo_paths.append(str(fpath))
    
    db.commit()
    
    # AI grouping
    photos = db.execute("SELECT * FROM photos WHERE batch_id=?", (batch_id,)).fetchall()
    # Convert web paths to filesystem paths for AI
    fs_paths = [str(Path("." + p["file_path"])) for p in photos]
    groups = await ai_service.group_photos(fs_paths)
    
    for group_indices in groups:
        db.execute("INSERT INTO item_groups (batch_id, status) VALUES (?, 'grouping')", (batch_id,))
        gid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        # First assign photos to group
        for idx in group_indices:
            if idx < len(photos):
                db.execute("UPDATE photos SET item_group_id=? WHERE id=?", (gid, photos[idx]["id"]))
        
        # Then do a separate sequencing pass per group
        group_paths = [fs_paths[idx] for idx in group_indices if idx < len(photos)]
        group_photo_ids = [photos[idx]["id"] for idx in group_indices if idx < len(photos)]
        if len(group_paths) > 1:
            seq_order = await ai_service.sequence_photos(group_paths)
            for seq, order_idx in enumerate(seq_order):
                if order_idx < len(group_photo_ids):
                    db.execute("UPDATE photos SET sequence=? WHERE id=?", (seq, group_photo_ids[order_idx]))
        else:
            for seq, pid in enumerate(group_photo_ids):
                db.execute("UPDATE photos SET sequence=? WHERE id=?", (seq, pid))
    
    db.execute("UPDATE batches SET status='grouping' WHERE id=?", (batch_id,))
    db.commit()
    db.close()
    return JSONResponse({"batch_id": batch_id, "redirect": f"/groups/{batch_id}"})

@app.post("/api/groups/{batch_id}/move-photo")
async def move_photo(batch_id: int, photo_id: int = Form(...), target_group_id: int = Form(...), position: int = Form(0)):
    db = get_db()
    # Move photo to target group
    db.execute("UPDATE photos SET item_group_id=? WHERE id=? AND batch_id=?", (target_group_id, photo_id, batch_id))
    # Re-sequence all photos in the target group
    photos = db.execute("SELECT id FROM photos WHERE item_group_id=? AND id!=? ORDER BY sequence, id", (target_group_id, photo_id)).fetchall()
    seq = 0
    for i, p in enumerate(photos):
        if i == position:
            db.execute("UPDATE photos SET sequence=? WHERE id=?", (seq, photo_id))
            seq += 1
        db.execute("UPDATE photos SET sequence=? WHERE id=?", (seq, p["id"]))
        seq += 1
    if position >= len(photos):
        db.execute("UPDATE photos SET sequence=? WHERE id=?", (seq, photo_id))
    db.commit()
    db.close()
    return JSONResponse({"ok": True})

@app.post("/api/groups/{batch_id}/new-group")
async def new_group(batch_id: int):
    db = get_db()
    db.execute("INSERT INTO item_groups (batch_id, status) VALUES (?, 'grouping')", (batch_id,))
    gid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return JSONResponse({"group_id": gid})

@app.post("/api/groups/{batch_id}/confirm")
async def confirm_groups(batch_id: int):
    """Confirm groupings and generate draft listings with market research + stock photos."""
    db = get_db()
    groups = db.execute("SELECT * FROM item_groups WHERE batch_id=?", (batch_id,)).fetchall()
    
    for g in groups:
        photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (g["id"],)).fetchall()
        if not photos:
            continue
        fs_paths = [str(Path("." + p["file_path"])) for p in photos]
        draft = await ai_service.generate_listing(fs_paths)
        
        # Search for stock photos
        stock_query = draft.get("stock_photo_query", "")
        if stock_query:
            try:
                stock_results = await ai_service.search_stock_photos(stock_query)
                batch_dir = UPLOAD_DIR / str(batch_id)
                batch_dir.mkdir(exist_ok=True)
                for i, stock in enumerate(stock_results[:2]):  # Max 2 stock photos
                    fname = f"stock_{g['id']}_{i}.jpg"
                    saved = await ai_service.download_stock_photo(stock["url"], batch_dir, fname)
                    if saved:
                        rel_path = f"/uploads/{batch_id}/{fname}"
                        # Stock photos go FIRST — shift existing photos down
                        db.execute("UPDATE photos SET sequence = sequence + 1 WHERE item_group_id=?", (g["id"],))
                        db.execute(
                            "INSERT INTO photos (batch_id, item_group_id, file_path, sequence, is_stock) VALUES (?,?,?,?,1)",
                            (batch_id, g["id"], rel_path, i)
                        )
                        print(f"  Added stock photo: {fname}")
            except Exception as e:
                print(f"  Stock photo search failed: {e}")
        
        # Build the full insert with all fields
        fields = {
            "item_group_id": g["id"],
            "title": draft.get("title", ""),
            "description": draft.get("description", ""),
            "category": draft.get("category", ""),
            "ebay_category_id": draft.get("ebay_category_id", ""),
            "condition": draft.get("condition", ""),
            "price": draft.get("price", 25.0),
            "brand": draft.get("brand", ""),
            "size": draft.get("size", ""),
            "color": draft.get("color", ""),
            "material": draft.get("material", ""),
            "style": draft.get("style", ""),
            "format_type": draft.get("format_type", "Buy It Now"),
            "best_offer": draft.get("best_offer", 1),
            "quantity": draft.get("quantity", 1),
            "shipping_policy": draft.get("shipping_policy", "Flat Rate"),
            "shipping_cost": draft.get("shipping_cost", 7.99),
            "shipping_weight_lbs": draft.get("shipping_weight_lbs", 0),
            "shipping_weight_oz": draft.get("shipping_weight_oz", 0),
            "return_policy": "30 Day Returns",
            "poshmark_category": draft.get("poshmark_category", ""),
            "poshmark_original_price": draft.get("poshmark_original_price", 0),
            "status": "ready_for_review",
        }
        cols = ", ".join(fields.keys())
        placeholders = ", ".join(["?"] * len(fields))
        db.execute(f"INSERT INTO listings ({cols}) VALUES ({placeholders})", list(fields.values()))
        db.execute("UPDATE item_groups SET status='drafting' WHERE id=?", (g["id"],))
    
    db.execute("UPDATE batches SET status='drafting' WHERE id=?", (batch_id,))
    db.commit()
    db.close()
    return JSONResponse({"redirect": "/review"})

@app.post("/api/listing/{listing_id}/save")
async def save_listing(listing_id: int, request: Request):
    form = await request.form()
    db = get_db()
    fields = {
        "title": str, "description": str, "category": str, "condition": str,
        "price": float, "brand": str, "size": str, "color": str, "material": str,
        "style": str, "format_type": str, "quantity": int, "sku": str, "upc": str,
        "shipping_weight_lbs": float, "shipping_weight_oz": float,
        "package_length": float, "package_width": float, "package_height": float,
        "shipping_policy": str, "shipping_cost": float, "return_policy": str,
        "ebay_category_id": str, "best_offer": int,
        "poshmark_category": str, "poshmark_subcategory": str,
        "poshmark_size": str, "poshmark_brand": str, "poshmark_original_price": float,
    }
    sets = []
    vals = []
    for field, typ in fields.items():
        if field in form:
            try:
                vals.append(typ(form[field]))
                sets.append(f"{field}=?")
            except (ValueError, TypeError):
                pass
    if sets:
        vals.append(listing_id)
        db.execute(f"UPDATE listings SET {', '.join(sets)} WHERE id=?", vals)
        db.commit()
    db.close()
    return JSONResponse({"ok": True})

@app.post("/api/listing/{listing_id}/approve")
async def approve_listing(listing_id: int):
    db = get_db()
    db.execute("UPDATE listings SET status='approved' WHERE id=?", (listing_id,))
    db.commit()
    db.close()
    return JSONResponse({"ok": True})

@app.post("/api/listing/{listing_id}/publish")
async def publish_listing(listing_id: int):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not listing:
        raise HTTPException(404)
    photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (listing["item_group_id"],)).fetchall()
    
    try:
        ebay_id = await ebay_service.publish_listing(dict(listing), [dict(p) for p in photos])
        db.execute("UPDATE listings SET status='published', ebay_listing_id=?, published_at=CURRENT_TIMESTAMP WHERE id=?",
                   (ebay_id, listing_id))
        db.commit()
        db.close()
        return JSONResponse({"ok": True, "ebay_listing_id": ebay_id})
    except Exception as e:
        db.close()
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/listing/{listing_id}/publish-poshmark")
async def publish_listing_poshmark(listing_id: int):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not listing:
        raise HTTPException(404)
    photos = db.execute("SELECT * FROM photos WHERE item_group_id=? ORDER BY sequence, id", (listing["item_group_id"],)).fetchall()

    try:
        result = await poshmark_service.publish_listing(dict(listing), [dict(p) for p in photos])
        if result.get("success"):
            if result.get("draft"):
                # Semi-automated: draft started, Katie finishes manually
                db.execute("UPDATE listings SET poshmark_listing_id=? WHERE id=?", ("draft", listing_id))
                db.commit()
                db.close()
                return JSONResponse({
                    "ok": True,
                    "draft": True,
                    "message": result.get("message", "Draft started on Poshmark"),
                    "remaining_fields": result.get("remaining_fields", {}),
                })
            posh_id = result.get("listing_id", "")
            posh_url = result.get("url", "")
            db.execute("UPDATE listings SET poshmark_listing_id=? WHERE id=?", (posh_id, listing_id))
            db.commit()
            db.close()
            return JSONResponse({"ok": True, "poshmark_listing_id": posh_id, "poshmark_url": posh_url})
        else:
            db.close()
            return JSONResponse({"error": result.get("error", "Unknown error")}, status_code=500)
    except Exception as e:
        db.close()
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/photo/{photo_id}/move")
async def move_photo_order(photo_id: int, request: Request):
    body = await request.json()
    direction = body.get("direction", "right")
    db = get_db()
    photo = db.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not photo:
        db.close()
        raise HTTPException(404)
    group_id = photo["item_group_id"]
    photos = db.execute("SELECT id, sequence FROM photos WHERE item_group_id=? ORDER BY sequence, id", (group_id,)).fetchall()
    ids = [p["id"] for p in photos]
    idx = ids.index(photo_id) if photo_id in ids else -1
    if idx < 0:
        db.close()
        return JSONResponse({"ok": False})
    swap_idx = idx - 1 if direction == "left" else idx + 1
    if 0 <= swap_idx < len(ids):
        # Swap sequences
        db.execute("UPDATE photos SET sequence=? WHERE id=?", (swap_idx, ids[idx]))
        db.execute("UPDATE photos SET sequence=? WHERE id=?", (idx, ids[swap_idx]))
        db.commit()
    db.close()
    return JSONResponse({"ok": True})

@app.delete("/api/photo/{photo_id}")
async def delete_photo(photo_id: int):
    db = get_db()
    photo = db.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if photo:
        # Delete file and thumbnail
        file_path = Path("." + photo["file_path"])
        if file_path.exists():
            file_path.unlink()
        thumb_path = file_path.parent / "thumbs" / file_path.name
        if thumb_path.exists():
            thumb_path.unlink()
        db.execute("DELETE FROM photos WHERE id=?", (photo_id,))
        db.commit()
    db.close()
    return JSONResponse({"ok": True})

@app.delete("/api/listing/{listing_id}")
async def delete_listing(listing_id: int):
    db = get_db()
    db.execute("DELETE FROM listings WHERE id=?", (listing_id,))
    db.commit()
    db.close()
    return JSONResponse({"ok": True})

@app.get("/api/financial-data")
async def get_financial_data():
    """Get financial data from Monarch Money"""
    try:
        import monarch_service
        data = await monarch_service.get_stbf_financial_data()
        return JSONResponse(data)
    except Exception as e:
        print(f"Error fetching financial data: {e}")
        return JSONResponse({
            "week": {"ebay": 0, "poshmark": 0, "shipping": 0},
            "month": {"ebay": 0, "poshmark": 0, "shipping": 0},
            "ytd": {
                "current": {"ebay": 0, "poshmark": 0, "shipping": 0},
                "prior": {"ebay": 0, "poshmark": 0, "shipping": 0}
            }
        })
