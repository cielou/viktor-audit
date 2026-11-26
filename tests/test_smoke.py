"""Smoke tests for VIKTOR Audit. Run: python3 -m pytest tests/ -v
(or: python3 tests/test_smoke.py)

Live tests hit the real internet: viktorcompany.com is the reference target
(the tool should score its own maker's site highly) and an unresolvable
name must exit non-zero.
"""

import subprocess
import sys
from pathlib import Path

try:
    import pytest
except ImportError:  # pytest is optional; tests also run standalone
    pytest = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from viktor_audit.i18n import check_i18n_complete  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "viktor_audit", *args],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )


def test_i18n_complete():
    assert check_i18n_complete() == {}


def test_viktorcompany_scores_high():
    res = run_cli("https://viktorcompany.com")
    assert res.returncode == 0, res.stderr
    assert "VIKTOR Audit Report" in res.stdout
    assert "Score:" in res.stdout
    assert "viktorcompany.com/audit" in res.stdout


def test_chinese_report():
    res = run_cli("https://viktorcompany.com", "--lang", "zh")
    assert res.returncode == 0, res.stderr
    assert "VIKTOR Audit" in res.stdout
    assert "得分" in res.stdout


def test_unresolvable_target_fails():
    res = run_cli("https://this-domain-definitely-does-not-exist-12345.com")
    assert res.returncode != 0


if __name__ == "__main__":
    if pytest is not None:
        sys.exit(pytest.main([__file__, "-v"]))
    for fn in (test_i18n_complete, test_viktorcompany_scores_high,
               test_chinese_report, test_unresolvable_target_fails):
        fn()
        print(f"{fn.__name__}: OK")
