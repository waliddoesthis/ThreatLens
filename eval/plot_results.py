"""Bar charts for the README from eval/results/*.json -> docs/img/*.png

python eval/plot_results.py   (needs matplotlib: pip install -e ".[eval]")
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).parents[1]
RES = ROOT / "eval" / "results"
IMG = ROOT / "docs" / "img"
BLUE, GRAY, INK, MUTED, SURFACE = "#2a78d6", "#b9b8b3", "#0b0b0b", "#52514e", "#fcfcfb"


def hbars(ax, labels, values, title, highlight=None):
    y = range(len(labels))[::-1]
    colors = [BLUE if highlight is None or lab == highlight else GRAY for lab in labels]
    ax.barh(list(y), values, color=colors, height=0.6, edgecolor=SURFACE, linewidth=2)
    for yi, v in zip(y, values, strict=True):
        ax.text(v + 0.01, yi, f"{v:.3f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(list(y), labels, fontsize=9, color=INK)
    ax.set_xlim(0, 1.12)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)
    ax.grid(axis="x", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#d0cfca")


def figure(rows, label_key, title, out, highlight=None):
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.45 * len(rows) + 1.4), facecolor=SURFACE)
    labels = [r[label_key] for r in rows]
    for ax, metric in zip(axes, ["recall@5", "mrr@10"], strict=True):
        ax.set_facecolor(SURFACE)
        hbars(ax, labels, [r[metric] for r in rows], metric.replace("@", " @ "), highlight)
    axes[1].set_yticks([])
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout()
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / out, dpi=150, facecolor=SURFACE)
    print("wrote", IMG / out)


def main() -> None:
    ret = json.loads((RES / "retrieval.json").read_text())["overall"]
    n = ret[0]["n"]
    figure(ret, "mode", f"Retrieval ablation ({n} questions)", "retrieval.png", "graph+translate")
    alerts_file = RES / "retrieval-alerts.json"
    if alerts_file.exists():
        al = json.loads(alerts_file.read_text())["overall"]
        title = f"Real command lines from Atomic Red Team ({al[0]['n']} alerts)"
        figure(al, "mode", title, "retrieval-alerts.png", "graph")
    abl_file = RES / "ablation.json"
    if abl_file.exists():
        abl = json.loads(abl_file.read_text())
        rows, seen = [], set()
        for group in ("chunk", "embedding"):
            for r in abl.get(group, {}).get("overall", []):
                if r["mode"] == "hybrid+rerank+rrf" and r["config"] not in seen:
                    seen.add(r["config"])
                    rows.append(r)
        if rows:
            figure(rows, "config", "Chunk size and embedding model (hybrid + fused rerank)",
                   "ablation.png", "bge-small-en-v1.5_220w")  # fmt: skip


if __name__ == "__main__":
    main()
