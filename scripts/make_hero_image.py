"""Generate a hero architecture diagram for the README."""
from __future__ import annotations

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)


def draw_box(ax, x, y, w, h, label, color, text_color="white", fontsize=10, bold=True):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.1",
        linewidth=0, facecolor=color, edgecolor="none",
    )
    ax.add_patch(box)
    fw = "bold" if bold else "normal"
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, color=text_color, fontweight=fw,
            wrap=True)


def arrow(ax, x1, y1, x2, y2, color="#666", lw=1.5):
    arr = FancyArrowPatch((x1, y1), (x2, y2),
                          arrowstyle="-|>", mutation_scale=14,
                          color=color, linewidth=lw)
    ax.add_patch(arr)


fig, ax = plt.subplots(figsize=(13, 7.5))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor("#FAFAFB")

# Title
ax.text(8, 8.55, "Enterprise AI Agent  ·  MCP-orchestrated CRM + ERP + QA",
        ha="center", fontsize=16, fontweight="bold", color="#1F2A44")
ax.text(8, 8.15, "Natural-language questions → Claude → 4 MCP servers → executive answers",
        ha="center", fontsize=11, color="#6B7280", style="italic")

# Top: user prompt
draw_box(ax, 5, 6.85, 6, 0.85,
         '"Who are my top 10 key accounts?"',
         "#FFEFD5", text_color="#6B4226", fontsize=12, bold=True)
arrow(ax, 8, 6.85, 8, 6.40, color="#9CA3AF", lw=2)

# Claude brain
draw_box(ax, 3.5, 5.4, 9, 0.95,
         "Claude Sonnet 4.5  ·  picks tools, calls them, synthesizes the answer",
         "#264E86", fontsize=11)
arrow(ax, 8, 5.4, 8, 5.05, color="#9CA3AF", lw=2)

# MCP protocol bar (extends across all four servers)
draw_box(ax, 0.4, 4.4, 12.5, 0.55,
         "MCP protocol  ·  stdio  ·  JSON-RPC tool calls",
         "#85B0F0", fontsize=10, text_color="#1F2A44")

# Four MCP servers
server_y, server_h, server_w = 2.65, 1.2, 2.9
servers = [
    ("Salesforce CRM", "10 tools", "#3B82F6"),
    ("ERP", "9 tools", "#10B981"),
    ("QA / Reliability", "7 tools", "#8B5CF6"),
    ("Analytics", "7 tools  ·  joins all 3", "#F97316"),
]
for i, (name, tools, color) in enumerate(servers):
    x = 0.4 + i * (server_w + 0.3)
    draw_box(ax, x, server_y, server_w, server_h, "", color)
    ax.text(x + server_w / 2, server_y + server_h - 0.35, name,
            ha="center", fontsize=11, fontweight="bold", color="white")
    ax.text(x + server_w / 2, server_y + 0.30, tools,
            ha="center", fontsize=9, color="white", style="italic")
    # Arrow from protocol bar to server
    arrow(ax, x + server_w / 2, 4.4, x + server_w / 2, server_y + server_h, color="#9CA3AF")
    # Arrow from server to database
    arrow(ax, x + server_w / 2, server_y, x + server_w / 2, server_y - 0.45, color="#9CA3AF")

# Databases
db_y, db_h = 1.4, 0.8
dbs = [
    ("crm.db", "Accounts, Opps,\nQuotes, Products", "#DBEAFE", "#1E40AF"),
    ("erp.db", "Orders, Invoices,\nRevenue, GL", "#D1FAE5", "#065F46"),
    ("qa.db", "Tests, MTBF, Failures,\nReturns, Compliance", "#EDE9FE", "#5B21B6"),
    ("(joins all 3)", "Cross-system\nanalytics", "#FED7AA", "#9A3412"),
]
for i, (name, sub, color, text) in enumerate(dbs):
    x = 0.4 + i * (server_w + 0.3)
    draw_box(ax, x, db_y, server_w, db_h, "", color)
    ax.text(x + server_w / 2, db_y + db_h - 0.20, name,
            ha="center", fontsize=10, fontweight="bold", color=text)
    ax.text(x + server_w / 2, db_y + 0.25, sub,
            ha="center", fontsize=8, color=text)

# Footer note
ax.text(8, 0.55,
        "Real-world reference data  ·  ~14 k CRM rows  ·  ~5 k ERP rows  ·  ~80 k QA rows  ·  Jan 2024 → May 2026",
        ha="center", fontsize=9, color="#6B7280", style="italic")

plt.tight_layout()
plt.savefig(OUT / "hero_architecture.png", dpi=160, bbox_inches="tight",
            facecolor="#FAFAFB")
print(f"Wrote {OUT / 'hero_architecture.png'}")
