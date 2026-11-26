"""HTTP fetching helpers for VIKTOR Audit. Standard library only.

No API keys, no signup, no server. Every fetch is a plain public GET.
A failed fetch is never silently treated as a negative result — the caller
decides whether it means fail or not verified.
"""

from __future__ import annotations

import gzip
import html as html_lib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (compatible; VIKTOR-Audit/0.1; +https://viktorcompany.com/audit)"
)

DEFAULT_TIMEOUT = 12


class FetchResult:
    def __init__(self, url, status, text, ttfb_ms, size_bytes):
        self.url = url
        self.status = status
        self.text = text or ""
        self.ttfb_ms = ttfb_ms
        self.size_bytes = size_bytes

    @property
    def ok(self):
        return self.status is not None and 200 <= self.status < 400


def fetch(url, timeout=DEFAULT_TIMEOUT):
    """GET a URL. Returns FetchResult, or None when unreachable.

    HTTP error statuses (404 etc.) still return a FetchResult with that
    status — a 404 is information, not a network failure.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"},
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ttfb_ms = int((time.monotonic() - start) * 1000)
            encoding = resp.headers.get("Content-Encoding", "")
            if "gzip" in encoding:
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                text = raw.decode(charset, errors="replace")
            except Exception:
                text = raw.decode("utf-8", errors="replace")
            return FetchResult(url, resp.status, text, ttfb_ms, len(raw))
    except urllib.error.HTTPError as e:
        ttfb_ms = int((time.monotonic() - start) * 1000)
        return FetchResult(url, e.code, "", ttfb_ms, 0)
    except Exception:
        return None


def get(url, timeout=DEFAULT_TIMEOUT):
    """Fetch and return text, or None."""
    res = fetch(url, timeout=timeout)
    if res is None or not res.ok:
        return None
    return res.text


def strip_tags(html_text):
    """Best-effort visible text from HTML."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_text,
                  flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_json_ld(html_text):
    """Return a list of parsed JSON-LD objects found in the page.

    Recurses into nested dicts/lists (e.g. Offer items inside an
    OfferCatalog's itemListElement) so nested @type objects are seen.
    """
    found = []

    def walk(node):
        if isinstance(node, dict):
            if "@type" in node:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html_text or ""):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue
        walk(data)
    return found


def json_ld_types(objects):
    """Set of @type values across JSON-LD objects (handles lists)."""
    types = set()
    for obj in objects:
        t = obj.get("@type")
        if isinstance(t, str):
            types.add(t)
        elif isinstance(t, list):
            types.update(x for x in t if isinstance(x, str))
    return types


def extract_links(html_text, base_url):
    """Absolute http(s) links found in the page, in document order."""
    links = []
    seen = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', html_text or "", re.IGNORECASE):
        href = href.strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        abs_url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        abs_url = abs_url.split("#")[0]
        if abs_url not in seen:
            seen.add(abs_url)
            links.append(abs_url)
    return links


def same_host(url, host):
    try:
        return urllib.parse.urlparse(url).netloc.lower().lstrip("www.") == host
    except Exception:
        return False


def resolve_name_to_url(name):
    """Resolve a bare business name to a homepage URL via DuckDuckGo HTML.

    Returns a URL string, or None when nothing usable is found. The caller
    must ask the user for a full URL in that case — never guess a domain.
    """
    query = urllib.parse.quote_plus(name)
    search_url = "https://html.duckduckgo.com/html/?q=" + query
    text = get(search_url)
    if not text:
        return None
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())
    for href in re.findall(r'result__a[^>]+href=["\']([^"\']+)["\']', text):
        if "duckduckgo.com" in href:
            continue
        parsed = urllib.parse.urlparse(href)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        domain = parsed.netloc.lower().lstrip("www.")
        domain_slug = re.sub(r"[^a-z0-9]+", "", domain.split(".")[0])
        if slug and (slug in domain_slug or domain_slug in slug):
            return href
    # Fall back to the first non-DDG result.
    for href in re.findall(r'result__a[^>]+href=["\']([^"\']+)["\']', text):
        if "duckduckgo.com" not in href:
            return href
    return None


def normalize_target(target):
    """Turn user input into a homepage URL, or None when it cannot resolve."""
    target = (target or "").strip()
    if not target:
        return None
    if "://" not in target:
        if "." in target and " " not in target:
            target = "https://" + target
        else:
            return resolve_name_to_url(target)
    return target
