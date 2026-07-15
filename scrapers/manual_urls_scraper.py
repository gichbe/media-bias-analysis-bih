"""
Pomocni scraper - obradi URL-ove iz tekstualnog fajla.

Korisno kad zelis ubaciti rucno odabrane clanke (npr. iz arhive
portala koja nema sitemap/RSS).

Pokretanje:
    python -m scrapers.manual_urls_scraper data/raw/manual_urls.txt
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from scrapers.base_scraper import Article, BaseScraper


class ManualScraper(BaseScraper):
    PORTAL_NAME = "manual"
    BASE_URL = ""

    def __init__(self, portal_override=None, **kwargs):
        super().__init__(**kwargs)
        self.portal_override = portal_override

    def get_article_urls(self, max_urls):
        return []  # ne koristi se

    def detect_portal(self, url):
        """Pogodi portal iz URL-a."""
        host = urlparse(url).netloc.lower().replace("www.", "")
        if "klix" in host: return "klix"
        if "avaz" in host: return "avaz"
        if "nezavisne" in host: return "nezavisne"
        if "vecernji" in host: return "vecernji"
        if "n1info" in host: return "n1"
        return "unknown"

    def scrape_urls(self, urls):
        # Dedup URL-ova (sacuvaj redoslijed)
        seen = set()
        unique_urls = []
        for url in urls:
            normalized = url.rstrip("/")
            if normalized not in seen:
                seen.add(normalized)
                unique_urls.append(url)
        if len(unique_urls) < len(urls):
            print(f"  Uklonjeno {len(urls) - len(unique_urls)} duplikata")
        urls = unique_urls

        # Grupiraj po portalu za bolji output
        by_portal = {}
        for url in urls:
            portal = self.detect_portal(url)
            by_portal.setdefault(portal, []).append(url)

        base_logger = logging.getLogger("manual_scraper")
        summary = {}

        for portal, portal_urls in by_portal.items():
            articles = []
            self.PORTAL_NAME = portal  # set za parse_article
            plog = logging.getLogger(f"manual_scraper.{portal}")
            plog.info("Obradjujem %d URL-ova za %s", len(portal_urls), portal)

            for i, url in enumerate(portal_urls):
                plog.info("[%d/%d] %s", i+1, len(portal_urls), url)
                article = self.parse_article(url)
                if article and article.is_valid():
                    articles.append(article)

            summary[portal] = {"total": len(portal_urls), "valid": len(articles)}

            if articles:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = self.output_dir / f"{portal}_manual_{timestamp}.json"
                with path.open("w", encoding="utf-8") as f:
                    json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)
                plog.info("Snimljeno %d clanaka u %s", len(articles), path)

        # Sazetak
        print("\n" + "=" * 50)
        print("SAZETAK MANUAL SCRAPE")
        print("=" * 50)
        total_urls = total_valid = 0
        for portal, counts in sorted(summary.items()):
            print(f"  {portal:15s}: {counts['valid']}/{counts['total']} validnih")
            total_urls += counts["total"]
            total_valid += counts["valid"]
        print(f"  {'UKUPNO':15s}: {total_valid}/{total_urls} validnih")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("urls_file", help="Tekstualni fajl sa URL-ovima (jedan po liniji)")
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()

    urls = []
    with open(args.urls_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and line.startswith("http"):
                urls.append(line)

    print(f"Ucitano {len(urls)} URL-ova")
    if not urls:
        return

    scraper = ManualScraper(output_dir=args.output_dir)
    scraper.scrape_urls(urls)


if __name__ == "__main__":
    main()
