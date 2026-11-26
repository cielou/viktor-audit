"""Render a VIKTOR Audit report as Markdown."""

from __future__ import annotations

from datetime import datetime, timezone

from .i18n import LANG_NAMES, strings

QUICK_WIN_FIX = {
    "A1": "Publish an llms.txt that lists your key pages so AI can cite you accurately.",
    "A2": "Allow AI crawlers (GPTBot, ClaudeBot, PerplexityBot) in robots.txt.",
    "A3": "Add Organization schema with name, URL, and sameAs links.",
    "A4": "Add FAQPage schema for the questions buyers actually ask.",
    "A5": "Add Service/Offer schema with price or price range.",
    "A6": "Get cited: publish answer-shaped content and earn third-party mentions.",
    "A7": "Claim profiles on Clutch, DesignRush, and Google Business Profile.",
    "A8": "Publish something new at least once a quarter.",
    "B1": "Publish pricing — even a range. Hidden pricing is a red flag to buyers.",
    "B2": "Publish one case study with a named client and one real number.",
    "B3": "Show the real team — names, roles, faces that are not stock photos.",
    "B4": "Publish a real address, phone number, or named email.",
    "B5": "Make sure your ads match their landing pages.",
    "B6": "Collect independent reviews and keep them recent.",
    "B7": "State who owns the account, the data, and the creative — in writing.",
    "B8": "Promise raw exports and live dashboards, not a monthly PDF.",
    "B9": "Fix mobile load speed — compress images, defer non-critical scripts.",
    "B10": "Post on LinkedIn or Instagram at least monthly.",
}


def render(results, summary, target, lang):
    s = strings(lang)
    names = s["check_names"]
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    verdict = summary["verdict"]

    lines.append(f"# {s['report_title']}")
    lines.append("")
    lines.append(f"- **{s['target']}:** {target}")
    lines.append(f"- **{s['date']}:** {now}")
    lines.append(f"- **{s['language']}:** {LANG_NAMES.get(lang, lang)}")
    lines.append("")
    lines.append(
        f"## {s['score_line']}: {summary['total']}/{summary['max']} — "
        f"{s['verdict_' + verdict]}"
    )
    lines.append("")
    lines.append(f"{s['verdict_' + verdict + '_line']}")
    lines.append("")
    lines.append(
        f"({summary['scored_count']}/{summary['total_count']} "
        f"{s['checks_scored']}, "
        f"{len(summary['not_verified'])} {s['not_verified_count']})"
    )
    lines.append("")
    lines.append(f"*{s['method_note']}*")
    lines.append("")
    lines.append(f"## {s['executive_summary']}")
    lines.append("")
    passed = [r for r in results if r.status == "pass"]
    failed = [r for r in results if r.status == "fail"]
    lines.append(f"- {s['summary_strength']} " + (
        ", ".join(names[r.id] for r in passed[:3]) if passed else "—"))
    lines.append(f"- {s['summary_weakness']} " + (
        ", ".join(names[r.id] for r in failed[:3]) if failed else "—"))
    lines.append(f"- {s['summary_unverified']} " + (
        ", ".join(names[r.id] for r in summary['not_verified'][:3])
        if summary['not_verified'] else "—"))
    lines.append("")
    lines.append(f"## {s['section_scores']}")
    lines.append("")
    lines.append(f"- {s['geo_section']}: {summary['geo']}/{summary['geo_max']}")
    lines.append(
        f"- {s['transparency_section']}: "
        f"{summary['transparency']}/{summary['transparency_max']}")
    lines.append("")
    lines.append(f"## {s['check_table']}")
    lines.append("")
    lines.append("| ID | Check | Result | Evidence |")
    lines.append("|----|-------|--------|----------|")
    for r in results:
        status = s["status_" + r.status]
        evidence = (r.evidence or "").replace("|", "/").replace("\n", " ")
        lines.append(f"| {r.id} | {names[r.id]} | {status} | {evidence} |")
    lines.append("")
    lines.append(f"## {s['red_flags']}")
    lines.append("")
    if summary["red_flags"]:
        for r in summary["red_flags"]:
            lines.append(f"- **{names[r.id]}** — {r.evidence}")
    else:
        lines.append(s["no_red_flags"])
    lines.append("")
    lines.append(f"## {s['questions_title']}")
    lines.append("")
    for i, q in enumerate(s["questions"], 1):
        lines.append(f"{i}. {q}")
    lines.append("")
    lines.append(f"## {s['quick_wins_title']}")
    lines.append("")
    wins = [r for r in failed][:5]
    if wins:
        for r in wins:
            lines.append(f"- **{names[r.id]}:** {QUICK_WIN_FIX.get(r.id, '')}")
    else:
        lines.append(s["no_red_flags"])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(s["footer"])
    lines.append("")
    return "\n".join(lines)
