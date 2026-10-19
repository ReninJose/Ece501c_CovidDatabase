import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "covid.db"
DDL_PATH = DB_DIR / "DDL.sql"


def get_connection(db_path=DB_PATH):
    return sqlite3.connect(db_path)


def get_cursor(db_path=DB_PATH):
    # Commit/close through the cursor's connection: cursor.connection.commit()
    return get_connection(db_path).cursor()


def init():
    with get_connection() as conn:
        # Construct table
        conn.executescript(DDL_PATH.read_text())
        conn.commit()

