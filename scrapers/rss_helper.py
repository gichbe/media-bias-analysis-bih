"""
RSS / Atom feed parser — alternativa sitemap-u za portale koji ga nemaju.

RSS feedovi obično daju 20-100 najnovijih članaka. Ako treba više,
moramo kombinovati više različitih feed-ova (po kategoriji).
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional

import requests

logger = logging.getLogger("rss")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_rss_urls(
    rss_url: str,
    session: requests.Session,
    url_pattern: Optional[str] = None,
    max_urls: int = 200,
) -> list[str]:
    """
    Skini RSS feed i izvuci URL-ove članaka.
    Podržava i RSS 2.0 i Atom.
    """
    try:
        r = session.get(rss_url, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("RSS fetch fail %s: %s", rss_url, e)
        return []

    try:
        content = r.content.decode("utf-8", errors="ignore")
        content = content.lstrip("\ufeff").strip()
        root = ET.fromstring(content)
    except ET.ParseError as e:
        logger.warning("RSS parse fail %s: %s", rss_url, e)
        return []

    pattern = re.compile(url_pattern) if url_pattern else None
    urls: list[str] = []

    # RSS 2.0: <rss><channel><item><link>...</link>
    for item in root.iter("item"):
        link_elem = item.find("link")
        if link_elem is not None and link_elem.text:
            url = link_elem.text.strip()
            if not pattern or pattern.search(url):
                if url not in urls:
                    urls.append(url)
        if len(urls) >= max_urls:
            break

    # Atom: <feed><entry><link href="..."/>
    if not urls:
        for entry in root.findall("atom:entry", ATOM_NS):
            link_elem = entry.find("atom:link", ATOM_NS)
            if link_elem is not None:
                url = link_elem.get("href", "").strip()
                if url and (not pattern or pattern.search(url)):
                    if url not in urls:
                        urls.append(url)
            if len(urls) >= max_urls:
                break

    logger.info("RSS %s → %d URL-ova", rss_url, len(urls))
    return urls


def fetch_multiple_rss(
    rss_urls: list[str],
    session: requests.Session,
    url_pattern: Optional[str] = None,
    max_total: int = 500,
) -> list[str]:
    """Spaja URL-ove iz više RSS feed-ova."""
    all_urls: list[str] = []
    seen: set[str] = set()
    for rss_url in rss_urls:
        urls = fetch_rss_urls(rss_url, session, url_pattern, max_total - len(all_urls))
        for u in urls:
            if u not in seen:
                seen.add(u)
                all_urls.append(u)
        if len(all_urls) >= max_total:
            break
    return all_urls
