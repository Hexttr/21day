"""SQLite DB для админки: рефералы и оплаты."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "admin.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Создаёт таблицы referrals и payments."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inv_id INTEGER UNIQUE NOT NULL,
                ref_code TEXT,
                email TEXT,
                name TEXT,
                phone TEXT,
                plan TEXT,
                out_sum REAL,
                paid_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (ref_code) REFERENCES referrals(code)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_ref ON payments(ref_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_inv ON payments(inv_id)")


def add_referral(code: str) -> bool:
    """Добавляет реферальный код. Возвращает False если уже есть."""
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO referrals (code) VALUES (?)", (code.strip().lower(),))
        return True
    except sqlite3.IntegrityError:
        return False


def delete_referral(code: str) -> bool:
    """Удаляет реферальный код."""
    with get_db() as conn:
        cur = conn.execute("DELETE FROM referrals WHERE code = ?", (code.strip().lower(),))
        return cur.rowcount > 0


def list_referrals():
    """Список всех реферальных кодов с количеством оплат."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.id, r.code, r.created_at,
                   (SELECT COUNT(*) FROM payments p WHERE p.ref_code = r.code) as payments_count
            FROM referrals r
            ORDER BY r.created_at DESC
        """).fetchall()
        return [dict(row) for row in rows]


def referral_exists(code: str) -> bool:
    """Проверяет, существует ли реферальный код."""
    if not code:
        return False
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM referrals WHERE code = ?", (code.strip().lower(),)).fetchone()
        return row is not None


def add_payment(inv_id: int, email: str, name: str, phone: str, plan: str, out_sum: float, ref_code: str = None):
    """Сохраняет оплату (вызывается из robokassa_result)."""
    with get_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO payments (inv_id, ref_code, email, name, phone, plan, out_sum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (inv_id, (ref_code or "").strip().lower() or None, email or "", name or "", phone or "", plan or "", float(out_sum or 0)))


def list_payments():
    """Список оплат с отметкой реферала."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT inv_id, ref_code, email, name, phone, plan, out_sum, paid_at
            FROM payments
            ORDER BY paid_at DESC
        """).fetchall()
        return [dict(row) for row in rows]
