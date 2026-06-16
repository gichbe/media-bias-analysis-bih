"""
Scraper za Klix.ba — kombinuje sitemap.xml i RSS feed.
"""

import argparse

from scrapers.base_scraper import BaseScraper
from scrapers.rss_helper import fetch_rss_urls


class KlixScraper(BaseScraper):
    PORTAL_NAME = "klix"
    BASE_URL = "https://www.klix.ba"
    SITEMAP_URL_PATTERN = r"klix\.ba/vijesti/(bih|politika|regija|svijet)/[\w\-]+/\d{6,}"
    MAX_AGE_DAYS = 180
    RSS_FEEDS = [
        "https://www.klix.ba/rss",
    ]

    def get_article_urls(self, max_urls: int) -> list[str]:
        # Prvo sitemap (potencijalno daje hiljade)
        urls = self.get_article_urls_from_sitemap(max_urls)

        # Dopuni iz RSS-a (najsvježiji članci)
        if len(urls) < max_urls:
            import re
            pattern = re.compile(self.SITEMAP_URL_PATTERN)
            for rss in self.RSS_FEEDS:
                rss_urls = fetch_rss_urls(rss, self.session, max_urls=max_urls)
                for u in rss_urls:
                    if pattern.search(u) and u not in urls:
                        urls.append(u)
                    if len(urls) >= max_urls:
                        break
        return urls[:max_urls]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-articles", type=int, default=100)
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()
    KlixScraper(output_dir=args.output_dir).run(max_articles=args.num_articles)


if __name__ == "__main__":
    main()
