"""Third pass: each test is a real line that an independent audit judged a false alarm."""

from rule_helpers import fx, hit_with, run

DATA_RESOLVE = "resolve-webmcp/lib/data.ts"
DATA_SNODROD = "Snodrod__ai-support-agent/src/data.ts"
WF_CFG = "workfamilai/supabase/config.toml"
WF_FN = "workfamilai/supabase/functions/"
BARCODE = "milk-me-not/supabase/migrations/20260820120000_remember_product_barcodes.sql"
BASELINE = "milk-me-not/supabase/migrations/00000000000000_baseline.sql"


def line_with(key: str, text: str) -> int:
    return next(i for i, x in enumerate(fx(key).text.splitlines(), 1) if text in x)


def test_xss_ignores_title_from_the_site_owner_attribute():
    assert run("xss-html-injection", "afhamahmed1__ai-support-agent/public/widget.js") == []


def test_xss_ignores_constant_icons_and_server_numbers():
    assert run("xss-html-injection", "mj-deving__ai-support-agent/public/index.html") == []


def test_xss_ignores_files_that_escape_every_value():
    assert run("xss-html-injection", "Snodrod__ai-support-agent/public/app.js") == []


def test_xss_ignores_site_owner_config_in_widget():
    assert run("xss-html-injection", "Hesper-Labs__owly/public/widget/owly-chat.js") == []


def test_open_jwt_ignores_public_donation_contact_and_newsletter_forms():
    srcs = [
        WF_FN + n + "/index.ts"
        for n in ("create-donation", "submit-contact-form", "subscribe-newsletter")
    ]
    assert run("auth-disabled-flag", WF_CFG, *srcs) == []


def test_register_route_is_public_by_design():
    assert run("api-route-no-auth", "SliceIQ/backend/src/routes/auth.ts") == []


def test_public_quote_form_with_a_rate_limit_is_not_flagged():
    assert run("api-route-no-auth", WF_FN + "submit-work-package-quote/index.ts") == []


def test_sample_orders_are_mock_data_not_config():
    for key in (DATA_RESOLVE, DATA_SNODROD):
        found = run("sample-records-module", key)
        assert found and found[0].category == "mock_data", key
        assert run("hardcoded-price-or-limit", key) == [], key


def test_published_domain_in_social_tags_is_not_a_preview_url():
    assert run("preview-or-tunnel-url", "my-wealth-view/src/routes/__root.tsx") == []


def test_prompt_rule_ignores_a_return_that_waits_for_customer_approval():
    found = run(
        "prompt-limit-not-in-code",
        "Snodrod__ai-support-agent/src/prompt.ts",
        "Snodrod__ai-support-agent/src/tools.ts",
    )
    assert [f for f in found if f.file.endswith("prompt.ts")] == []


def test_empty_search_result_with_a_note_is_not_a_canned_tool():
    key = "Snodrod__ai-support-agent/src/tools.ts"
    bad = line_with(key, "No matching article")
    assert all(
        not (f.line <= bad <= (f.end_line or f.line)) for f in run("tool-returns-canned", key)
    )


def test_row_security_with_definer_functions_is_on_purpose():
    found = run("rls-enabled-no-policy-or-grants", BARCODE, BASELINE)
    assert [f for f in found if "product_barcodes" in f.snippet] == []


def test_anon_execute_on_a_read_only_lookup_is_not_open():
    assert [f for f in run("rpc-or-function-open", BARCODE) if "GRANT" in f.snippet.upper()] == []


def test_decorative_stock_photo_is_not_placeholder_media():
    assert run("placeholder-media", "cal-ai-clone/src/components/WelcomeScreen.tsx") == []


def test_todo_inside_a_tool_body_is_left_to_the_fake_tool_rule():
    key = "afhamahmed1__ai-support-agent/src/agent/tools.service.ts"
    assert run("todo-handler-body", key) == []
    assert run("tool-returns-canned", key)


def test_labeled_demo_mode_is_not_mock_data_or_a_fake_delay():
    key = "resolve-webmcp/app/workspace/page.tsx"
    assert hit_with("mock-array-literal", "demoSteps", key) == []
    demo_wait = line_with(key, "650")
    assert [f for f in run("fake-delay-loader", key) if f.line == demo_wait] == []
    assert [f for f in run("settimeout-success", key) if f.line == demo_wait] == []
