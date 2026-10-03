from rule_helpers import hit_with, run

MILK = "milk-me-not/src/components/MapboxWorldMap.tsx"


def test_mock_array_ignores_real_database_tools():
    assert run("mock-array-literal", "ai-customer-support-agent/src/lib/agent/tools.ts") == []


def test_mock_library_import_flags_faker():
    found = hit_with("mock-library-import", "@faker-js/faker", "docs/faker-usage.js")
    assert found and found[0].label == "throwaway"


def test_mock_library_import_ignores_map_component():
    assert run("mock-library-import", MILK) == []


def test_mock_path_flags_the_file_that_imports_a_mock_module():
    found = run("mock-path-segment", "nexora-ai/lib/ai-mock.ts", "nexora-ai/lib/ai.ts")
    assert any(f.file == "lib/ai.ts" and f.related_file == "lib/ai-mock.ts" for f in found)


def test_mock_path_needs_an_importer():
    assert run("mock-path-segment", "nexora-ai/lib/ai-mock.ts") == []


def test_placeholder_identity_flags_example_email_in_store_data():
    assert hit_with("placeholder-identity", "example.com", "Snodrod__ai-support-agent/src/data.ts")


def test_placeholder_identity_ignores_map_component():
    assert run("placeholder-identity", MILK) == []


def test_rules_without_a_corpus_hit_stay_quiet_on_real_code():
    for rid in ("lorem-ipsum", "json-file-as-database", "inline-record-array"):
        assert run(rid, MILK) == [], rid
