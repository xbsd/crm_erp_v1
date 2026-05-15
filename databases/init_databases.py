"""Initialize the three SQLite databases (CRM, ERP, QA) from the schema files."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB_DIR = ROOT


def init_db(db_path: Path, schema_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Initialized {db_path.name}")


def main() -> None:
    init_db(DB_DIR / "crm.db", DB_DIR / "schema_crm.sql")
    init_db(DB_DIR / "erp.db", DB_DIR / "schema_erp.sql")
    init_db(DB_DIR / "qa.db", DB_DIR / "schema_qa.sql")
    print("All databases initialized.")


if __name__ == "__main__":
    main()
