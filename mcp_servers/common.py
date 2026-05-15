"""Shared utilities for all MCP servers (DB connections, formatting helpers)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

# Resolve database paths relative to the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = REPO_ROOT / "databases"

CRM_DB = DB_DIR / "crm.db"
ERP_DB = DB_DIR / "erp.db"
QA_DB = DB_DIR / "qa.db"


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Open a read-only connection (URI mode)."""
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def crm() -> sqlite3.Connection:
    return connect_readonly(CRM_DB)


def erp() -> sqlite3.Connection:
    return connect_readonly(ERP_DB)


def qa() -> sqlite3.Connection:
    return connect_readonly(QA_DB)


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def json_dumps_safe(obj: Any) -> str:
    return json.dumps(obj, default=str, indent=2)
