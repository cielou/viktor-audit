"""The 18 checks. Group A: GEO (40 pts). Group B: Transparency (60 pts).

Discipline, inherited from the internal audit tool:
- The tool does arithmetic; a human judges. A check states what was
  measured, never "this agency is bad".
- Missing data is NOT VERIFIED: listed, never silently skipped, never
  replaced with a proxy, never treated as a pass or a fail.
- Ad Library empty, or a directory search that returns nothing, is NOT
  evidence of absence.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import fetch as fx

AI_BOTS = [
    "gptbot", "chatgpt-user", "oai-searchbot", "claudebot", "claude-web",
    "anthropic-ai", "perplexitybot", "perplexity-user", "ccbot",
    "cohere-ai", "meta-externalagent", "applebot-extended",
    "duckassistbot", "google-extended",
]

DIRECTORY_HOSTS = [
    "clutch.co", "designrush.com", "trustpilot.com", "g2.com",
    "capterra.com", "goodfirms.co", "sortlist.com", "google.com/maps",
    "g.page", "yelp.com", "bbb.org",
]

ROLE_KEYWORDS = [
    "founder", "co-founder", "ceo", "chief", "director", "manager",
    "lead", "head of", "strategist", "specialist", "president", "partner",
]

PRICE_RE = re.compile(
    r"(?:US\$|CA\$|C\$|A\$|\$|€|£)\s?\d[\d,]*(?:\.\d{2})?"
    r"|(?:from|starting at|starts at|à partir de|desde)\s*(?:US\$|CA\$|\$|€|£)",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|x\b|X\b)|(?:US\$|CA\$|\$|€|£)\s?\d[\d,]*")

ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[\w\s.'-]{2,40}?\b(?:St|Street|Ave|Avenue|Rd|Road|Blvd|"
    r"Boulevard|Dr|Drive|Lane|Ln|Way|Suite|Ste|Floor|Fl)\b",
    re.IGNORECASE,
)

# check id -> (group, points)
POINTS = {
    "A1": ("A", 6), "A2": ("A", 5), "A3": ("A", 5), "A4": ("A", 4),
    "A5": ("A", 4), "A6": ("A", 8), "A7": ("A", 4), "A8": ("A", 4),
    "B1": ("B", 8), "B2": ("B", 8), "B3": ("B", 6), "B4": ("B", 4),
    "B5": ("B", 8), "B6": ("B", 8), "B7": ("B", 6), "B8": ("B", 6),
    "B9": ("B", 3), "B10": ("B", 3),
}

PAGE_HINTS = {
    "pricing": ["pricing", "price", "packages", "plans"],
    "services": ["services", "service", "solutions", "what-we-do", "audit", "geo"],
    "work": ["work", "case-studies", "case-study", "clients", "results", "portfolio"],
    "team": ["team", "about", "about-us", "people"],
    "contact": ["contact", "contact-us"],
    "terms": ["terms", "terms-of-service", "terms-and-conditions", "legal", "privacy"],
    "blog": ["blog", "news", "insights", "journal"],
}


class CheckResult:
    def __init__(self, cid, status, evidence):
        self.id = cid
        self.group, self.points = POINTS[cid]
        self.status = status  # pass | fail | not_verified
        self.evidence = evidence

    @property
    def earned(self):
        return self.points if self.status == "pass" else 0


class SiteData:
    """Everything fetched once, then read by all checks."""

    def __init__(self, url):
        self.base_url = url
        parsed = urllib.parse.urlparse(url)
        self.host = parsed.netloc.lower()
        self.root = f"{parsed.scheme}://{parsed.netloc}"
        self.pages = {}       # url -> text (visible text)
        self.html = {}        # url -> raw html
        self.home = None      # FetchResult for the homepage
        self.robots = None
        self.llms = None
        self.sitemap = None
        self.json_ld = []

    def fetch_page(self, url):
        res = fx.fetch(url)
        if res is not None and res.ok:
            self.pages[url] = fx.strip_tags(res.text)
            self.html[url] = res.text
            return res
        return None

    def discover(self, max_extra_pages=14):
        """Fetch homepage, robots, llms, sitemap, then candidate pages."""
        self.home = self.fetch_page(self.base_url)
        if self.home is None:
            return False
        self.html[self.base_url] = self.home.text
        self.pages[self.base_url] = fx.strip_tags(self.home.text)
        self.json_ld = fx.extract_json_ld(self.home.text)
        self.robots = fx.fetch(self.root + "/robots.txt")
        self.llms = fx.fetch(self.root + "/llms.txt")
        self.sitemap = fx.fetch(self.root + "/sitemap.xml")

        links = fx.extract_links(self.home.text, self.base_url)
        wanted = []
        per_kind = 2
        for kind, hints in PAGE_HINTS.items():
            taken = 0
            for link in links:
                if taken >= per_kind or len(wanted) >= max_extra_pages:
                    break
                if not fx.same_host(link, self.host.lstrip("www.")):
                    continue
                path = urllib.parse.urlparse(link).path.lower()
                if kind == "blog" and path.rstrip("/") != "/blog":
                    continue
                if any(h in path for h in hints) and link not in wanted:
                    wanted.append(link)
                    taken += 1
        for link in wanted:
            self.fetch_page(link)
        # Schema lives on inner pages too (/audit/ Service, /geo/ FAQ).
        # Collect JSON-LD across everything fetched, not just the homepage.
        for url, html in self.html.items():
            if url == self.base_url:
                continue
            self.json_ld.extend(fx.extract_json_ld(html))
        return True

    def pages_of_kind(self, kind):
        hints = PAGE_HINTS[kind]
        out = []
        for url, text in self.pages.items():
            path = urllib.parse.urlparse(url).path.lower()
            if kind != "blog" and path.startswith("/blog/"):
                continue
            if any(h in path for h in hints):
                out.append((url, text))
        return out

    def all_text(self):
        return "\n".join(self.pages.values())

    def homepage_links(self):
        return fx.extract_links(self.home.text if self.home else "", self.base_url)


def _robots_disallows_ai(robots_text):
    """True when a user-agent block disallows a known AI crawler."""
    current_agents = []
    disallowed = set()
    for raw_line in (robots_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            current_agents = [value.lower()]
        elif key == "disallow" and value and value != "/":
            for agent in current_agents:
                if agent == "*":
                    continue
                disallowed.add(agent)
        elif key == "disallow" and value == "/":
            for agent in current_agents:
                disallowed.add(agent)
    return any(bot in disallowed for bot in AI_BOTS)


def _parse_lastmod(xml):
    dates = []
    for m in re.findall(r"<lastmod>([^<]+)</lastmod>", xml or "", re.IGNORECASE):
        try:
            dates.append(datetime.fromisoformat(m.strip().replace("Z", "+00:00")))
        except ValueError:
            continue
    return dates


# ---------------------------------------------------------------- checks

def check_a1(site):
    res = site.llms
    if res is None:
        return CheckResult("A1", "not_verified", "llms.txt fetch failed (network error)")
    if res.status == 404:
        return CheckResult("A1", "fail", "GET /llms.txt -> 404")
    if not res.ok:
        return CheckResult("A1", "not_verified", f"GET /llms.txt -> HTTP {res.status}")
    links = len(re.findall(r"https?://", res.text))
    if len(res.text.strip()) < 100:
        return CheckResult("A1", "fail", "llms.txt exists but is nearly empty")
    return CheckResult("A1", "pass", f"llms.txt present ({len(res.text)} chars, {links} links)")


def check_a2(site):
    res = site.robots
    if res is None:
        return CheckResult("A2", "not_verified", "robots.txt fetch failed (network error)")
    if res.status == 404:
        return CheckResult("A2", "pass", "No robots.txt — AI crawlers allowed by default")
    if not res.ok:
        return CheckResult("A2", "not_verified", f"GET /robots.txt -> HTTP {res.status}")
    if _robots_disallows_ai(res.text):
        return CheckResult("A2", "fail", "robots.txt disallows one or more AI crawlers")
    return CheckResult("A2", "pass", "robots.txt does not block AI crawlers")


def check_a3(site):
    types = fx.json_ld_types(site.json_ld)
    org_types = {"Organization", "LocalBusiness", "ProfessionalService",
                 "Corporation", "Brand", "EducationalOrganization"}
    if types & org_types:
        return CheckResult("A3", "pass", f"Organization schema present ({sorted(types & org_types)[0]})")
    if site.json_ld:
        return CheckResult("A3", "fail", "JSON-LD present but no Organization type")
    return CheckResult("A3", "fail", "No JSON-LD found on homepage")


def check_a4(site):
    types = fx.json_ld_types(site.json_ld)
    if "FAQPage" in types:
        return CheckResult("A4", "pass", "FAQPage schema present")
    return CheckResult("A4", "fail", "No FAQPage schema found")


def check_a5(site):
    for obj in site.json_ld:
        t = obj.get("@type")
        types = [t] if isinstance(t, str) else (t or [])
        if any(x in ("Service", "Offer", "Product") for x in types):
            if any(k in obj for k in ("price", "priceRange", "priceSpecification", "offers")):
                return CheckResult("A5", "pass", f"{types[0]} schema with price info")
    return CheckResult("A5", "fail", "No Service/Offer schema with price info")


def check_a6(site):
    return CheckResult(
        "A6", "not_verified",
        "CLI cannot ask an AI directly. Run with the skill: the agent asks "
        "ChatGPT / Perplexity whether this brand is cited for its category.",
    )


def check_a7(site):
    links = site.homepage_links()
    hits = sorted({u for u in links if any(d in u for d in DIRECTORY_HOSTS)})
    same_as = set()
    for obj in site.json_ld:
        sa = obj.get("sameAs")
        if isinstance(sa, str):
            same_as.add(sa)
        elif isinstance(sa, list):
            same_as.update(x for x in sa if isinstance(x, str))
    hits += sorted({u for u in same_as if any(d in u for d in DIRECTORY_HOSTS)})
    if hits:
        return CheckResult("A7", "pass", "Linked from: " + ", ".join(list(dict.fromkeys(hits))[:3]))
    return CheckResult(
        "A7", "not_verified",
        "No directory links found on the site. A listing may still exist — "
        "this check cannot prove absence.",
    )


def check_a8(site):
    res = site.sitemap
    if res is None:
        return CheckResult("A8", "not_verified", "sitemap.xml fetch failed (network error)")
    if res.status == 404:
        return CheckResult("A8", "not_verified", "No sitemap.xml found")
    if not res.ok:
        return CheckResult("A8", "not_verified", f"GET /sitemap.xml -> HTTP {res.status}")
    dates = _parse_lastmod(res.text)
    if not dates:
        return CheckResult("A8", "not_verified", "sitemap.xml has no lastmod dates")
    newest = max(dates)
    age = (datetime.now(timezone.utc) - newest).days
    if age <= 90:
        return CheckResult("A8", "pass", f"Newest sitemap entry {age} days ago")
    return CheckResult("A8", "fail", f"Newest sitemap entry {age} days ago (>90)")


def check_b1(site):
    candidates = site.pages_of_kind("pricing") + site.pages_of_kind("services")
    candidates.append((site.base_url, site.pages.get(site.base_url, "")))
    for url, text in candidates:
        if PRICE_RE.search(text or ""):
            return CheckResult("B1", "pass", f"Price found on {url}")
    return CheckResult("B1", "fail", "No price, range, or starting price found on pricing/services pages")


def check_b2(site):
    pages = site.pages_of_kind("work")
    if not pages:
        return CheckResult("B2", "fail", "No work / case-study / clients page found")
    for url, text in pages:
        if NUMBER_RE.search(text or ""):
            return CheckResult("B2", "pass", f"Case page with real numbers: {url}")
    return CheckResult("B2", "fail", "Case pages exist but show no real numbers")


def check_b3(site):
    pages = site.pages_of_kind("team")
    if not pages:
        return CheckResult("B3", "fail", "No team / about page found")
    for url, text in pages:
        lowered = (text or "").lower()
        found = {kw for kw in ROLE_KEYWORDS if kw in lowered}
        if len(found) >= 2:
            return CheckResult("B3", "pass", f"Team page names roles ({', '.join(sorted(found)[:4])}): {url}")
    return CheckResult("B3", "fail", "Team/about page exists but names no clear roles")


def check_b4(site):
    text = site.all_text()
    html_all = " ".join(site.html.values())
    if "tel:" in html_all or "mailto:" in html_all:
        return CheckResult("B4", "pass", "Phone link or email link present")
    if ADDRESS_RE.search(text):
        return CheckResult("B4", "pass", "Street address published")
    return CheckResult("B4", "fail", "No phone, email link, or street address found")


def check_b5(site):
    name = site.host.replace("www.", "")
    ad_library = (
        "https://www.facebook.com/ads/library/?active_status=all&ad_type=all"
        f"&country=ALL&q={urllib.parse.quote(name)}"
    )
    transparency = (
        "https://adstransparency.google.com/?region=anywhere"
        f"&search={urllib.parse.quote(name)}"
    )
    return CheckResult(
        "B5", "not_verified",
        "Ad Library pages need a browser session — the CLI cannot verify them. "
        f"Check manually: {ad_library} | {transparency}",
    )


def check_b6(site):
    brand = site.host.replace("www.", "").split(".")[0]
    clutch = f"https://clutch.co/search?q={urllib.parse.quote(brand)}"
    designrush = f"https://www.designrush.com/agency/search?query={urllib.parse.quote(brand)}"
    return CheckResult(
        "B6", "not_verified",
        "Review platforms block automated reads. Check manually: "
        f"{clutch} | {designrush}",
    )


def check_b7(site):
    pages = site.pages_of_kind("terms")
    if not pages:
        return CheckResult("B7", "fail", "No terms page found")
    keywords = ["ownership", "terminate", "termination", "notice period", "cancel"]
    for url, text in pages:
        lowered = (text or "").lower()
        found = [kw for kw in keywords if kw in lowered]
        if found:
            return CheckResult("B7", "pass", f"Terms mention: {', '.join(found)} ({url})")
    return CheckResult("B7", "fail", "Terms page exists but says nothing about ownership or exit")


def check_b8(site):
    pages = site.pages_of_kind("services") + site.pages_of_kind("work")
    text = "\n".join(t for _, t in pages).lower()
    if any(kw in text for kw in ("export", "raw data", "dashboard", "real-time", "live reporting")):
        return CheckResult("B8", "pass", "Reporting page promises exports, raw data, or a live dashboard")
    if "monthly report" in text or "pdf report" in text:
        return CheckResult("B8", "fail", "Reporting described only as a monthly/PDF report")
    return CheckResult("B8", "fail", "No reporting transparency found on services pages")


def check_b9(site, pagespeed_key=None):
    home = site.home
    if home is None:
        return CheckResult("B9", "not_verified", "Homepage fetch failed")
    if pagespeed_key:
        url = (
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            f"?url={urllib.parse.quote(site.base_url)}&strategy=mobile&key={pagespeed_key}"
        )
        text = fx.get(url, timeout=25)
        if text:
            import json as _json
            try:
                data = _json.loads(text)
                lcp = data["lighthouseResult"]["audits"]["largest-contentful-paint"]["numericValue"]
                seconds = lcp / 1000
                if seconds <= 2.5:
                    return CheckResult("B9", "pass", f"Mobile LCP {seconds:.1f}s (PageSpeed lab)")
                return CheckResult("B9", "fail", f"Mobile LCP {seconds:.1f}s > 2.5s (PageSpeed lab)")
            except Exception:
                pass
        return CheckResult("B9", "not_verified", "PageSpeed API did not return LCP")
    ttfb = home.ttfb_ms
    size_kb = home.size_bytes // 1024
    if ttfb <= 800 and home.size_bytes <= 2 * 1024 * 1024:
        return CheckResult(
            "B9", "pass",
            f"Proxy check (no PageSpeed key): TTFB {ttfb}ms, homepage {size_kb}KB. "
            "Lab LCP needs --pagespeed-key.",
        )
    return CheckResult(
        "B9", "fail",
        f"Proxy check (no PageSpeed key): TTFB {ttfb}ms, homepage {size_kb}KB. "
        "Lab LCP needs --pagespeed-key.",
    )


def check_b10(site):
    links = site.homepage_links()
    same_as = set()
    for obj in site.json_ld:
        sa = obj.get("sameAs")
        if isinstance(sa, str):
            same_as.add(sa)
        elif isinstance(sa, list):
            same_as.update(x for x in sa if isinstance(x, str))
    candidates = links + sorted(same_as)
    social = [u for u in candidates if "linkedin.com/company" in u or "instagram.com/" in u]
    if not social:
        return CheckResult("B10", "fail", "No LinkedIn company page or Instagram linked")
    return CheckResult(
        "B10", "not_verified",
        "Social profiles linked but need a login to verify activity: " + ", ".join(social[:2]),
    )


CHECKS = [
    check_a1, check_a2, check_a3, check_a4, check_a5, check_a6,
    check_a7, check_a8, check_b1, check_b2, check_b3, check_b4,
    check_b5, check_b6, check_b7, check_b8, check_b9, check_b10,
]


def run_all(site, pagespeed_key=None):
    results = []
    for fn in CHECKS:
        if fn is check_b9:
            results.append(fn(site, pagespeed_key=pagespeed_key))
        else:
            results.append(fn(site))
    return results


def score(results):
    total = sum(r.earned for r in results)
    scored = [r for r in results if r.status != "not_verified"]
    geo = sum(r.earned for r in results if r.group == "A")
    geo_max = sum(r.points for r in results if r.group == "A")
    tr = sum(r.earned for r in results if r.group == "B")
    tr_max = sum(r.points for r in results if r.group == "B")
    if total >= 80:
        verdict = "solid"
    elif total >= 50:
        verdict = "ask"
    else:
        verdict = "risk"
    return {
        "total": total,
        "max": 100,
        "scored_count": len(scored),
        "total_count": len(results),
        "geo": geo, "geo_max": geo_max,
        "transparency": tr, "transparency_max": tr_max,
        "verdict": verdict,
        "red_flags": [r for r in results if r.group == "B" and r.status == "fail"],
        "not_verified": [r for r in results if r.status == "not_verified"],
    }
