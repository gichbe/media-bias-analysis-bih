"""
Metrike za poređenje anotacija.

Podržava dva slučaja:
  1. Dva anotatora (Human vs LLM, ili dva ljudska anotatora) — Cohen's Kappa
  2. 3+ anotatora (više ljudskih) — Fleiss' kappa, Krippendorff's alpha, pairwise Cohen

Dodatno:
  - Konstrukcija gold-standard anotacije iz više anotatora
    (medijan za ordinalne, mode za kategoričke dimenzije)
"""

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
)


ORDINAL_DIMS = ["tone", "balance"]
CATEGORICAL_DIMS = ["framing", "political_lean"]
ALL_DIMS = ORDINAL_DIMS + CATEGORICAL_DIMS


# ============================================================================
# Slučaj 1: Dva anotatora (Human vs LLM, ili 2 ljudska)
# ============================================================================

def align_annotations(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    """Spaja dvije anotacije po article_id."""
    return df_a.merge(df_b, on="article_id", suffixes=("_a", "_b"), how="inner")


def compute_dimension_metrics(merged: pd.DataFrame, dim: str) -> dict:
    """Računa metrike slaganja za jednu dimenziju (2 anotatora)."""
    col_a = f"{dim}_a"
    col_b = f"{dim}_b"
    df = merged.dropna(subset=[col_a, col_b])
    if df.empty:
        return {"n": 0, "error": "Nema preklapanja"}

    metrics = {"n": len(df)}

    if dim in ORDINAL_DIMS:
        y_a = pd.to_numeric(df[col_a], errors="coerce")
        y_b = pd.to_numeric(df[col_b], errors="coerce")
        valid = y_a.notna() & y_b.notna()
        y_a = y_a[valid].astype(int).values
        y_b = y_b[valid].astype(int).values

        metrics["kappa_linear"] = cohen_kappa_score(y_a, y_b, weights="linear")
        metrics["kappa_quadratic"] = cohen_kappa_score(y_a, y_b, weights="quadratic")
        metrics["mae"] = mean_absolute_error(y_a, y_b)
        metrics["exact_agreement"] = accuracy_score(y_a, y_b)
        metrics["mean_a"] = float(np.mean(y_a))
        metrics["mean_b"] = float(np.mean(y_b))
    else:
        y_a = df[col_a].astype(str).values
        y_b = df[col_b].astype(str).values
        metrics["kappa"] = cohen_kappa_score(y_a, y_b)
        metrics["accuracy"] = accuracy_score(y_a, y_b)
        metrics["f1_macro"] = f1_score(y_a, y_b, average="macro", zero_division=0)

        labels = sorted(set(y_a) | set(y_b))
        cm = confusion_matrix(y_a, y_b, labels=labels)
        metrics["labels"] = labels
        metrics["confusion_matrix"] = cm.tolist()

    return metrics


def compare(df_a: pd.DataFrame, df_b: pd.DataFrame,
            label_a: str, label_b: str) -> dict:
    """Glavno poređenje dva seta anotacija."""
    merged = align_annotations(df_a, df_b)
    return {
        "mode": "two_annotators",
        "annotator_a": label_a,
        "annotator_b": label_b,
        "n_overlap": len(merged),
        "dimensions": {dim: compute_dimension_metrics(merged, dim) for dim in ALL_DIMS},
    }


# ============================================================================
# Slučaj 2: Tri ili više anotatora
# ============================================================================

def align_multi(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Spaja N anotacija po article_id; vraća merged sa sufiksima _0, _1, _2..."""
    if not dfs:
        return pd.DataFrame()
    # Standardiziraj kolone — samo article_id + 4 dimenzije
    cleaned = []
    for i, df in enumerate(dfs):
        keep = ["article_id"] + ALL_DIMS
        existing = [c for c in keep if c in df.columns]
        sub = df[existing].copy()
        sub = sub.rename(columns={d: f"{d}_{i}" for d in ALL_DIMS if d in sub.columns})
        cleaned.append(sub)

    merged = cleaned[0]
    for sub in cleaned[1:]:
        merged = merged.merge(sub, on="article_id", how="inner")
    return merged


def compute_fleiss_kappa(merged: pd.DataFrame, dim: str, n_annotators: int) -> float | None:
    """Fleiss' kappa za kategoričku dimenziju, više anotatora."""
    try:
        from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa
    except ImportError:
        return None

    cols = [f"{dim}_{i}" for i in range(n_annotators)]
    df = merged.dropna(subset=cols)
    if df.empty:
        return None
    ratings = df[cols].astype(str).values
    table, _ = aggregate_raters(ratings)
    return float(fleiss_kappa(table, method="fleiss"))


def compute_krippendorff_alpha(
    merged: pd.DataFrame, dim: str, n_annotators: int, level: str = "ordinal"
) -> float | None:
    """Krippendorff's alpha. level = 'ordinal' ili 'nominal'."""
    try:
        import krippendorff
    except ImportError:
        return None

    cols = [f"{dim}_{i}" for i in range(n_annotators)]
    df = merged[cols]
    if level == "ordinal":
        data = df.apply(pd.to_numeric, errors="coerce").values.T  # (n_raters, n_items)
    else:
        data = df.astype(str).values.T

    try:
        return float(krippendorff.alpha(reliability_data=data, level_of_measurement=level))
    except Exception:
        return None


def compute_pairwise_cohen(
    merged: pd.DataFrame, dim: str, n_annotators: int, ordinal: bool
) -> list[dict]:
    """Cohen's kappa za sve parove anotatora."""
    results = []
    for i, j in combinations(range(n_annotators), 2):
        col_i = f"{dim}_{i}"
        col_j = f"{dim}_{j}"
        df = merged.dropna(subset=[col_i, col_j])
        if len(df) < 2:
            continue
        if ordinal:
            y_i = pd.to_numeric(df[col_i], errors="coerce").dropna().astype(int).values
            y_j = pd.to_numeric(df[col_j], errors="coerce").dropna().astype(int).values
            kappa = cohen_kappa_score(y_i, y_j, weights="linear")
        else:
            y_i = df[col_i].astype(str).values
            y_j = df[col_j].astype(str).values
            kappa = cohen_kappa_score(y_i, y_j)
        results.append({"pair": f"A{i}-A{j}", "kappa": float(kappa), "n": len(df)})
    return results


def compute_multi_dimension_metrics(
    merged: pd.DataFrame, dim: str, n_annotators: int
) -> dict:
    """Sve metrike slaganja za jednu dimenziju, više anotatora."""
    is_ordinal = dim in ORDINAL_DIMS
    metrics = {
        "n_items": len(merged),
        "is_ordinal": is_ordinal,
    }

    if is_ordinal:
        alpha = compute_krippendorff_alpha(merged, dim, n_annotators, level="ordinal")
        metrics["krippendorff_alpha_ordinal"] = alpha
    else:
        fleiss = compute_fleiss_kappa(merged, dim, n_annotators)
        alpha = compute_krippendorff_alpha(merged, dim, n_annotators, level="nominal")
        metrics["fleiss_kappa"] = fleiss
        metrics["krippendorff_alpha_nominal"] = alpha

    metrics["pairwise_cohen"] = compute_pairwise_cohen(merged, dim, n_annotators, is_ordinal)
    return metrics


def compare_multi(dfs: list[pd.DataFrame], labels: list[str]) -> dict:
    """Slaganje između 3+ anotatora."""
    merged = align_multi(dfs)
    n = len(dfs)
    return {
        "mode": "multi_annotators",
        "annotators": labels,
        "n_annotators": n,
        "n_overlap": len(merged),
        "dimensions": {
            dim: compute_multi_dimension_metrics(merged, dim, n) for dim in ALL_DIMS
        },
    }


# ============================================================================
# Konstrukcija gold-standard anotacije
# ============================================================================

def build_gold_standard(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Iz N anotacija pravi gold-standard:
      - Ordinalne dimenzije: medijan ocjena
      - Kategoričke dimenzije: mode (većinsko glasanje); izjednačenje → prvi po abecedi

    Zadržava samo članke koje su SVI anotatori obradili.
    """
    if not dfs:
        return pd.DataFrame()

    merged = align_multi(dfs)
    n = len(dfs)
    rows = []

    for _, row in merged.iterrows():
        gold = {"article_id": row["article_id"], "annotator_id": "GOLD"}

        # Ordinalne: medijan, zaokruženo prema 0
        for dim in ORDINAL_DIMS:
            cols = [f"{dim}_{i}" for i in range(n)]
            vals = pd.to_numeric(row[cols], errors="coerce").dropna().values
            if len(vals) == 0:
                gold[dim] = None
                continue
            med = np.median(vals)
            # Zaokruživanje prema 0 (neutralna vrijednost) u slučaju .5
            if med == int(med):
                gold[dim] = int(med)
            else:
                # 1.5 → 1, -1.5 → -1 (prema 0)
                gold[dim] = int(np.sign(med) * np.floor(abs(med)))

        # Kategoričke: mode
        for dim in CATEGORICAL_DIMS:
            cols = [f"{dim}_{i}" for i in range(n)]
            vals = row[cols].astype(str).values
            vals = [v for v in vals if v not in ("nan", "None", "")]
            if not vals:
                gold[dim] = None
                continue
            mode_vals = pd.Series(vals).mode()
            gold[dim] = mode_vals.iloc[0]  # prvi po abecedi ako više njih

        rows.append(gold)

    return pd.DataFrame(rows)


# ============================================================================
# Helpers za interpretaciju i ispis
# ============================================================================

def interpret_kappa(kappa: float | None) -> str:
    if kappa is None:
        return "n/a"
    if kappa < 0:
        return "gore od slučajnog"
    if kappa < 0.20:
        return "vrlo slabo"
    if kappa < 0.40:
        return "slabo"
    if kappa < 0.60:
        return "umjereno"
    if kappa < 0.80:
        return "znatno"
    return "gotovo savršeno"


def print_two_annotator_report(report: dict) -> None:
    print("\n" + "=" * 70)
    print(f"  Poređenje: {report['annotator_a']} vs {report['annotator_b']}")
    print(f"  Preklapanje: n = {report['n_overlap']}")
    print("=" * 70)
    for dim, m in report["dimensions"].items():
        print(f"\n  [{dim.upper()}] (n={m.get('n', 0)})")
        if "error" in m:
            print(f"    {m['error']}")
            continue
        if dim in ORDINAL_DIMS:
            k_lin = m["kappa_linear"]
            print(f"    κ (linearna):    {k_lin:.3f}  ({interpret_kappa(k_lin)})")
            print(f"    κ (kvadratna):   {m['kappa_quadratic']:.3f}")
            print(f"    MAE:             {m['mae']:.3f}")
            print(f"    Tačno slaganje:  {m['exact_agreement']:.1%}")
            print(f"    Srednje: A={m['mean_a']:+.2f}, B={m['mean_b']:+.2f}")
        else:
            k = m["kappa"]
            print(f"    κ:           {k:.3f}  ({interpret_kappa(k)})")
            print(f"    Accuracy:    {m['accuracy']:.1%}")
            print(f"    F1 (macro):  {m['f1_macro']:.3f}")


def print_multi_annotator_report(report: dict) -> None:
    print("\n" + "=" * 70)
    print(f"  Poređenje {report['n_annotators']} anotatora: " +
          ", ".join(report["annotators"]))
    print(f"  Članci anotirani od svih: n = {report['n_overlap']}")
    print("=" * 70)

    for dim, m in report["dimensions"].items():
        print(f"\n  [{dim.upper()}]")
        if m["is_ordinal"]:
            alpha = m.get("krippendorff_alpha_ordinal")
            label = "ordinalna" if alpha is not None else "n/a (instaliraj krippendorff)"
            print(f"    Krippendorff's α ({label}):  " +
                  (f"{alpha:.3f}  ({interpret_kappa(alpha)})" if alpha is not None else "—"))
        else:
            fleiss = m.get("fleiss_kappa")
            alpha = m.get("krippendorff_alpha_nominal")
            if fleiss is not None:
                print(f"    Fleiss' κ:        {fleiss:.3f}  ({interpret_kappa(fleiss)})")
            else:
                print(f"    Fleiss' κ:        n/a (instaliraj statsmodels)")
            if alpha is not None:
                print(f"    Krippendorff α:   {alpha:.3f}  ({interpret_kappa(alpha)})")

        print("    Pairwise Cohen's κ:")
        for p in m["pairwise_cohen"]:
            print(f"      {p['pair']}:  {p['kappa']:.3f}  ({interpret_kappa(p['kappa'])})  n={p['n']}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Metrike slaganja anotacija (2 ili više anotatora)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Postojeći mode: dva anotatora
    p_two = sub.add_parser("two", help="Poređenje dva anotatora (npr. Human vs LLM)")
    p_two.add_argument("--annotation-a", required=True)
    p_two.add_argument("--annotation-b", required=True)
    p_two.add_argument("--label-a", default="A")
    p_two.add_argument("--label-b", default="B")
    p_two.add_argument("--output-json", default=None)

    # Novi mode: više anotatora
    p_multi = sub.add_parser("multi", help="Poređenje 3+ anotatora")
    p_multi.add_argument("--annotations", nargs="+", required=True,
                         help="CSV fajlovi sa anotacijama")
    p_multi.add_argument("--labels", nargs="+",
                         help="Oznake anotatora (default: A1, A2, ...)")
    p_multi.add_argument("--output-json", default=None)
    p_multi.add_argument("--build-gold", default=None,
                         help="Putanja za snimanje gold-standard CSV-a")

    args = parser.parse_args()

    if args.cmd == "two":
        df_a = pd.read_csv(args.annotation_a)
        df_b = pd.read_csv(args.annotation_b)
        report = compare(df_a, df_b, args.label_a, args.label_b)
        print_two_annotator_report(report)

        if args.output_json:
            Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

    elif args.cmd == "multi":
        dfs = [pd.read_csv(p) for p in args.annotations]
        labels = args.labels or [f"A{i+1}" for i in range(len(dfs))]
        if len(labels) != len(dfs):
            raise ValueError("Broj label-a mora odgovarati broju fajlova")

        report = compare_multi(dfs, labels)
        print_multi_annotator_report(report)

        if args.output_json:
            Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        if args.build_gold:
            gold = build_gold_standard(dfs)
            Path(args.build_gold).parent.mkdir(parents=True, exist_ok=True)
            gold.to_csv(args.build_gold, index=False, encoding="utf-8")
            print(f"\nGold standard ({len(gold)} članaka) snimljen u {args.build_gold}")


if __name__ == "__main__":
    main()
