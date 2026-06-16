"""
Scraper za Večernji list BiH — koristi RSS feed.
"""

import argparse

from scrapers.base_scraper import BaseScraper
from scrapers.rss_helper import fetch_multiple_rss


class VecernjiScraper(BaseScraper):
    PORTAL_NAME = "vecernji"
    BASE_URL = "https://www.vecernji.ba"
    SITEMAP_URL_PATTERN = r"vecernji\.ba/[\w\-/]+-\d{6,}"

    RSS_FEEDS = [
        "https://www.vecernji.ba/feeds/latest",  # opcija ako postoji
        "https://www.vecernji.ba/feed",
        "https://www.vecernji.ba/rss",
        "https://www.vecernji.ba/vijesti/feed",
        "https://www.vecernji.ba/vijesti/rss",
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
    VecernjiScraper(output_dir=args.output_dir).run(max_articles=args.num_articles)


if __name__ == "__main__":
    main()
