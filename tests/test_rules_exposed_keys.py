from rule_helpers import hit_with, run

MAPBOX = "milk-me-not/src/components/MapboxWorldMap.tsx"


def test_server_env_read_in_client_flags_db_password():
    assert hit_with("server-env-read-in-client", "DB_PASSWORD", "docs/vite-env-doc.js")


def test_server_env_read_ignores_public_prefixed_name():
    assert not hit_with("server-env-read-in-client", "VITE_SOME_KEY", "docs/vite-env-doc.js")


def test_public_prefix_name_ignores_a_public_map_token():
    assert run("public-prefix-secret-name", MAPBOX) == []


def test_default_fallback_ignores_a_project_ref():
    assert run("secret-default-fallback", "EAA-Chapter-84-Connect/src/lib/mcp/index.ts") == []


def test_snippet_never_shows_a_key_value():
    from vibexray.rules.base import redact

    assert "[hidden]" in redact("const k = 'whsec_" + "a1b2c3d4e5f6g7h8i9j0k1l2'")
    assert "[hidden]" in redact("const k = 'rk_live_" + "a1b2c3d4e5f6g7h8i9j0k1l2'")
    assert "[hidden]" in redact("key=sb_secret_" + "a1b2c3d4e5f6g7h8i9j0k1l2")


def test_rules_without_a_corpus_hit_stay_quiet():
    for rid in (
        "key-pattern-in-source",
        "vite-define-env-leak",
        "public-prefix-secret-value",
        "env-file-committed",
    ):
        assert run(rid, MAPBOX) == [], rid
