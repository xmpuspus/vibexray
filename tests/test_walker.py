import shutil
from pathlib import Path

from vibexray.walker import collect_files

# Firebase rules text from https://firebase.google.com/docs/rules/basics (test mode example).
FIRESTORE_TEST_MODE = """rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
"""


def test_walker_reads_firebase_rules_and_gitignore(tmp_path):
    (tmp_path / "firestore.rules").write_text(FIRESTORE_TEST_MODE)
    (tmp_path / "storage.rules").write_text(FIRESTORE_TEST_MODE)
    (tmp_path / ".gitignore").write_text("node_modules\n")
    paths = {f.path for f in collect_files(tmp_path)}
    assert {"firestore.rules", "storage.rules", ".gitignore"} <= paths


def test_walker_skips_the_vibexray_skill_installed_in_the_project(tmp_path):
    # A project-scope install puts the skill, and its copy of this package, inside the repo.
    skill = Path(__file__).resolve().parents[1] / "skills" / "vibexray"
    for root in (".claude/skills", ".agents/skills"):
        shutil.copytree(skill, tmp_path / root / "vibexray")
    (tmp_path / ".claude" / "settings.json").write_text("{}\n")
    (tmp_path / "app.ts").write_text("export const a = 1;\n")
    paths = {f.path for f in collect_files(tmp_path)}
    assert paths == {"app.ts", ".claude/settings.json"}


def test_walker_skips_dependencies_and_lockfiles(tmp_path):
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1;\n")
    (tmp_path / "package-lock.json").write_text("{}\n")
    (tmp_path / "app.ts").write_text("export const a = 1;\n")
    paths = {f.path for f in collect_files(tmp_path)}
    assert paths == {"app.ts"}


def test_line_numbers_and_snippets_agree_after_a_form_feed(tmp_path):
    # Python's splitlines() also breaks on form feeds and  . The rules count "\n" only.
    from vibexray.rules import run_rules

    (tmp_path / "api.ts").write_text(
        "const a = 1;\x0c\nexport const load = () => fetch('http://localhost:3000/api/orders');\n"
        "const b = 2;\n"
    )
    hits = [f for f in run_rules(collect_files(tmp_path)) if "localhost" in f.rule_id]
    assert hits, "the localhost rule found nothing"
    for f in hits:
        assert "localhost" in f.snippet, (f.line, f.snippet)
