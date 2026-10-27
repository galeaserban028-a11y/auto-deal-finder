"""
Database Layer (SQLite)
Stocheaza anunturile, calculele de profit si istoricul alertelor Telegram.
Garanteaza ca nu primesti acelasi anunt de doua ori, dar re-evalueaza un anunt
deja vazut daca vanzatorul i-a scazut pretul (scaderile de pret sunt o sursa majora de ponturi).
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from config.settings import DATABASE_PATH

# Un anunt deja vazut este re-evaluat doar daca pretul a scazut cu cel putin 3%
PRICE_DROP_REEVALUATE_PCT = 3.0


def get_connection():
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _column_names(cursor, table: str) -> List[str]:
    return [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT UNIQUE,
        source TEXT,
        title TEXT,
        url TEXT,
        price_eur REAL,
        make TEXT,
        model TEXT,
        year INTEGER,
        mileage INTEGER,
        fuel TEXT,
        transmission TEXT,
        city TEXT,
        seller_type TEXT,
        seller_phone TEXT,
        photo_url TEXT,
        is_safe INTEGER,
        safety_reason TEXT,
        created_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER UNIQUE,
        median_price REAL,
        floor_price REAL,
        discount_pct REAL,
        net_profit REAL,
        deal_rating TEXT,
        alerted_telegram INTEGER DEFAULT 0,
        alerted_at TEXT,
        created_at TEXT,
        FOREIGN KEY (listing_id) REFERENCES listings(id)
    );
    """)

    # Migrari pentru baze de date create de versiunile vechi
    if "updated_at" not in _column_names(cursor, "listings"):
        cursor.execute("ALTER TABLE listings ADD COLUMN updated_at TEXT")
    # details_json pastreaza raportul AI, generatia, nr. de comparabile etc. pentru alerta Telegram
    # (inainte se pierdeau, iar alerta afisa valori inventate: "Scor AI 85/100", "0 masini active").
    if "details_json" not in _column_names(cursor, "deals"):
        cursor.execute("ALTER TABLE deals ADD COLUMN details_json TEXT")

    # Curatare date corupte de versiunile vechi (idempotent):
    # - anunturi Publi24 salvate cu pret gresit (ex. 10 € in loc de 10.500 €) din cauza bug-ului de parsare;
    #   le stergem ca sa fie re-evaluate corect la urmatoarea scanare
    # - inregistrari scrise de teste in baza reala
    cursor.execute("""
        DELETE FROM listings
        WHERE source = 'UnitTest'
           OR (price_eur < 100 AND id NOT IN (SELECT listing_id FROM deals WHERE alerted_telegram = 1))
    """)
    cursor.execute("DELETE FROM deals WHERE listing_id NOT IN (SELECT id FROM listings)")

    # Performance & Concurrency Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_alerted ON deals(alerted_telegram);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_listing_id ON deals(listing_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_make_model ON listings(make, model);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_created_at ON listings(created_at);")

    conn.commit()
    conn.close()


def is_already_seen(external_id: str) -> bool:
    """Verifica daca un anunt a fost deja procesat."""
    return get_seen_price(external_id) is not None


def get_seen_price(external_id: str) -> Optional[float]:
    """Pretul cu care a fost vazut ultima data anuntul, sau None daca e nou."""
    if not external_id:
        return None
    conn = get_connection()
    try:
        row = conn.execute("SELECT price_eur FROM listings WHERE external_id = ?", (str(external_id),)).fetchone()
        return float(row["price_eur"] or 0) if row else None
    finally:
        conn.close()


