import sqlite3
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'uploaded'
        );
        CREATE TABLE IF NOT EXISTS item_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL REFERENCES batches(id),
            status TEXT DEFAULT 'grouping',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL REFERENCES batches(id),
            item_group_id INTEGER REFERENCES item_groups(id),
            file_path TEXT NOT NULL,
            gdrive_id TEXT,
            sequence INTEGER DEFAULT 0,
            is_stock INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_group_id INTEGER NOT NULL REFERENCES item_groups(id),
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            ebay_category_id TEXT DEFAULT '',
            condition TEXT DEFAULT '',
            price REAL DEFAULT 0,
            brand TEXT DEFAULT '',
            size TEXT DEFAULT '',
            color TEXT DEFAULT '',
            material TEXT DEFAULT '',
            style TEXT DEFAULT '',
            format_type TEXT DEFAULT 'Buy It Now',
            quantity INTEGER DEFAULT 1,
            sku TEXT DEFAULT '',
            upc TEXT DEFAULT '',
            item_specifics TEXT DEFAULT '{}',
            shipping_weight_lbs REAL DEFAULT 0,
            shipping_weight_oz REAL DEFAULT 0,
            package_length REAL DEFAULT 0,
            package_width REAL DEFAULT 0,
            package_height REAL DEFAULT 0,
            shipping_policy TEXT DEFAULT 'Flat Rate',
            shipping_cost REAL DEFAULT 0,
            return_policy TEXT DEFAULT '30 Day Returns',
            best_offer INTEGER DEFAULT 1,
            poshmark_category TEXT DEFAULT '',
            poshmark_subcategory TEXT DEFAULT '',
            poshmark_size TEXT DEFAULT '',
            poshmark_brand TEXT DEFAULT '',
            poshmark_original_price REAL DEFAULT 0,
            ebay_listing_id TEXT,
            poshmark_listing_id TEXT,
            status TEXT DEFAULT 'drafting',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
