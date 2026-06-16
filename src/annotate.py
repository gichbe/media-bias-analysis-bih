"""
Pomoćni CLI alat za ručnu anotaciju.

Učitava članke iz CSV-a, prikazuje ih jedan po jedan, i traži unos
po svakoj dimenziji prema kodbooku.

Pokretanje:
    python -m src.annotate \\
        --input data/processed/articles.csv \\
        --output data/annotations/human_A1.csv \\
        --annotator-id A1
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

FRAMING_OPTIONS = [
    "konflikt", "odgovornost", "ekonomski", "ljudski_interes",
    "moralni", "proceduralni", "nacionalni", "neutralan",
]

LEAN_OPTIONS = [
    "pro_vlast", "pro_opozicija",
    "pro_bosnjacka_opcija", "pro_srpska_opcija", "pro_hrvatska_opcija",
    "pro_gradjanska_opcija", "nejasno", "neutralan",
]


def prompt_int(question: str, valid: list[int], default: int | None = None) -> int:
    """Pita int sa validacijom."""
    suffix = f" (default={default})" if default is not None else ""
    while True:
        ans = input(f"{question}{suffix}: ").strip()
        if not ans and default is not None:
            return default
        try:
            v = int(ans)
            if v in valid:
                return v
        except ValueError:
            pass
        print(f"  Pogrešan unos. Validni: {valid}")


def prompt_choice(question: str, options: list[str]) -> str:
    """Pita izbor iz numerisane liste."""
    print(f"\n{question}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        ans = input(f"Izbor (1-{len(options)}): ").strip()
        try:
            idx = int(ans)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except ValueError:
            pass
        print("  Pogrešan unos.")


def show_article(article: dict, idx: int, total: int) -> None:
    """Lijep prikaz članka."""
    print("\n" + "=" * 80)
    print(f"  Članak {idx + 1} / {total}  ({article['portal']})")
    print("=" * 80)
    print(f"\n📰 NASLOV: {article['title']}")
    if article.get("date_published"):
        print(f"📅 DATUM:  {article['date_published']}")
    print(f"🔗 URL:    {article.get('url', 'n/a')}")
    print("\n" + "-" * 80)

    body = article.get("body", "")
    # Skrati ako je preduga
    if len(body) > 3000:
        print(body[:3000])
        print(f"\n[...skraćeno, ukupno {len(body)} karaktera]")
    else:
        print(body)
    print("-" * 80)


def annotate_article(article: dict, annotator_id: str) -> dict | None:
    """Pita anotatora za sve dimenzije. Vraća dict ili None ako preskače."""
    print("\n▶ KOMANDE: enter=dalje, 's'=skip, 'q'=quit i sačuvaj")
    cmd = input("Pritisni Enter za anotaciju: ").strip().lower()
    if cmd == "q":
        return "QUIT"
    if cmd == "s":
        return None

    tone = prompt_int("\n1. TON (-2..+2)", [-2, -1, 0, 1, 2])
    framing = prompt_choice("2. FRAMING", FRAMING_OPTIONS)
    balance = prompt_int("\n3. BALANSIRANOST (0=jednostrano, 1=djel., 2=balansirano)", [0, 1, 2])
    political_lean = prompt_choice("4. POLITICAL LEAN", LEAN_OPTIONS)
    dominant_actor = input("\n5. DOMINANTNI AKTER (slobodan tekst, enter za prazno): ").strip()
    confidence = prompt_int("\n6. CONFIDENCE (1-5)", [1, 2, 3, 4, 5], default=3)
    notes = input("\n7. NAPOMENE (opciono): ").strip()

    return {
        "article_id": article.get("article_id"),
        "portal": article.get("portal"),
        "url": article.get("url"),
        "title": article.get("title"),
        "date_published": article.get("date_published"),
        "annotator_id": annotator_id,
        "tone": tone,
        "framing": framing,
        "balance": balance,
        "political_lean": political_lean,
        "dominant_actor": dominant_actor or None,
        "confidence": confidence,
        "notes": notes or None,
    }


def load_existing(output_path: Path) -> set[str]:
    """Vrati article_id-ove već anotiranih (za nastavak sesije)."""
    if not output_path.exists():
        return set()
    df = pd.read_csv(output_path)
    return set(df["article_id"].astype(str).values)


def save_annotation(row: dict, output_path: Path) -> None:
    """Append jednu anotaciju u CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame([row])
    if output_path.exists():
        df_new.to_csv(output_path, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df_new.to_csv(output_path, index=False, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV ili JSON sa člancima")
    parser.add_argument("--output", required=True, help="CSV za snimanje anotacija")
    parser.add_argument("--annotator-id", required=True, help="Tvoj ID (npr. A1)")
    parser.add_argument("--shuffle", action="store_true", help="Random redoslijed")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.suffix == ".json":
        with input_path.open(encoding="utf-8") as f:
            articles = json.load(f)
    else:
        articles = pd.read_csv(input_path).to_dict("records")

    output_path = Path(args.output)
    already_done = load_existing(output_path)
    print(f"Već anotirano u ovom fajlu: {len(already_done)}")

    todo = [a for a in articles if str(a.get("article_id")) not in already_done]
    if args.shuffle:
        import random
        random.shuffle(todo)
    if args.limit:
        todo = todo[: args.limit]

    print(f"Za anotaciju u ovoj sesiji: {len(todo)}")

    for i, article in enumerate(todo):
        show_article(article, i, len(todo))
        result = annotate_article(article, args.annotator_id)
        if result == "QUIT":
            print("\nIzlazim. Anotacije su snimljene.")
            sys.exit(0)
        if result is None:
            continue
        save_annotation(result, output_path)
        print(f"✓ Snimljeno. Ukupno u fajlu: {len(load_existing(output_path))}")

    print(f"\n🎉 Završeno! Anotacija: {output_path}")


if __name__ == "__main__":
    main()
