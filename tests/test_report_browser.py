"""Open report.html in Chromium at three screen sizes. Every scan runs the real rules."""

import os
from pathlib import Path

import pytest
from test_report import SECTIONS, scan_fixture, with_history

from vibexray.cli import scan
from vibexray.report import write_reports

pytestmark = pytest.mark.browser
sync_api = pytest.importorskip("playwright.sync_api")

VIEWPORTS = {"desktop": (1920, 1080), "laptop": (1440, 900), "phone": (390, 844)}
CORPUS = Path(os.environ.get("VIBEXRAY_CORPUS", Path(__file__).parents[1] / ".cache" / "corpus"))


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def full_report(tmp_path, monkeypatch) -> Path:
    result = with_history(scan_fixture("SliceIQ", tmp_path), monkeypatch)
    return write_reports(result, tmp_path / "full")["html"]


def empty_report(tmp_path, _monkeypatch) -> Path:
    target = tmp_path / "empty-app"
    target.mkdir()
    result = scan(target, tmp_path / "empty", run=False, history_mode="none")
    return write_reports(result, tmp_path / "empty")["html"]


def big_report(tmp_path, _monkeypatch) -> Path:
    repo = CORPUS / "yana-contabila"
    if not repo.is_dir():
        pytest.skip("corpus not fetched; set VIBEXRAY_CORPUS")
    result = scan(repo, tmp_path / "big", run=False, history_mode="none")
    return write_reports(result, tmp_path / "big")["html"]


def open_report(browser, html: Path, size: tuple[int, int]):
    page = browser.new_page(viewport={"width": size[0], "height": size[1]})
    seen = {"errors": [], "requests": []}
    page.on("console", lambda m: m.type == "error" and seen["errors"].append(m.text))
    page.on("pageerror", lambda e: seen["errors"].append(str(e)))
    page.on("request", lambda r: seen["requests"].append(r.url))
    page.goto(html.as_uri())
    page.wait_for_load_state("load")
    return page, seen


def overflow(page) -> int:
    return page.evaluate("document.documentElement.scrollWidth - window.innerWidth")


@pytest.mark.parametrize("build", [full_report, empty_report, big_report])
@pytest.mark.parametrize("viewport", list(VIEWPORTS))
def test_report_fits_and_shows_every_section(browser, tmp_path, monkeypatch, build, viewport):
    html = build(tmp_path, monkeypatch)
    page, seen = open_report(browser, html, VIEWPORTS[viewport])
    try:
        assert overflow(page) <= 0, "page scrolls sideways"
        for sid in SECTIONS:
            section = page.locator(f"section#{sid}")
            assert section.is_visible(), sid
            heading = section.locator("h2").inner_text().strip()
            assert heading, sid
            body = section.inner_text().replace(heading, "", 1)
            assert len(body.split()) > 5, f"{sid} looks blank"
        # Opened code boxes must scroll inside themselves, never widen the page.
        page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
        assert overflow(page) <= 0, "an opened code box widens the page"
        assert seen["errors"] == []
        stray = [u for u in seen["requests"] if not u.startswith(("file://", "data:"))]
        assert stray == []
        assert seen["requests"] == [html.as_uri()]
    finally:
        page.close()


def test_first_screen_shows_the_answer(browser, tmp_path, monkeypatch):
    html = full_report(tmp_path, monkeypatch)
    for name in ("laptop", "phone"):
        width, height = VIEWPORTS[name]
        page, _ = open_report(browser, html, (width, height))
        try:
            for selector in ("h1", ".stats", "#decisions h2", "#decisions .q"):
                box = page.locator(selector).first.bounding_box()
                assert box and box["y"] < height, (name, selector)
        finally:
            page.close()


def test_phone_toggles_are_big_enough_to_tap(browser, tmp_path, monkeypatch):
    html = full_report(tmp_path, monkeypatch)
    page, _ = open_report(browser, html, VIEWPORTS["phone"])
    try:
        heights = page.evaluate(
            "[...document.querySelectorAll('summary')].map(s => s.getBoundingClientRect().height)"
        )
        assert heights and min(heights) >= 44
    finally:
        page.close()


def test_print_opens_every_code_box(browser, tmp_path, monkeypatch):
    html = full_report(tmp_path, monkeypatch)
    page, seen = open_report(browser, html, VIEWPORTS["laptop"])
    try:
        page.emulate_media(media="print")
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        closed = page.evaluate(
            "[...document.querySelectorAll('details')].filter(d => !d.open).length"
        )
        assert closed == 0
        assert seen["errors"] == []
    finally:
        page.close()
