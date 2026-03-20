import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_url TEXT,
            page_url TEXT,
            issue_type TEXT,
            issue_detail TEXT,
            fixed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS published_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_url TEXT,
            wp_post_id INTEGER,
            title TEXT,
            keyword TEXT,
            url TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS backlink_outreach (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_url TEXT,
            target_url TEXT,
            contact_email TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP,
            replied_at TIMESTAMP,
            linked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_url TEXT,
            keyword TEXT,
            page_url TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            recorded_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
