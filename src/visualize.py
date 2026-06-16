"""
Vizualizacija rezultata.

Funkcije:
  - Distribucija pristrasnosti po portalu
  - Heatmap slaganja LLM vs human
  - Confusion matrice
  - Ton distribucija (boxplot/violin)
  - Comparison plot za više modela
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", context="notebook")


# ---------------------------------------------------------------------------
# Pojedinačni grafikoni
# ---------------------------------------------------------------------------


def plot_tone_by_portal(df: pd.DataFrame, output: Path, title_suffix: str = ""):
    """Box+strip plot tona po portalu."""
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=df, x="portal", y="tone", ax=ax, palette="vlag")
    sns.stripplot(data=df, x="portal", y="tone", ax=ax,
                  color="black", alpha=0.3, size=3)
    ax.set_ylabel("Ton (-2 do +2)")
    ax.set_xlabel("Portal")
    ax.set_title(f"Distribucija tona po portalu {title_suffix}")
    ax.axhline(0, color="gray", linestyle="--", linewidth=1)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_framing_distribution(df: pd.DataFrame, output: Path, title_suffix: str = ""):
    """Stacked bar plot framing-a po portalu."""
    cross = pd.crosstab(df["portal"], df["framing"], normalize="index") * 100

    fig, ax = plt.subplots(figsize=(11, 6))
    cross.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_ylabel("Postotak članaka (%)")
    ax.set_xlabel("Portal")
    ax.set_title(f"Distribucija framing-a po portalu {title_suffix}")
    ax.legend(title="Framing", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_political_lean_distribution(df: pd.DataFrame, output: Path, title_suffix: str = ""):
    """Stacked bar političke naklonosti po portalu."""
    cross = pd.crosstab(df["portal"], df["political_lean"], normalize="index") * 100

    fig, ax = plt.subplots(figsize=(11, 6))
    cross.plot(kind="bar", stacked=True, ax=ax, colormap="Set2")
    ax.set_ylabel("Postotak članaka (%)")
    ax.set_xlabel("Portal")
    ax.set_title(f"Politička naklonost po portalu {title_suffix}")
    ax.legend(title="Naklonost", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_balance_distribution(df: pd.DataFrame, output: Path, title_suffix: str = ""):
    """Distribucija balansiranosti."""
    fig, ax = plt.subplots(figsize=(9, 5))
    cross = pd.crosstab(df["portal"], df["balance"], normalize="index") * 100
    cross.plot(kind="bar", stacked=True, ax=ax,
               color=["#d62728", "#ff7f0e", "#2ca02c"])
    ax.set_ylabel("Postotak članaka (%)")
    ax.set_title(f"Balansiranost po portalu {title_suffix}")
    ax.legend(title="Balansiranost", labels=["0 - jednostrano", "1 - djelimično", "2 - balansirano"])
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_human_vs_llm_scatter(
    df_human: pd.DataFrame, df_llm: pd.DataFrame, dim: str,
    output: Path, llm_name: str = "LLM",
):
    """Scatter plot human vs LLM za ordinalnu dimenziju."""
    merged = df_human.merge(df_llm, on="article_id", suffixes=("_h", "_l"))
    merged = merged.dropna(subset=[f"{dim}_h", f"{dim}_l"])

    fig, ax = plt.subplots(figsize=(7, 7))

    # Jitter da se vidi gustoća
    jitter = np.random.normal(0, 0.05, len(merged))
    ax.scatter(
        merged[f"{dim}_h"] + jitter,
        merged[f"{dim}_l"] + np.random.normal(0, 0.05, len(merged)),
        alpha=0.5,
    )

    # Linija savršenog slaganja
    vmin = min(merged[f"{dim}_h"].min(), merged[f"{dim}_l"].min())
    vmax = max(merged[f"{dim}_h"].max(), merged[f"{dim}_l"].max())
    ax.plot([vmin, vmax], [vmin, vmax], "r--", label="Savršeno slaganje")

    ax.set_xlabel(f"Human: {dim}")
    ax.set_ylabel(f"{llm_name}: {dim}")
    ax.set_title(f"Human vs {llm_name} — {dim}")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_confusion_matrix(
    y_true, y_pred, labels, output: Path, title: str = "Confusion Matrix"
):
    """Confusion matrix heatmap."""
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(
        cm_norm,
        annot=cm,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
    )
    ax.set_xlabel("Predviđeno (LLM)")
    ax.set_ylabel("Tačno (Human)")
    ax.set_title(title)
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def plot_kappa_summary(report_files: list[Path], output: Path):
    """Bar plot kappa vrijednosti za više LLM modela."""
    import json

    data = []
    for f in report_files:
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        label = r["annotator_b"]
        for dim, m in r["dimensions"].items():
            kappa = m.get("kappa_linear") or m.get("kappa")
            if kappa is None:
                continue
            data.append({"model": label, "dimension": dim, "kappa": kappa})

    df = pd.DataFrame(data)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x="dimension", y="kappa", hue="model", ax=ax)
    ax.axhline(0.60, color="green", linestyle="--", label="Znatno slaganje (κ=0.6)")
    ax.axhline(0.40, color="orange", linestyle="--", label="Umjereno (κ=0.4)")
    ax.set_ylabel("Cohen's κ")
    ax.set_xlabel("Dimenzija")
    ax.set_title("Slaganje LLM modela sa ručnom anotacijom")
    ax.legend(loc="best")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV sa anotacijama")
    parser.add_argument("--output-dir", default="results", help="Direktorij za grafikone")
    parser.add_argument("--label", default="", help="Tag za naslov (npr. 'Human' ili 'GPT-4')")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = f"({args.label})" if args.label else ""

    plot_tone_by_portal(df, out_dir / "tone_by_portal.png", suffix)
    plot_framing_distribution(df, out_dir / "framing_by_portal.png", suffix)
    plot_political_lean_distribution(df, out_dir / "political_lean_by_portal.png", suffix)
    plot_balance_distribution(df, out_dir / "balance_by_portal.png", suffix)

    print(f"Grafikoni snimljeni u {out_dir}")


if __name__ == "__main__":
    main()
