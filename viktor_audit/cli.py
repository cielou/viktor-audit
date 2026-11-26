"""VIKTOR Audit — command line interface.

Usage:
    python -m viktor_audit "https://some-agency.com" [--lang en|zh|fr|es]
    python -m viktor_audit "Some Agency" --lang zh --out report.md

Standard library only. No API keys, no signup, no server.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, checks, fetch
from .checks import SiteData, run_all, score
from .report import render

LANGS = ["en", "zh", "fr", "es"]


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="viktor-audit",
        description="Public-footprint audit of a marketing agency or app. "
                    "Paste a URL or a name, get a scored report.",
    )
    parser.add_argument("target", help="Agency/app URL or name")
    parser.add_argument("--lang", choices=LANGS, default="en",
                        help="Report language (default: en)")
    parser.add_argument("--out", help="Write the Markdown report to this file")
    parser.add_argument("--pagespeed-key",
                        help="Optional PageSpeed Insights API key for a lab LCP "
                             "reading on the performance check")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    url = fetch.normalize_target(args.target)
    if not url:
        print(f"Could not resolve '{args.target}' to a URL. "
              "Please pass the full URL, e.g. https://some-agency.com",
              file=sys.stderr)
        return 2

    site = SiteData(url)
    if not site.discover():
        print(f"Could not fetch {url}. Check the URL and your connection.",
              file=sys.stderr)
        return 2

    results = run_all(site, pagespeed_key=args.pagespeed_key)
    summary = score(results)
    text = render(results, summary, url, args.lang)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Report written to {args.out} "
              f"({summary['total']}/100, {summary['verdict']})")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
