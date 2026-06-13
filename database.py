import os
import sqlite3
from pathlib import Path


def database_path():
    return os.getenv("DATABASE_URL", "voters.db")


def get_connection():
    db_path = database_path()
    parent = Path(db_path).expanduser().parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Use CREATE TABLE IF NOT EXISTS to prevent data loss on restart
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            voter_id TEXT PRIMARY KEY,
            name TEXT,
            fathers_name TEXT,
            house_number TEXT,
            age INTEGER,
            gender TEXT,
            photo_status TEXT
        )
    """)

    # Add indexes for faster searches
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_voter_id ON voters(voter_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON voters(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fathers_name ON voters(fathers_name)")

    conn.commit()
    conn.close()

def search_voters_by_name_prefix(name_prefix):
    """
    Returns a subset of voters whose name starts with or contains the prefix
    to limit the pool for fuzzy matching.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Basic SQL filtering to reduce candidate pool
    search_term = f"%{name_prefix}%"
    cursor.execute("SELECT * FROM voters WHERE name LIKE ? LIMIT 100", (search_term,))
    rows = cursor.fetchall()
    conn.close()
    return rows
