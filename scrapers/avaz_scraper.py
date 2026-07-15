"""
Scraper za Avaz.ba - koristi RSS feed jer im sitemap nije pouzdan.
"""

import argparse
from scrapers.base_scraper import BaseScraper
from scrapers.rss_helper import fetch_multiple_rss


class AvazScraper(BaseScraper):
    PORTAL_NAME = "avaz"
    BASE_URL = "https://avaz.ba"
    # Format URL-ova: avaz.ba/vijesti/bih/1048252/slug ili teme/...
    SITEMAP_URL_PATTERN = r"avaz\.ba/(vijesti|teme|biznis|sport)/[\w\-/]+/\d+/"

    RSS_FEEDS = [
        "https://avaz.ba/rss",
        "https://avaz.ba/feed",
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
    AvazScraper(output_dir=args.output_dir).run(max_articles=args.num_articles)


if __name__ == "__main__":
    main()
