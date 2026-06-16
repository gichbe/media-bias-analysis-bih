"""
Scraper za Nezavisne novine — koristi RSS jer nemaju sitemap.
"""

import argparse

from scrapers.base_scraper import BaseScraper
from scrapers.rss_helper import fetch_multiple_rss


class NezavisneScraper(BaseScraper):
    PORTAL_NAME = "nezavisne"
    BASE_URL = "https://www.nezavisne.com"
    SITEMAP_URL_PATTERN = r"nezavisne\.com/novosti/[\w\-]+/[\w\-%]+/\d+"

    # Probamo glavni feed i kategorije
    RSS_FEEDS = [
        "https://www.nezavisne.com/rss",
        "https://www.nezavisne.com/rss/novosti",
        "https://www.nezavisne.com/rss/novosti/bih",
        "https://www.nezavisne.com/rss/novosti/politika",
    ]

    def get_article_urls(self, max_urls: int) -> list[str]:
        return fetch_multiple_rss(
            self.RSS_FEEDS, self.session,
            url_pattern=self.SITEMAP_URL_PATTERN,
            max_total=max_urls,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-articles", type=int, default=100)
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()
    NezavisneScraper(output_dir=args.output_dir).run(max_articles=args.num_articles)


if __name__ == "__main__":
    main()
