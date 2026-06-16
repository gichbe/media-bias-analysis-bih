"""
Orchestrator — pokreće sve scrapere i kombinuje rezultate u jedan dataset.

Pokretanje:
    python -m scrapers.run_all --num-per-portal 100
"""

import argparse
import json
from pathlib import Path

from scrapers.avaz_scraper import AvazScraper
from scrapers.klix_scraper import KlixScraper
from scrapers.n1_scraper import N1Scraper
from scrapers.nezavisne_scraper import NezavisneScraper
from scrapers.vecernji_scraper import VecernjiScraper

SCRAPERS = [
    KlixScraper,
    AvazScraper,
    NezavisneScraper,
    VecernjiScraper,
    N1Scraper,
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-per-portal", type=int, default=100)
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument(
        "--combined-output", default="data/processed/all_articles.json"
    )
    parser.add_argument(
        "--only",
        nargs="*",
        help="Pokreni samo navedene portale (npr. klix avaz)",
    )
    args = parser.parse_args()

    all_articles = []

    for ScraperCls in SCRAPERS:
        if args.only and ScraperCls.PORTAL_NAME not in args.only:
            continue
        scraper = ScraperCls(output_dir=args.output_dir)
        try:
            articles = scraper.run(max_articles=args.num_per_portal)
            all_articles.extend(a.to_dict() for a in articles)
        except Exception as exc:
            scraper.logger.exception("Scraper %s pao: %s", ScraperCls.PORTAL_NAME, exc)

    # Kombinovani output
    combined_path = Path(args.combined_output)
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    with combined_path.open("w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    # Sažetak
    print("\n" + "=" * 50)
    print("SAŽETAK SCRAPING-A")
    print("=" * 50)
    by_portal = {}
    for a in all_articles:
        by_portal[a["portal"]] = by_portal.get(a["portal"], 0) + 1
    for portal, count in sorted(by_portal.items()):
        print(f"  {portal:15s}: {count} članaka")
    print(f"  {'UKUPNO':15s}: {len(all_articles)} članaka")
    print(f"\nSnimljeno u: {combined_path}")


if __name__ == "__main__":
    main()
