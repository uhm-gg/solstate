"""Minimal HTTP client built on the standard library only.

The brief prefers solutions with no external dependencies beyond the Python
standard library, so this replaces `requests` outright. It handles the three
things `requests` was actually doing for us: gzip decoding, JSON round-trips,
and retry with backoff.

Nothing here is imported from a third-party package, so `pip install` is never
required to run this tool.
"""
import gzip
import json
import time
import urllib.error
import urllib.request
import zlib

USER_AGENT = "solstate/1.0 (+stdlib-only)"
DEFAULT_TIMEOUT = 30
RETRIES = 3
BACKOFF = 1.6


class HttpError(RuntimeError):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


def _decode(resp):
    raw = resp.read()
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        raw = gzip.decompress(raw)
    elif enc == "deflate":
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def request(url, data=None, headers=None, timeout=DEFAULT_TIMEOUT,
            retries=RETRIES, method=None):
    """Fetch a URL, retrying transient failures. Returns the body as text."""
    hdrs = {"User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate"}
    if headers:
        hdrs.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _decode(resp)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = _decode(e)[:200]
            except Exception:
                pass
            last = HttpError(f"HTTP {e.code} for {url} {detail}", e.code)
            # Client errors other than rate-limiting will not fix themselves.
            if e.code not in (408, 425, 429, 500, 502, 503, 504):
                raise last
        except Exception as e:
            last = HttpError(f"{type(e).__name__}: {e} for {url}")
        if attempt < retries - 1:
            time.sleep(BACKOFF ** attempt)
    raise last


def get_json(url, **kw):
    return json.loads(request(url, **kw))


def post_json(url, payload, **kw):
    return json.loads(request(url, data=payload, **kw))
