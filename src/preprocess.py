"""
Preprocessing — uzima sirove scrapirane JSON-ove i pretvara ih u
jedinstven CSV spreman za anotaciju.

Pokretanje:
    python -m src.preprocess --input data/raw/ --output data/processed/articles.csv
"""

import argparse
import json
import logging
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def clean_text(text: str) -> str:
    """Osnovno čišćenje teksta."""
    if not isinstance(text, str):
        return ""
    # Ukloni višestruke whitespace
    text = re.sub(r"\s+", " ", text)
    # Ukloni "PROČITAJTE I:" i slične promo segmente koji često ostaju
    text = re.sub(
        r"(PROČITAJTE I:|VIDI JOŠ:|MOŽDA VAS ZANIMA:)[^.]*\.",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def load_raw_files(input_dir: Path) -> list[dict]:
    """Učitaj sve JSON fajlove iz raw direktorija."""
    articles = []
    for json_file in input_dir.glob("*.json"):
        logger.info("Učitavam %s", json_file)
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            articles.extend(data)
        else:
            articles.append(data)
    return articles


def deduplicate(articles: list[dict]) -> list[dict]:
    """Ukloni duplikate po article_id i URL-u."""
    seen_ids = set()
    seen_urls = set()
    unique = []
    for a in articles:
        aid = a.get("article_id")
        url = a.get("url")
        if aid in seen_ids or url in seen_urls:
            continue
        seen_ids.add(aid)
        seen_urls.add(url)
        unique.append(a)
    return unique


def filter_quality(articles: list[dict], min_length: int = 300) -> list[dict]:
    """Filtriraj članke koji su prekratki ili imaju problem."""
    filtered = []
    for a in articles:
        body = a.get("body", "")
        title = a.get("title", "")
        if not title or not body:
            continue
        if len(body) < min_length:
            continue

        # Listing/kategorijske stranice: kratak naslov sa "|"
        # (npr. "Ekonomija | N1 info", "Vijesti | Klix")
        if "|" in title and len(title) < 50:
            continue

        # Body koji izgleda kao listing (mnogo "prije X h" oznaka)
        body_lower = body.lower()
        listing_markers = body_lower.count("prije") + body_lower.count(" | 0")
        if listing_markers > 10:
            continue

        filtered.append(a)
    return filtered


def filter_political(articles: list[dict]) -> list[dict]:
    """
    Filtriraj samo političke članke na osnovu ključnih riječi.
    Korisno ako su scraperi pokupili i ne-političke teme.
    """
    keywords = [
        # Bošnjački/civic politički termini
        "premijer", "ministar", "vlada", "parlament", "skupština",
        "izbori", "stranka", "SDA", "SDP", "NiP", "Naša stranka",
        # Srpski/RS termini
        "Republika Srpska", "Dodik", "SNSD", "PDP", "Cvijanović",
        # Hrvatski termini
        "HDZ", "Čović", "Hrvati BiH",
        # Opći
        "BiH", "Bosna i Hercegovina", "Federacija", "ustav", "predsjedništvo",
        "zakon", "EU integracije", "NATO", "izborna",
    ]
    keywords_lower = [k.lower() for k in keywords]

    filtered = []
    for a in articles:
        text = (a.get("title", "") + " " + a.get("body", "")).lower()
        if any(kw in text for kw in keywords_lower):
            filtered.append(a)
    return filtered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw", help="Direktorij sa raw JSON-ovima")
    parser.add_argument("--output", default="data/processed/articles.csv")
    parser.add_argument("--min-length", type=int, default=300)
    parser.add_argument(
        "--no-political-filter",
        action="store_true",
        help="Preskoči filtriranje po političkim ključnim riječima",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    raw_articles = load_raw_files(input_dir)
    logger.info("Učitano sirovih: %d", len(raw_articles))

    # Pipeline
    articles = deduplicate(raw_articles)
    logger.info("Nakon dedup: %d", len(articles))

    articles = filter_quality(articles, args.min_length)
    logger.info("Nakon kvalitet filtera: %d", len(articles))

    if not args.no_political_filter:
        articles = filter_political(articles)
        logger.info("Nakon političkog filtera: %d", len(articles))

    # Očisti tekstove
    for a in articles:
        a["title"] = clean_text(a.get("title", ""))
        a["body"] = clean_text(a.get("body", ""))
        a["lead"] = clean_text(a.get("lead", ""))

    # U CSV
    df = pd.DataFrame(articles)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    # I JSON za zadržavanje punog teksta bez CSV escape problema
    json_path = output_path.with_suffix(".json")
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # Sažetak
    print("\nSAŽETAK PO PORTALU:")
    print(df["portal"].value_counts().to_string())
    print(f"\nUkupno: {len(df)} članaka")
    print(f"CSV: {output_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
