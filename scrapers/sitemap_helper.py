"""
Sitemap-based discovery članaka.

Većina novinskih portala ima sitemap.xml (ili sitemap_news.xml) gdje
listaju sve svoje članke. To je daleko pouzdaniji način da nađemo URL-ove
nego HTML listing stranice + paginacija.

Reference: https://www.sitemaps.org/protocol.html
"""

import gzip
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger("sitemap")

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

DEFAULT_SITEMAP_PATHS = [
    "/sitemap_news.xml",
    "/news-sitemap.xml",
    "/sitemap-news.xml",
    "/news.xml",
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
]


def find_sitemap(domain: str, session: requests.Session) -> Optional[str]:
    """Pokušaj pronaći sitemap URL preko robots.txt ili standardnih lokacija."""
    domain = domain.rstrip("/")

    # 1. Provjeri robots.txt
    try:
        r = session.get(f"{domain}/robots.txt", timeout=10)
        if r.ok:
            sitemaps = []
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sm_url = line.split(":", 1)[1].strip()
                    sitemaps.append(sm_url)
            if sitemaps:
                # Preferira "news" sitemap ako postoji
                for sm in sitemaps:
                    if "news" in sm.lower():
                        return sm
                return sitemaps[0]
    except requests.RequestException:
        pass

    # 2. Probaj standardne lokacije
    for path in DEFAULT_SITEMAP_PATHS:
        url = domain + path
        try:
            r = session.head(url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                return r.url
        except requests.RequestException:
            continue
    return None


def fetch_sitemap_xml(url: str, session: requests.Session) -> Optional[str]:
    """Skini sitemap XML, automatski dekompresuje .gz."""
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        content = r.content
        if url.endswith(".gz") or r.headers.get("Content-Type", "").startswith("application/x-gzip"):
            content = gzip.decompress(content)
        return content.decode("utf-8", errors="ignore")
    except (requests.RequestException, gzip.BadGzipFile) as e:
        logger.warning("Sitemap fetch fail %s: %s", url, e)
        return None


def parse_sitemap_urls(
    sitemap_url: str,
    session: requests.Session,
    url_pattern: Optional[re.Pattern] = None,
    max_age_days: int = 365,
    max_urls: int = 500,
    _depth: int = 0,
) -> list[str]:
    """
    Vrati listu URL-ova iz sitemap-a, sa filtriranjem po regex-u i datumu.
    Automatski rekurzivno prati sitemap-indexe.
    """
    if _depth > 3:
        return []

    content = fetch_sitemap_xml(sitemap_url, session)
    if not content:
        return []

    try:
        # Neki portali stavljaju BOM ili nepotrebne prefikse
        content = content.lstrip("\ufeff").strip()
        root = ET.fromstring(content)
    except ET.ParseError as e:
        logger.error("XML parse fail za %s: %s", sitemap_url, e)
        return []

    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    urls: list[str] = []

    # Slučaj 1: sitemap index (lista drugih sitemap-ova)
    child_sitemaps = root.findall("sm:sitemap", NS)
    if child_sitemaps:
        logger.info("Sitemap index sa %d podsitemap-ova", len(child_sitemaps))
        for sm in child_sitemaps[:30]:
            loc = sm.find("sm:loc", NS)
            if loc is None or not loc.text:
                continue
            child_url = loc.text.strip()

            # Lagano filtriranje — preskoči samo očito ne-news child sitemape
            lower = child_url.lower()
            if any(skip in lower for skip in ["image_sitemap", "video_sitemap", "videos_"]):
                continue

            logger.info("  → pratim child sitemap: %s", child_url)
            sub_urls = parse_sitemap_urls(
                child_url, session, url_pattern, max_age_days,
                max_urls - len(urls), _depth + 1,
            )
            urls.extend(sub_urls)
            if len(urls) >= max_urls:
                break
        return urls[:max_urls]

    # Slučaj 2: obični sitemap sa URL-ovima
    for url_elem in root.findall("sm:url", NS):
        loc = url_elem.find("sm:loc", NS)
        if loc is None or not loc.text:
            continue
        url = loc.text.strip()

        if url_pattern and not url_pattern.search(url):
            continue

        # Filter po datumu ako postoji <lastmod> ili <news:publication_date>
        date_ok = True
        lastmod = url_elem.find("sm:lastmod", NS)
        if lastmod is not None and lastmod.text:
            try:
                # Obično ISO format: 2026-06-09 ili 2026-06-09T12:00:00+00:00
                date_str = lastmod.text[:10]
                last_date = datetime.strptime(date_str, "%Y-%m-%d")
                if last_date < cutoff:
                    date_ok = False
            except ValueError:
                pass

        if date_ok:
            urls.append(url)
        if len(urls) >= max_urls:
            break

    return urls


def discover_article_urls(
    domain: str,
    session: requests.Session,
    url_pattern: Optional[str] = None,
    max_age_days: int = 365,
    max_urls: int = 500,
) -> list[str]:
    """
    Glavna funkcija — vrati URL-ove članaka za dati domain.

    Args:
        domain: npr. "https://www.klix.ba"
        url_pattern: regex koji URL mora zadovoljiti (npr. r"/vijesti/(bih|politika)/")
        max_age_days: koliko unazad članci mogu biti
        max_urls: limit broja URL-ova
    """
    sitemap_url = find_sitemap(domain, session)
    if not sitemap_url:
        logger.warning("Nije pronađen sitemap za %s", domain)
        return []

    logger.info("Sitemap za %s: %s", domain, sitemap_url)
    pattern = re.compile(url_pattern) if url_pattern else None
    urls = parse_sitemap_urls(sitemap_url, session, pattern, max_age_days, max_urls)
    logger.info("Pronađeno %d URL-ova iz sitemap-a", len(urls))
    return urls
