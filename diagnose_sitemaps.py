"""
Diagnostička skripta — provjerava sitemap dostupnost za svaki portal.

Pokretanje:
    python diagnose_sitemaps.py

"""

import gzip
import xml.etree.ElementTree as ET

import requests

PORTALS = [
    ("klix",      "https://www.klix.ba"),
    ("avaz",      "https://avaz.ba"),
    ("nezavisne", "https://www.nezavisne.com"),
    ("vecernji",  "https://www.vecernji.ba"),
]

SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap_news.xml",
    "/news-sitemap.xml",
    "/sitemap-news.xml",
    "/sitemap_1.xml",
    "/sitemap/sitemap.xml",
    "/sitemap/sitemap_news.xml",
    "/news.xml",
    "/feed",
    "/rss",
    "/rss.xml",
]

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}


def probe(url: str) -> dict:
    """Probaj URL i vrati osnovne info."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return {
            "status": r.status_code,
            "final_url": r.url,
            "content_type": r.headers.get("Content-Type", "")[:60],
            "size": len(r.content),
            "content": r.content,
        }
    except requests.RequestException as e:
        return {"status": "ERR", "error": str(e)[:100]}


def try_parse_xml(content: bytes) -> dict:
    """Probaj parsirati XML i izvuci osnovne info."""
    try:
        if content[:2] == b'\x1f\x8b':
            content = gzip.decompress(content)
        text = content.decode("utf-8", errors="ignore").lstrip("\ufeff").strip()
        root = ET.fromstring(text)

        # Brojiš child sitemap-ove
        child_sitemaps = root.findall("sm:sitemap", NS)
        urls = root.findall("sm:url", NS)

        # Uzmi prvih par primjera
        sample_children = []
        for sm in child_sitemaps[:5]:
            loc = sm.find("sm:loc", NS)
            if loc is not None:
                sample_children.append(loc.text)

        sample_urls = []
        for u in urls[:5]:
            loc = u.find("sm:loc", NS)
            if loc is not None:
                sample_urls.append(loc.text)

        return {
            "ok": True,
            "child_sitemaps": len(child_sitemaps),
            "urls": len(urls),
            "sample_children": sample_children,
            "sample_urls": sample_urls,
        }
    except ET.ParseError as e:
        return {"ok": False, "error": str(e)[:100]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}


def main():
    for portal, domain in PORTALS:
        print("\n" + "=" * 75)
        print(f"  PORTAL: {portal.upper()}  ({domain})")
        print("=" * 75)

        # 1. robots.txt
        print("\n--- robots.txt ---")
        r = probe(f"{domain}/robots.txt")
        if r.get("status") == 200:
            text = r["content"].decode("utf-8", errors="ignore")
            sitemap_lines = [
                line for line in text.splitlines()
                if line.lower().strip().startswith("sitemap:")
            ]
            if sitemap_lines:
                print("Sitemap linije iz robots.txt:")
                for line in sitemap_lines:
                    print(f"  {line}")
            else:
                print("Nema 'Sitemap:' linije u robots.txt")
        else:
            print(f"Status: {r.get('status')}")

        # 2. Pokušaj standardne putanje
        print("\n--- Probe sitemap putanja ---")
        for path in SITEMAP_PATHS:
            url = domain + path
            r = probe(url)
            status = r.get("status")
            if status == 200 and r.get("size", 0) > 200:
                ct = r.get("content_type", "")
                size_kb = r.get("size", 0) / 1024
                print(f"  [200] {url}  ({size_kb:.1f}KB, {ct})")

                # Pokušaj parsirati ako liči na XML
                if "xml" in ct.lower() or url.endswith(".xml"):
                    parsed = try_parse_xml(r["content"])
                    if parsed.get("ok"):
                        if parsed["child_sitemaps"]:
                            print(f"        SITEMAP_INDEX sa {parsed['child_sitemaps']} child sitemap-ova:")
                            for c in parsed["sample_children"]:
                                print(f"          → {c}")
                        if parsed["urls"]:
                            print(f"        DIREKTNI URL-ovi ({parsed['urls']}), prvih 5:")
                            for u in parsed["sample_urls"]:
                                print(f"          → {u}")
                    else:
                        print(f"        Parse fail: {parsed.get('error')}")
            elif status not in (404, "ERR"):
                print(f"  [{status}] {url}")


if __name__ == "__main__":
    main()
