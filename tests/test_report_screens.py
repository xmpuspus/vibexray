"""The report embeds app-run screenshots that the scan saved next to it.

The fixture is a real screenshot of the /chat page of ai-customer-support-agent
(MIT, see tests/corpus/corpus.lock.json), taken by `vibexray scan` with the app run.
"""

import shutil
from pathlib import Path

from vibexray.model import AppRun, Finding, Page, ScanResult
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


def test_pages_with_the_same_screen_share_one_card(tmp_path):
    # In the hero run, five /admin pages all redirected to the same sign-in screen.
    out = tmp_path / "report"
    (out / "screens").mkdir(parents=True)
    for name in ("01-admin.png", "02-admin-tickets.png"):
        shutil.copy(SCREEN, out / "screens" / name)
    run = AppRun(
        state="ran",
        reason="vibexray started the app and visited 2 pages.",
        url="http://localhost:3000",
        pages=[
            Page(path="/admin", title="Support", screenshot="screens/01-admin.png", status=200),
            Page(
                path="/admin/tickets",
                title="Support",
                screenshot="screens/02-admin-tickets.png",
                status=200,
            ),
        ],
    )
    result = _result_with_page("screens/01-admin.png")
    result.app_run = run
    write_reports(result, out)
    html = (out / "report.html").read_text()
    assert html.count("data:image/png;base64,") == 1
    assert "These 2 pages showed the same screen" in html
    assert "/<wbr>admin/<wbr>tickets" in html


def test_file_paths_can_wrap_at_each_folder(tmp_path):
    out = tmp_path / "report"
    result = _result_with_page("screens/none.png")
    result.findings = [
        Finding(
            rule_id="review",
            category="auth_gap",
            severity="high",
            file="src/app/api/conversations/[id]/route.ts",
            line=6,
            snippet="export async function GET(_req: Request, { params }: { params: { id: string } }) {",
            pm_text="Anyone can read any chat.",
            engineer_text="Add a session check.",
            label="rewrite",
        )
    ]
    write_reports(result, out)
    html = (out / "report.html").read_text()
    assert "src/<wbr>app/<wbr>api/<wbr>conversations/<wbr>[id]/<wbr>route.ts:6" in html
