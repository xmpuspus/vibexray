"""The report embeds app-run screenshots that the scan saved next to it.

The fixture is a real screenshot of the /chat page of ai-customer-support-agent
(MIT, see tests/corpus/corpus.lock.json), taken by `vibexray scan` with the app run.
"""

import shutil
from pathlib import Path

from vibexray.model import AppRun, Page, ScanResult
from vibexray.report import write_reports

SCREEN = Path(__file__).parent / "fixtures" / "screens" / "07-chat.png"


def _result_with_page(shot: str) -> ScanResult:
    run = AppRun(
        state="ran",
        reason="vibexray started the app and visited 1 page.",
        url="http://localhost:3000",
        pages=[Page(path="/chat", title="Support", screenshot=shot, status=200)],
    )
    return ScanResult(
        version="test",
        target="/home/pm/support-bot",
        app_name="support-bot",
        generated_at="2026-10-04 00:00 UTC",
        files_scanned=74,
        app_run=run,
    )


def test_relative_screenshot_path_resolves_against_the_report_folder(tmp_path, monkeypatch):
    out = tmp_path / "report"
    (out / "screens").mkdir(parents=True)
    shutil.copy(SCREEN, out / "screens" / "07-chat.png")
    # Run from another folder, the way a PM runs the CLI from their project root.
    monkeypatch.chdir(tmp_path)
    write_reports(_result_with_page("screens/07-chat.png"), out)
    html = (out / "report.html").read_text()
    assert "data:image/png;base64," in html
    assert "The screenshot file is missing." not in html


def test_missing_screenshot_says_so_plainly(tmp_path):
    out = tmp_path / "report"
    write_reports(_result_with_page("screens/does-not-exist.png"), out)
    assert "The screenshot file is missing." in (out / "report.html").read_text()
