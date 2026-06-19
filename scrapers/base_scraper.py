"""
Bazna klasa za scraper-e novinskih portala.
Sve portal-specifične klase nasljeđuju ovu klasu.
"""

import json
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@dataclass
class Article:
    """Strukturirani prikaz jednog scrapeovanog članka."""

    article_id: str
    portal: str
    url: str
    title: str
    date_published: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    lead: Optional[str] = None
    body: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self, min_body_length: int = 300) -> bool:
        """Provjera da li je članak iskoristiv (ima dovoljno teksta)."""
        return bool(self.title) and len(self.body) >= min_body_length


class BaseScraper(ABC):
    """
    Bazna klasa. Podklase trebaju definirati:
      - PORTAL_NAME (klasa atribut)
      - BASE_URL (klasa atribut)
      - get_article_urls() (metoda)
      - parse_article() (metoda — može koristiti default trafilatura ekstrakciju)
    """

    PORTAL_NAME: str = "base"
    BASE_URL: str = ""
    POLITICS_SECTION_URLS: list[str] = []
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "bs,hr,sr;q=0.9,en;q=0.5",
    }
    REQUEST_DELAY_RANGE = (1.5, 3.5)  # poštovanje servera
    REQUEST_TIMEOUT = 20

    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.logger = logging.getLogger(self.PORTAL_NAME)

    def fetch(self, url: str) -> Optional[str]:
        """Skida HTML stranicu uz delay i error handling."""
        try:
            time.sleep(random.uniform(*self.REQUEST_DELAY_RANGE))
            response = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()

            # Robusno otkrivanje enkoding-a:
            # - Ako server eksplicitno deklariše charset, vjeruj mu
            # - Ako kaže ISO-8859-1 (requests default), vjerovatno je pogrešno - probaj
            #   apparent_encoding koji analizira sadržaj
            # - Kao zadnja opcija forsiraj UTF-8 (99% news sajtova)
            content_type = response.headers.get("Content-Type", "").lower()
            declared_charset = "charset=" in content_type
            current_enc = (response.encoding or "").lower()

            if not declared_charset or current_enc in ("iso-8859-1", "latin-1", "ascii"):
                detected = (response.apparent_encoding or "").lower()
                if detected and detected not in ("ascii", "iso-8859-1"):
                    response.encoding = detected
                else:
                    response.encoding = "utf-8"

            return response.text
        except requests.RequestException as exc:
            self.logger.warning("Failed to fetch %s: %s", url, exc)
            return None

    def extract_with_trafilatura(self, html: str, url: str) -> dict:
        """
        Generička ekstrakcija članka pomoću trafilatura biblioteke.
        Robusna za većinu novinskih portala.
        """
        extracted = trafilatura.extract(
            html,
            url=url,
            output_format="json",
            with_metadata=True,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )
        if extracted:
            return json.loads(extracted)
        return {}

    def make_article_id(self, url: str) -> str:
        """Pravi ID iz URL-a — koristan za deduplikaciju."""
        path = urlparse(url).path.strip("/").replace("/", "_")
        return f"{self.PORTAL_NAME}_{path[-100:]}"

    # Override-aj u podklasi ako koristiš drugu strategiju
    SITEMAP_URL_PATTERN: str = ""
    MAX_AGE_DAYS: int = 365

    def get_article_urls_from_sitemap(self, max_urls: int) -> list[str]:
        """Default: traži URL-ove preko sitemap.xml."""
        from scrapers.sitemap_helper import discover_article_urls
        return discover_article_urls(
            domain=self.BASE_URL,
            session=self.session,
            url_pattern=self.SITEMAP_URL_PATTERN or None,
            max_age_days=self.MAX_AGE_DAYS,
            max_urls=max_urls,
        )

    @abstractmethod
    def get_article_urls(self, max_urls: int) -> list[str]:
        """
        Vraća listu URL-ova političkih članaka.
        Svaki portal mora implementirati svoju logiku
        (listing strana, paginacija, sitemap, RSS...).
        """
        ...

    def parse_article(self, url: str) -> Optional[Article]:
        """
        Default implementacija — koristi trafilatura.
        Portali mogu nadjačati za bolju ekstrakciju.
        """
        html = self.fetch(url)
        if not html:
            return None

        data = self.extract_with_trafilatura(html, url)
        if not data:
            self.logger.warning("Trafilatura nije izvukla sadržaj iz %s", url)
            return None

        article = Article(
            article_id=self.make_article_id(url),
            portal=self.PORTAL_NAME,
            url=url,
            title=data.get("title", ""),
            date_published=data.get("date"),
            author=data.get("author"),
            category=data.get("categories"),
            body=data.get("text", ""),
        )

        # Lead = prva 1-2 paragrafa
        paragraphs = article.body.split("\n\n")
        if paragraphs:
            article.lead = paragraphs[0][:500]

        return article

    def run(self, max_articles: int = 100) -> list[Article]:
        """Glavni entry-point: skida URL-ove pa parsira članke."""
        self.logger.info("Krećem sa scraping-om za %s", self.PORTAL_NAME)

        urls = self.get_article_urls(max_urls=max_articles * 2)
        self.logger.info("Pronađeno %d URL-ova", len(urls))

        articles: list[Article] = []
        seen_ids: set[str] = set()

        for i, url in enumerate(urls):
            if len(articles) >= max_articles:
                break

            self.logger.info("[%d/%d] %s", i + 1, len(urls), url)
            article = self.parse_article(url)

            if article is None:
                continue
            if article.article_id in seen_ids:
                continue
            if not article.is_valid():
                self.logger.info("  -> preskačem (prekratak ili nepotpun)")
                continue

            articles.append(article)
            seen_ids.add(article.article_id)

        self.logger.info("Završeno: %d validnih članaka", len(articles))
        self.save(articles)
        return articles

    def save(self, articles: list[Article]) -> Path:
        """Snima članke u JSON fajl."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{self.PORTAL_NAME}_{timestamp}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                [a.to_dict() for a in articles],
                f,
                ensure_ascii=False,
                indent=2,
            )
        self.logger.info("Snimljeno u %s", output_path)
        return output_path

    @staticmethod
    def extract_links_from_listing(
        html: str, base_url: str, link_pattern: str = ""
    ) -> list[str]:
        """Pomoćna metoda za izvlačenje linkova sa listing stranice."""
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(base_url, href)
            if link_pattern and link_pattern not in absolute:
                continue
            if absolute not in links:
                links.append(absolute)
        return links
