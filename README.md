# VIKTOR Audit

**Audit any marketing agency from its public footprint — paste a URL, get a scored report.**

```bash
python3 -m viktor_audit "https://some-agency.com"
```

No login. No API key. No signup. Standard-library-only Python.

## What it does

You paste a marketing agency's URL or name. VIKTOR Audit checks what anyone can see without access — its AI search visibility and its transparency — and produces a scored Markdown report:

- **GEO — AI Search Visibility (40 pts):** llms.txt, AI-crawler access, Organization / FAQPage / Offer schema, AI citation, third-party mentions, content freshness.
- **Transparency — Should You Hire Them (60 pts):** pricing published, named case studies with real numbers, real team page, real contact details, Ad Library activity, independent reviews, contract signals, reporting transparency, site performance, social presence.

Verdict bands: **80–100 Solid** · **50–79 Ask first** · **0–49 High risk**. Every report ends with "5 questions to ask before you hire them" — and quick wins for the target.

## Install

```bash
git clone https://github.com/cielou/viktor-audit.git
cd viktor-audit
python3 -m viktor_audit "https://some-agency.com"
```

Requires Python 3.10+. No dependencies.

## Usage

```bash
# English report (default), printed to stdout
python3 -m viktor_audit "https://some-agency.com"

# Another language, written to a file
python3 -m viktor_audit "Some Agency" --lang zh --out report.md

# All languages: en (default), zh, fr, es
python3 -m viktor_audit "https://some-agency.com" --lang fr

# Optional: lab LCP reading on the performance check
python3 -m viktor_audit "https://some-agency.com" --pagespeed-key YOUR_KEY
```

## How it works

Each check is **pass / fail / not verified**. Missing data is reported as NOT VERIFIED — never silently skipped, never guessed, never treated as a pass or a fail. The report always shows the denominator ("16/18 checks scored"). Four checks need a browser session or a live AI (AI citation, Ad Library, reviews, social activity): the CLI marks them NOT VERIFIED with the links to check manually, and the `SKILL.md` lets any AI agent complete them.

## AI skill

`SKILL.md` in this repo lets Claude Code, Codex, Cursor, Gemini CLI, and other agents run the same audit: the agent runs the CLI, fills in the four browser/AI checks with its own tools, and produces the report in the requested language.

## White-label

Reports are Markdown. Re-render them with your own brand (company name, logo, accent color) — keep the "Powered by VIKTOR Audit" line at the bottom.

## What this is not

This is the **outside view**. It cannot see inside an ad account — spend, fees, vendor contracts, tracking accuracy. That is what a full independent audit does: [viktorcompany.com/audit](https://viktorcompany.com/audit).

## License

MIT. Built by [VIKTOR & COMPANY](https://viktorcompany.com) — independent auditor of ad agencies, with no stake in your account.
