"""
Scraper za Avaz.ba.

Avaz drži mjesečne sitemap-ove na:
  https://avaz.ba/sitemap-server.xml/currentMonth.xml
  https://avaz.ba/sitemap-server.xml/YYYY-M.xml
"""

import argparse
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

from scrapers.base_scraper import BaseScraper
from scrapers.sitemap_helper import parse_sitemap_urls


class AvazScraper(BaseScraper):
    PORTAL_NAME = "avaz"
    BASE_URL = "https://avaz.ba"
    SITEMAP_URL_PATTERN = r"avaz\.ba/(vijesti|teme)/[\w\-/]+/\d+/"
    MAX_AGE_DAYS = 180

    def get_article_urls(self, max_urls: int) -> list[str]:
        # Konstruiši URL-ove za zadnja 3 mjeseca
        sitemap_urls = ["https://avaz.ba/sitemap-server.xml/currentMonth.xml"]
        today = datetime.utcnow()
        for i in range(1, 4):
            d = today - relativedelta(months=i)
            sitemap_urls.append(f"https://avaz.ba/sitemap-server.xml/{d.year}-{d.month}.xml")

        pattern = re.compile(self.SITEMAP_URL_PATTERN)
        urls: list[str] = []
        for sm_url in sitemap_urls:
            self.logger.info("Avaz sitemap: %s", sm_url)
            sub = parse_sitemap_urls(
                sm_url, self.session, pattern,
                self.MAX_AGE_DAYS, max_urls - len(urls),
            )
            urls.extend(u for u in sub if u not in urls)
            if len(urls) >= max_urls:
                break
        return urls[:max_urls]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-articles", type=int, default=100)
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()
    AvazScraper(output_dir=args.output_dir).run(max_articles=args.num_articles)


if __name__ == "__main__":
    main()
