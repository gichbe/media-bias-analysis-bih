"""Scraper za N1 BiH — koristi sitemap."""

import argparse
from scrapers.base_scraper import BaseScraper


class N1Scraper(BaseScraper):
    PORTAL_NAME = "n1"
    BASE_URL = "https://n1info.ba"  # N1 BiH se preselio na n1info.ba
    # N1 ima dosta sekcija, fokusiramo se na vijesti i biznis
    SITEMAP_URL_PATTERN = r"n1info\.ba/(vijesti|biznis|region)/[\w\-%]+/?$"
    MAX_AGE_DAYS = 180

    def get_article_urls(self, max_urls: int) -> list[str]:
        return self.get_article_urls_from_sitemap(max_urls)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-articles", type=int, default=100)
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()
    N1Scraper(output_dir=args.output_dir).run(max_articles=args.num_articles)


if __name__ == "__main__":
    main()
