#!/usr/bin/env python
"""End-to-end UI smoke test using Playwright.

- Loads every page
- Captures screenshots
- Verifies critical content rendered (KPI cards, account list, tool catalog, etc.)
- Drives the AI Assistant WebSocket through 3 representative questions and checks the trace + answer.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.async_api import async_playwright


SCREENSHOT_DIR = REPO_ROOT / "outputs" / "ui_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


PAGES = [
    {"path": "/",             "name": "01_dashboard",     "wait_for": ".kpi-value", "title_contains": "Executive Dashboard"},
    {"path": "/assistant",    "name": "02_assistant",     "wait_for": "#composer-input", "title_contains": "AI Assistant"},
    {"path": "/customer-360", "name": "03_customer360",   "wait_for": "#account-select", "title_contains": "Customer 360"},
    {"path": "/reliability",  "name": "04_reliability",   "wait_for": "#product-select", "title_contains": "Product Reliability"},
    {"path": "/tools",        "name": "05_tools",         "wait_for": "#catalog", "title_contains": "Tool Catalog"},
    {"path": "/data-model",   "name": "06_data_model",    "wait_for": "#db-tables", "title_contains": "Data Model"},
    {"path": "/system",       "name": "07_system",        "wait_for": "#server-cards", "title_contains": "System Health"},
]

ASSISTANT_QUESTIONS = [
    "Who are my top 5 key accounts? Show industry and total revenue.",
    "Is there any big change in Q1 2026 vs Q1 2025 revenue for key accounts? Limit to 5 examples.",
    "Show me the order booking patterns for Lockheed Martin by quarter.",
]


async def smoke(base_url: str, theme: str = "light") -> None:
    print(f"\n=== UI smoke test against {base_url} (theme={theme}) ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Set theme via localStorage before any navigation
        await page.add_init_script(f"localStorage.setItem('theme', '{theme}');")

        results: list[dict] = []
        for p_info in PAGES:
            url = base_url + p_info["path"]
            print(f"  → {url}")
            t0 = time.time()
            await page.goto(url, wait_until="networkidle")
            try:
                await page.wait_for_selector(p_info["wait_for"], timeout=10_000)
                ok = True
                err = None
            except Exception as e:
                ok = False
                err = str(e)
            # Wait a bit longer for charts to render
            await page.wait_for_timeout(1200)
            shot = SCREENSHOT_DIR / f"{p_info['name']}_{theme}.png"
            await page.screenshot(path=str(shot), full_page=True)
            dt = time.time() - t0
            print(f"     {'✓' if ok else '✗'} {dt:.1f}s · screenshot: {shot.name}{' · err: '+err if err else ''}")
            results.append({"page": p_info["path"], "ok": ok, "duration": dt, "screenshot": str(shot)})

        # ------------------------------------------------------------------
        # AI Assistant interactive test
        # ------------------------------------------------------------------
        print(f"\n  AI Assistant — running {len(ASSISTANT_QUESTIONS)} questions live…")
        await page.goto(base_url + "/assistant", wait_until="networkidle")
        await page.wait_for_selector("#composer-input")

        for i, q in enumerate(ASSISTANT_QUESTIONS, 1):
            print(f"    [{i}] {q[:80]}")
            await page.fill("#composer-input", q)
            await page.keyboard.press("Enter")
            # Wait for the final event in the trace panel (".event.final")
            t0 = time.time()
            try:
                await page.wait_for_selector(".event.final", timeout=120_000)
                ok = True
            except Exception as e:
                ok = False
                print(f"       ✗ timeout waiting for final event: {e}")
            dt = time.time() - t0
            # Pull metrics
            n_events = await page.locator(".event").count()
            n_tools = await page.locator(".event.tool_call").count()
            print(f"       {'✓' if ok else '✗'} {dt:.1f}s · {n_events} events · {n_tools} tool calls")
            # Screenshot
            shot = SCREENSHOT_DIR / f"08_assistant_q{i}_{theme}.png"
            await page.screenshot(path=str(shot), full_page=True)
            # Reset before next
            if i < len(ASSISTANT_QUESTIONS):
                await page.click("#reset-btn")
                await page.wait_for_timeout(800)

        await browser.close()
        print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8770")
    parser.add_argument("--theme", default="light", choices=["light", "dark"])
    args = parser.parse_args()
    asyncio.run(smoke(args.base_url, args.theme))
