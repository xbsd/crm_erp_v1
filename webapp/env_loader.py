"""Automatic .env loading.

Loads, in order:
  1. <repo>/.env   (project-local)
  2. ~/.env        (user-global — where the user keeps shared keys)

Later sources do NOT override earlier ones, so a project-specific value wins.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env(verbose: bool = False) -> dict[str, bool]:
    """Load .env files into os.environ. Returns which files were found."""
    project_env = REPO_ROOT / ".env"
    home_env = Path.home() / ".env"
    found = {"project": False, "home": False}

    if project_env.exists():
        load_dotenv(project_env, override=False)
        found["project"] = True

    if home_env.exists():
        load_dotenv(home_env, override=False)
        found["home"] = True

    if verbose:
        print(f"Project .env: {'found' if found['project'] else 'absent'} ({project_env})")
        print(f"Home    .env: {'found' if found['home'] else 'absent'} ({home_env})")
        print(f"ANTHROPIC_API_KEY: {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'missing'}")

    return found
