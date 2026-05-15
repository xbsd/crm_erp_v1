#!/usr/bin/env python
"""Run the FastAPI Enterprise AI Workbench.

Usage:
    python scripts/run_webapp.py [--port 8000] [--host 127.0.0.1] [--reload]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from webapp.env_loader import load_env  # noqa: E402
load_env(verbose=True)

import uvicorn  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run(
        "webapp.main:app",
        host=args.host, port=args.port,
        reload=args.reload, log_level="info",
    )


if __name__ == "__main__":
    main()