def should_skip_seen(external_id: str, current_price: float) -> bool:
    """
    True daca anuntul a fost deja procesat si pretul NU a scazut semnificativ.
    False pentru anunturi noi sau pentru cele cu pretul scazut (care merita re-evaluate).
    """
    seen_price = get_seen_price(external_id)
    if seen_price is None:
        return False
    try:
        current_price = float(current_price or 0)
    except (TypeError, ValueError):
        return True
    if seen_price > 0 and 0 < current_price <= seen_price * (1 - PRICE_DROP_REEVALUATE_PCT / 100):
        return False
    return True


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def save_listing_and_deal(listing: Dict, deal_eval: Dict) -> Optional[int]:
    """
    Salveaza (sau actualizeaza) anuntul si evaluarea sa de profit.
    Returneaza ID-ul deal-ului daca este un pont NOU (netrimis inca), altfel None.
    """
    external_id = str(listing.get("external_id") or "")
    if not external_id:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    try:
        cursor.execute("""
        INSERT INTO listings (
            external_id, source, title, url, price_eur, make, model, year,
            mileage, fuel, transmission, city, seller_type, seller_phone, photo_url,
            is_safe, safety_reason, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
            price_eur = excluded.price_eur,
            title = excluded.title,
            is_safe = excluded.is_safe,
            safety_reason = excluded.safety_reason,
            updated_at = excluded.updated_at
        """, (
            external_id,
            listing.get("source", "unknown"),
            listing.get("title", ""),
            listing.get("url", ""),
            _safe_float(listing.get("price_eur")),
            listing.get("make", ""),
            listing.get("model", ""),
            _safe_int(listing.get("year")),
            _safe_int(listing.get("mileage")),
            listing.get("fuel", ""),
            listing.get("transmission", ""),
            listing.get("city", ""),
            listing.get("seller_type", "private"),
            listing.get("seller_phone", ""),
            listing.get("photo_url", ""),
            1 if listing.get("is_safe", True) else 0,
            listing.get("safety_reason", ""),
            now_str,
            now_str,
        ))

        listing_row = cursor.execute("SELECT id FROM listings WHERE external_id = ?", (external_id,)).fetchone()
        if not listing_row:
            conn.commit()
            return None
        listing_id = listing_row["id"]

        deal_id = None
        if deal_eval.get("is_deal"):
            details = deal_eval.get("details") or {}
            existing = cursor.execute("SELECT id, alerted_telegram FROM deals WHERE listing_id = ?", (listing_id,)).fetchone()
            values = (
                _safe_float(deal_eval.get("median_price")),
                _safe_float(deal_eval.get("floor_price")),
                _safe_float(deal_eval.get("discount_pct")),
                _safe_float(deal_eval.get("net_profit")),
                deal_eval.get("deal_rating", "STANDARD"),
                json.dumps(details, ensure_ascii=False, default=str),
            )
            if existing is None:
                cursor.execute("""
                INSERT INTO deals (
                    median_price, floor_price, discount_pct, net_profit,
                    deal_rating, details_json, listing_id, alerted_telegram, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, values + (listing_id, now_str))
                deal_id = cursor.lastrowid
            else:
                # Pont deja cunoscut (ex: a scazut si mai mult pretul): actualizam cifrele.
                # Re-alertam doar daca nu a fost inca trimis.
                cursor.execute("""
                UPDATE deals SET median_price = ?, floor_price = ?, discount_pct = ?, net_profit = ?,
                    deal_rating = ?, details_json = ?
                WHERE listing_id = ?
                """, values + (listing_id,))
                if not existing["alerted_telegram"]:
                    deal_id = existing["id"]

        conn.commit()
        return deal_id

    except Exception as e:
        conn.rollback()
        print(f"[DB Error] {e}")
        return None
    finally:
        conn.close()


def mark_as_alerted(deal_id: int):
    """Marcheaza deal-ul ca trimis pe Telegram."""
    conn = get_connection()
    try:
        conn.execute("""
        UPDATE deals
        SET alerted_telegram = 1, alerted_at = ?
        WHERE id = ?
        """, (datetime.now().isoformat(), deal_id))
        conn.commit()
    finally:
        conn.close()


_DEAL_SELECT = """
    SELECT
        d.id as deal_id, d.median_price, d.floor_price, d.discount_pct, d.net_profit, d.deal_rating,
        d.alerted_telegram, d.created_at, d.details_json,
        l.external_id, l.source, l.title, l.url, l.price_eur, l.make, l.model, l.year,
        l.mileage, l.fuel, l.transmission, l.city, l.seller_type, l.seller_phone, l.photo_url
    FROM deals d
    JOIN listings l ON d.listing_id = l.id
"""


def _row_to_deal(row) -> Dict:
    deal = dict(row)
    raw = deal.pop("details_json", None)
    if raw:
        try:
            details = json.loads(raw)
            if isinstance(details, dict):
                # Detaliile (raport AI, generatie...) nu suprascriu coloanele de baza
                for k, v in details.items():
                    deal.setdefault(k, v)
        except (TypeError, ValueError):
            pass
    return deal


def get_unalerted_deals() -> List[Dict]:
    """Returneaza ponturile care nu au fost inca trimise pe Telegram."""
    conn = get_connection()
    try:
        rows = conn.execute(_DEAL_SELECT + " WHERE d.alerted_telegram = 0 ORDER BY d.net_profit DESC").fetchall()
        return [_row_to_deal(r) for r in rows]
    finally:
        conn.close()


def get_all_deals(limit: int = 50) -> List[Dict]:
    """Returneaza toate ponturile pentru afisare in Dashboard."""
    conn = get_connection()
    try:
        rows = conn.execute(_DEAL_SELECT + " ORDER BY d.created_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [_row_to_deal(r) for r in rows]
    finally:
        conn.close()


def checkpoint():
    """Scrie WAL-ul in fisierul principal .db (necesar inainte de commit-ul bazei in GitHub Actions)."""
    conn = get_connection()
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    finally:
        conn.close()


# Initialize database automatically
init_db()
