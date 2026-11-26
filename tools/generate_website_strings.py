"""Generate the website trial's strings.js from viktor_audit/i18n.py.

The Python i18n.py is the single source of truth for report strings.
The Cloudflare Pages Function (functions/api/) is plain JS, so this script
dumps the STRINGS + LANG_NAMES dicts as an ES module.

Usage:
    python3 tools/generate_website_strings.py <output-path>
    # e.g. python3 tools/generate_website_strings.py \
    #        ../../viktorcompany/functions/api/strings.js

Re-run after any change to viktor_audit/i18n.py, then push both repos.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viktor_audit.i18n import LANG_NAMES, STRINGS, check_i18n_complete  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("usage: generate_website_strings.py <output-path>", file=sys.stderr)
        return 2
    missing = check_i18n_complete()
    if missing:
        print(f"i18n incomplete: {missing}", file=sys.stderr)
        return 1
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        "// Generated from viktor-audit/viktor_audit/i18n.py — do not edit by hand.\n"
        "// Re-run: python3 tools/generate_website_strings.py <this-path>\n"
        "export const STRINGS = "
        + json.dumps(STRINGS, ensure_ascii=False, indent=2)
        + ";\n\nexport const LANG_NAMES = "
        + json.dumps(LANG_NAMES, ensure_ascii=False, indent=2)
        + ";\n"
    )
    out.write_text(payload, encoding="utf-8")
    print(f"wrote {out} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
