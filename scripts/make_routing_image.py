"""Render a tool-routing heat-map showing which MCP server answered which use case."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "outputs" / "use_case_runs.json"
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

data = json.loads(RUNS.read_text())
servers = ["Salesforce CRM", "ERP System", "QA / Reliability", "Analytics (cross-system)"]
cases = data["runs"]

# Matrix: rows = use cases, cols = servers, value = tool calls
matrix = np.zeros((len(cases), len(servers)), dtype=int)
case_labels = []
for i, c in enumerate(cases):
    case_labels.append(f"{c['id']}  {c['title']}")
    for t in c["trace"]:
        if t["server_label"] in servers:
            j = servers.index(t["server_label"])
            matrix[i, j] += 1

# Plot
fig, ax = plt.subplots(figsize=(11, 5.2))
cmap = plt.colormaps["YlOrRd"]
im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=max(matrix.max(), 2))

ax.set_xticks(range(len(servers)))
ax.set_xticklabels(servers, rotation=20, ha="right")
ax.set_yticks(range(len(cases)))
ax.set_yticklabels(case_labels)
ax.set_title("Which MCP server answered each question?", fontsize=14, fontweight="bold", pad=14)

# Annotate cells
for i in range(matrix.shape[0]):
    for j in range(matrix.shape[1]):
        v = matrix[i, j]
        if v > 0:
            ax.text(j, i, str(v), ha="center", va="center",
                    color="white" if v >= 2 else "#1F2A44",
                    fontsize=11, fontweight="bold")

cbar = plt.colorbar(im, ax=ax, label="Tool calls", shrink=0.7)
plt.tight_layout()
plt.savefig(OUT / "tool_routing.png", dpi=160, facecolor="white", bbox_inches="tight")
print(f"Wrote {OUT / 'tool_routing.png'}")
