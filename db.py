"""SQLite adapter for the data_import_*.py ETL scripts.

Phase 1 of the public-demo build: the scripts no longer need a hosted MySQL
instance and now write to a local SQLite file. player_crud.py and
07_mlb_assistant_app.py still talk to MySQL directly until they migrate too.
"""
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "mlb_scouting.db"),
)


def create_db_connection():
    """Creates a connection to the local SQLite database.

    Rows are returned as sqlite3.Row, which supports both positional and
    column-name access, so existing code written against mysql.connector's
    dictionary=True cursors keeps working unchanged.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        print(f"Connected to SQLite database at: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None
