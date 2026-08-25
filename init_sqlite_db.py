"""Creates the local SQLite database from 05_DDL_schema_v1_sqlite.sql.

Run this once before the data_import_*.py scripts. Safe to re-run against an
existing file as long as the tables don't already exist (drop the .db file
first if you want a clean rebuild).
"""
import os
import sqlite3

from db import DB_PATH

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "05_DDL_schema_v1_sqlite.sql")


def main():
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print(f"Creating SQLite database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(schema_sql)
        conn.commit()
        print("Schema created successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
