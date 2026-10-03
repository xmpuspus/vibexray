from rule_helpers import hit_with, run

BUBBLE = "SliceIQ/frontend/src/components/MessageBubble.tsx"
WIDGET = "afhamahmed1__ai-support-agent/public/widget.js"


def test_model_text_in_inner_html_is_flagged():
    assert hit_with("xss-html-injection", "dangerouslySetInnerHTML", BUBBLE)


def test_eval_word_in_a_string_list_is_not_a_call():
    assert run("eval-or-new-function", "milk-me-not/src/lib/fileValidation.ts") == []


def test_wildcard_cors_without_credentials_is_ignored():
    assert (
        run(
            "cors-wildcard-credentials",
            "EAA-Chapter-84-Connect/supabase/functions/auth-email-hook/index.ts",
        )
        == []
    )


def test_login_token_in_local_storage_is_flagged():
    assert hit_with(
        "token-in-localstorage", "sliceiq_token", "SliceIQ/frontend/src/components/Login.tsx"
    )


def test_tls_check_off_is_flagged():
    path = "yana-contabila/supabase/functions/email-client/index.ts"
    assert hit_with("tls-checks-off", "rejectUnauthorized: false", path)


def test_firebase_allow_all_is_flagged():
    found = hit_with(
        "firebase-open-rules", "allow read, write: if true", "docs/firebase-insecure.rules"
    )
    assert found and found[0].label == "rewrite"


def test_public_storage_bucket_is_flagged():
    path = "EAA-Chapter-84-Connect/supabase/migrations/20260302234155_82a8f4f7-af24-4ddc-91e3-6e9fb9ecc700.sql"
    assert hit_with("public-storage-bucket", "member-images", path)


def test_user_name_in_system_prompt_is_flagged():
    path = "yana-contabila/supabase/functions/samanta-voice-incoming/index.ts"
    assert hit_with("user-input-in-system-prompt", "systemPrompt", path)


def test_file_read_with_a_tool_supplied_path_is_flagged():
    assert hit_with(
        "path-traversal", "readFile(params.path", "yana-contabila/public/yana-local-agent/agent.mjs"
    )


def test_route_with_a_rate_limit_is_clean():
    assert run("ai-endpoint-no-rate-limit", "nexora-ai/app/api/chat/route.ts") == []


def test_rules_without_a_corpus_hit_stay_quiet():
    keys = ("nexora-ai/app/api/chat/route.ts", "nexora-ai/app/api/documents/route.ts")
    for rid in (
        "sql-string-concat",
        "open-redirect",
        "debug-route-left-on",
        "weak-jwt-secret",
        "cookie-missing-flags",
        "ssrf-user-url",
        "client-trusted-amount",
    ):
        assert run(rid, *keys) == [], rid
