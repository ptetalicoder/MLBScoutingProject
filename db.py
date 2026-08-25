"""SQLite adapter shared by the ETL scripts, the Streamlit app, and player_crud.py.

Public-demo build: everything reads/writes a local SQLite file instead of a
hosted MySQL instance.
"""
import os
import shutil
import sqlite3
import tempfile

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "mlb_scouting.db"),
)


def create_db_connection():
    """Creates a connection to the local SQLite database.

    check_same_thread=False: the Streamlit app caches this connection with
    st.cache_resource, and Streamlit executes each script rerun on a fresh
    thread. Without this, the second interaction in any session raises
    "SQLite objects created in a thread can only be used in that same
    thread." Safe here because the app only ever does one query at a time
    per cached connection -- there's no concurrent access to guard against.

    Rows default to sqlite3.Row, which supports both positional access
    (row[0]) and column-name access (row["col"]) and unpacks like a tuple
    when iterated -- a drop-in replacement for mysql.connector's plain
    cursors. Code that was written against mysql.connector's
    dictionary=True cursors (which calls row.get(...)) needs plain dicts
    instead, since sqlite3.Row has no .get(); use dict_row_factory on that
    specific cursor for those call sites, e.g.:

        cursor = conn.cursor()
        cursor.row_factory = dict_row_factory
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        print(f"Connected to SQLite database at: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None


def create_readonly_connection():
    """Read-only connection to the committed database, safe to share publicly.

    Opens `mlb_scouting.db` in SQLite's URI read-only mode, so even a bug or
    a hostile query can't write to the committed file -- used for the public
    demo's SQL Chat and Analytics Dashboard, which only ever need SELECT.
    """
    try:
        uri = f"file:{DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        print(f"Connected read-only to SQLite database at: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database (read-only): {e}")
        return None


def create_sandbox_connection():
    """Writable connection to a private, temporary copy of the database.

    Copies the committed database to a fresh temp file and connects to the
    copy, so CRUD writes never touch the real mlb_scouting.db. Callers
    should create one of these per session (e.g. cached on
    st.session_state) rather than calling this on every rerun, since each
    call makes a new on-disk copy.
    """
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db", prefix="mlb_scouting_sandbox_")
        os.close(tmp_fd)
        shutil.copy2(DB_PATH, tmp_path)
        conn = sqlite3.connect(tmp_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        print(f"Connected to per-session CRUD sandbox at: {tmp_path}")
        return conn
    except (sqlite3.Error, OSError) as e:
        print(f"Error creating CRUD sandbox: {e}")
        return None


def dict_row_factory(cursor, row):
    """Per-cursor row_factory that returns a plain dict instead of sqlite3.Row.

    Set this on individual cursors that need dict-style .get() access
    (the equivalent of mysql.connector's cursor(dictionary=True)), while
    leaving the connection's default sqlite3.Row factory alone for code
    that unpacks rows positionally.
    """
    fields = [col[0] for col in cursor.description]
    return dict(zip(fields, row))
