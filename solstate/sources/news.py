"""Ecosystem news from public RSS/Atom feeds.

The brief asks for ecosystem and community news alongside the metrics. Twitter
is not usable here -- its API needs a paid key, and scraping it is brittle and
against terms -- so this reads official project feeds instead, which are open,
stable and citable.

Parsed with xml.etree from the standard library; no feed parser dependency.
"""
import re
import time
import calendar
import email.utils
import xml.etree.ElementTree as ET
import concurrent.futures as cf

from solstate.http import request

# Keep this list to feeds that are small, public and authoritative. Helius'
# feed is ~6MB and is deliberately excluded: the cost is not worth the content.
FEEDS = [
    ("Solana", "https://solana.com/news/rss.xml"),
]

NS = {"atom": "http://www.w3.org/2005/Atom"}
_TAG = re.compile(r"<[^>]+>")


def _clean(s, limit=280):
    if not s:
        return ""
    s = _TAG.sub(" ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">")
          .replace("&#39;", "'").replace("&quot;", '"'))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def _parse_date(s):
    """RSS uses RFC-822, Atom uses ISO-8601. Accept either, return epoch."""
    if not s:
        return None
    try:
        return calendar.timegm(email.utils.parsedate(s))
    except Exception:
        pass
    try:
        s2 = s.strip().replace("Z", "+00:00")
        import datetime
        return datetime.datetime.fromisoformat(s2).timestamp()
    except Exception:
        return None


def _items(root, source):
    out = []
    # RSS 2.0
    for it in root.findall(".//item"):
        out.append({
            "source": source,
            "title": _clean(it.findtext("title"), 200),
            "link": (it.findtext("link") or "").strip(),
            "summary": _clean(it.findtext("description")),
            "ts": _parse_date(it.findtext("pubDate")),
        })
    # Atom
    for en in root.findall(".//atom:entry", NS):
        link = ""
        le = en.find("atom:link", NS)
        if le is not None:
            link = le.get("href") or ""
        out.append({
            "source": source,
            "title": _clean(en.findtext("atom:title", namespaces=NS), 200),
            "link": link,
            "summary": _clean(en.findtext("atom:summary", namespaces=NS)
                              or en.findtext("atom:content", namespaces=NS)),
            "ts": _parse_date(en.findtext("atom:updated", namespaces=NS)
                              or en.findtext("atom:published", namespaces=NS)),
        })
    return out


def fetch_one(feed):
    source, url = feed
    body = request(url, timeout=20, retries=2)
    root = ET.fromstring(body.encode("utf-8", "replace"))
    return _items(root, source)


def news(limit=8):
    items, errors = [], {}

    def run(f):
        try:
            return f[0], fetch_one(f), None
        except Exception as e:
            return f[0], [], f"{type(e).__name__}: {str(e)[:120]}"

    with cf.ThreadPoolExecutor(max_workers=max(1, len(FEEDS))) as ex:
        for src, got, err in ex.map(run, FEEDS):
            if err:
                errors[src] = err
            else:
                items.extend(got)

    items.sort(key=lambda i: i.get("ts") or 0, reverse=True)
    now = time.time()
    for i in items:
        if i.get("ts"):
            age_d = (now - i["ts"]) / 86400
            i["age"] = (f"{int(age_d)}d ago" if age_d >= 1
                        else f"{int(age_d*24)}h ago")
        else:
            i["age"] = ""
    return {"items": items[:limit], "count": len(items), "errors": errors}


if __name__ == "__main__":
    n = news()
    print(f"{n['count']} items, errors={n['errors']}\n")
    for i in n["items"]:
        print(f"  [{i['source']}] {i['age']:>8}  {i['title'][:70]}")
