from pathlib import Path

from conftest import load_report_json

from vibexray import __version__
from vibexray.model import CATEGORIES

FAKE_CATEGORIES = {k for k, v in CATEGORIES.items() if v[1] == "fake"}


def test_version_flag_prints_version(cli):
    result = cli("--version")
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_scan_missing_folder_fails_with_plain_message(cli, tmp_path):
    result = cli("scan", str(tmp_path / "nope"))
    assert result.returncode == 2
    assert "not a folder" in result.stderr.lower()


def test_scan_empty_folder_writes_all_three_outputs(cli, tmp_path):
    target = tmp_path / "empty-app"
    target.mkdir()
    out = tmp_path / "out"
    result = cli("scan", str(target), "--out", str(out), "--no-run", "--no-history")
    assert result.returncode == 0, result.stderr
    for name in ("report.html", "handoff.md", "vibexray.json"):
        assert (out / name).is_file(), name


def test_empty_scan_shows_explicit_empty_states_never_blank(cli, tmp_path):
    target = tmp_path / "empty-app"
    target.mkdir()
    out = tmp_path / "out"
    cli("scan", str(target), "--out", str(out), "--no-run", "--no-history")
    html = (out / "report.html").read_text()
    assert "No fake parts found" in html
    assert "The app did not run" in html
    assert "No build chat found" in html
    data = load_report_json(out)
    assert data["findings"] == []
    assert data["app_run"]["state"] == "not_attempted"
    assert data["history"]["source"] == "none"


def test_report_json_records_target_and_version(cli, tmp_path):
    target = tmp_path / "app"
    target.mkdir()
    (target / "package.json").write_text('{"name": "app"}')
    out = tmp_path / "out"
    cli("scan", str(target), "--out", str(out), "--no-run", "--no-history")
    data = load_report_json(out)
    assert data["version"] == __version__
    assert Path(data["target"]).name == "app"
    assert data["files_scanned"] == 1


FIXTURE = Path(__file__).parent / "fixtures" / "ai-customer-support-agent"


def _row(stdout: str, label: str) -> int:
    line = next(ln for ln in stdout.splitlines() if ln.strip().startswith(label))
    return int(line.split()[len(label.split())])


def test_terminal_summary_uses_the_report_numbers(cli, tmp_path):
    out = tmp_path / "out"
    result = cli("scan", str(FIXTURE), "--out", str(out), "--no-run", "--no-history")
    assert result.returncode == 0, result.stderr
    data = load_report_json(out)
    files = {"fake": set(), "risk": set()}
    for f in data["findings"]:
        files["fake" if f["category"] in FAKE_CATEGORIES else "risk"].add(f["file"])
    assert _row(result.stdout, "Fake parts") == len(files["fake"])
    assert _row(result.stdout, "Parts that can break") == len(files["risk"])
    assert _row(result.stdout, "Decisions for you") == len(data["questions"])
    assert "App run   The app did not run. Skipped: the scan ran with --no-run." in result.stdout


def test_terminal_summary_counts_read_as_plain_english(cli, tmp_path):
    target = tmp_path / "empty-app"
    target.mkdir()
    result = cli("scan", str(target), "--out", str(tmp_path / "out"), "--no-run", "--no-history")
    assert "vibexray found no app code in empty-app." in result.stdout
    assert " 1 questions" not in result.stdout
