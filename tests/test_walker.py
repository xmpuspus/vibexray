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


def test_walker_skips_dependencies_and_lockfiles(tmp_path):
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1;\n")
    (tmp_path / "package-lock.json").write_text("{}\n")
    (tmp_path / "app.ts").write_text("export const a = 1;\n")
    paths = {f.path for f in collect_files(tmp_path)}
    assert paths == {"app.ts"}
