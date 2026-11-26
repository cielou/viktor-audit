<p align="center">
  <img src="https://viktorcompany.com/og.jpg" width="480" alt="Viktor & Company">
</p>

# VIKTOR Audit

**Audit any marketing agency from its public footprint — paste a URL, get a scored report.**

```bash
python -m viktor_audit "https://some-agency.com"
```

No login. No API key. No signup. Standard-library-only Python.

**Try it in your browser — no install:** [viktorcompany.com/audit-tool](https://viktorcompany.com/audit-tool/) — paste any agency's URL and get the scored report.

## What it does

You paste a marketing agency's URL or name. VIKTOR Audit checks what anyone can see without access — its AI search visibility and its transparency — and produces a scored Markdown report:

- **GEO — AI Search Visibility (40 pts):** llms.txt, AI-crawler access, Organization / FAQPage / Offer schema, AI citation, third-party mentions, content freshness.
- **Transparency — Should You Hire Them (60 pts):** pricing published, named case studies with real numbers, real team page, real contact details, Ad Library activity, independent reviews, contract signals, reporting transparency, site performance, social presence.

Verdict bands: **80–100 Solid** · **50–79 Ask first** · **0–49 High risk**. Every report ends with "5 questions to ask before you hire them" — and quick wins for the target.

## Install

Requires Python 3.10+ and Git. No other dependencies.

```bash
git clone https://github.com/cielou/viktor-audit.git
cd viktor-audit
python -m viktor_audit "https://some-agency.com"
```

On macOS/Linux, use `python3` instead of `python`.

## Usage

```bash
# English report (default), printed to stdout
python -m viktor_audit "https://some-agency.com"

# Another language, written to a file
python -m viktor_audit "Some Agency" --lang zh --out report.md

# All languages: en (default), zh, fr, es
python -m viktor_audit "https://some-agency.com" --lang fr

# Optional: lab LCP reading on the performance check
python -m viktor_audit "https://some-agency.com" --pagespeed-key YOUR_KEY
```

On Windows, legacy CMD garbles non-English output — run `chcp 65001` first, then `--lang zh` (or fr/es).

## How it works

Each check is **pass / fail / not verified**. Missing data is reported as NOT VERIFIED — never silently skipped, never guessed, never treated as a pass or a fail. The report always shows the denominator ("16/18 checks scored"). Four checks need a browser session or a live AI (AI citation, Ad Library, reviews, social activity): the CLI marks them NOT VERIFIED with the links to check manually, and the `skills/viktor-audit/SKILL.md` skill lets any AI agent complete them.

## AI skill

`skills/viktor-audit/SKILL.md` in this repo lets Claude Code, Codex, Cursor, Gemini CLI, and other agents run the same audit: the agent runs the CLI, fills in the four browser/AI checks with its own tools, and produces the report in the requested language.

Install it as a Claude Code plugin:

```
/plugin marketplace add cielou/viktor-audit
/plugin install viktor-audit
```

## White-label

Reports are Markdown. Re-render them with your own brand (company name, logo, accent color) — keep the "Powered by VIKTOR Audit" line at the bottom.

## What this is not

This is the **outside view**. It cannot see inside an ad account — spend, fees, vendor contracts, tracking accuracy. That is what a full independent audit does: [viktorcompany.com/audit](https://viktorcompany.com/audit).

## About Viktor & Company

VIKTOR & COMPANY is a Vancouver-based independent marketing consultancy for DTC and consumer brands — paid social, influencer and creator campaigns, SEO and AI-search (GEO) visibility, and North America market entry. Founded in 2020; every engagement is led personally by the founder, never handed to juniors.

The firm only audits — it never sells the execution for the work it audits, and it holds no stake in your ad account. The $1K Growth Audit is the paid version of this tool: hours inside the actual account, with the numbers recomputed from raw data: [viktorcompany.com/audit](https://viktorcompany.com/audit).

## License

MIT. Built by [VIKTOR & COMPANY](https://viktorcompany.com) — independent auditor of ad agencies, with no stake in your account.
