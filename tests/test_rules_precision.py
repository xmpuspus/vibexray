"""Second pass: fewer wrong hits on real code, tool spans, and the two new AI categories."""

from rule_helpers import fx, hit_with, run

from vibexray.model import CATEGORIES, Finding

APP_JS = "Snodrod__ai-support-agent/public/app.js"
LOOP = "SliceIQ/backend/src/agent/react-loop.ts"
TOOLS = "SliceIQ/backend/src/agent/tools.ts"
AFHAM = "afhamahmed1__ai-support-agent/src/agent/tools.service.ts"
EAA_CFG = "EAA-Chapter-84-Connect/supabase/config.toml"
EAA_OPEN = "EAA-Chapter-84-Connect/supabase/functions/handle-email-events/index.ts"
EAA_HOOK = "EAA-Chapter-84-Connect/supabase/functions/auth-email-hook/index.ts"


def test_new_ai_categories_exist_in_group_ai():
    assert CATEGORIES["ai_no_tests"] == ("AI behavior has no tests", "ai")
    assert CATEGORIES["ai_no_cost_limit"] == ("AI use has no cost limit", "ai")


def test_missing_evals_and_cost_limits_use_their_own_category():
    assert {f.category for f in run("ai-no-eval-files", LOOP, TOOLS)} == {"ai_no_tests"}
    assert {f.category for f in run("ai-cost-controls", LOOP, TOOLS)} == {"ai_no_cost_limit"}


def test_price_flags_a_nonzero_money_constant():
    path = "my-wealth-view/src/routes/_authenticated/transactions.tsx"
    assert hit_with("hardcoded-price-or-limit", "WORTH_IT_MIN_AMOUNT", path)


def test_price_flags_plan_price_in_a_purchase_component():
    assert hit_with(
        "hardcoded-price-or-limit",
        "price: 10",
        "yana-contabila/src/components/AICreditsPurchase.tsx",
    )


def test_price_ignores_zero_cost_state_in_the_browser_app():
    assert run("hardcoded-price-or-limit", APP_JS) == []


def test_price_ignores_zero_cost_counter_in_a_cost_page():
    assert run("hardcoded-price-or-limit", "yana-contabila/src/pages/PlatformCosts.tsx") == []


def test_price_ignores_sample_order_data():
    assert run("hardcoded-price-or-limit", "resolve-webmcp/lib/data.ts") == []


def test_xss_ignores_static_markup_template():
    assert run("xss-html-injection", "yana-contabila/src/components/VisualFeedback.tsx") == []


def test_xss_flags_markup_joined_with_a_variable():
    assert hit_with(
        "xss-html-injection", "container.innerHTML", "Hesper-Labs__owly/public/widget/owly-chat.js"
    )


def test_xss_flags_a_variable_assigned_to_inner_html():
    assert hit_with("xss-html-injection", "inner.innerHTML = html", APP_JS)


def test_token_flags_access_token_in_session_storage():
    path = "milk-me-not/src/contexts/AuthContext.tsx"
    assert hit_with("token-in-localstorage", "passwordRecoveryAccessToken", path)


def test_token_ignores_a_session_id_in_session_storage():
    assert run("token-in-localstorage", APP_JS) == []


def _covers(f: Finding, text_in_tool: str, key: str) -> bool:
    lines = fx(key).text.splitlines()
    marker = next(i for i, x in enumerate(lines, 1) if text_in_tool in x)
    return f.end_line is not None and f.line <= marker <= f.end_line


def test_no_approval_finding_covers_the_whole_refund_tool():
    found = [f for f in run("tool-action-no-approval", LOOP, TOOLS) if "refund" in f.snippet]
    assert found and _covers(found[0], "required: ['orderId', 'amount', 'reason']", LOOP)


def test_unbounded_finding_covers_the_whole_refund_tool():
    found = run("tool-number-unbounded", LOOP, TOOLS)
    assert found and _covers(found[0], "required: ['orderId', 'amount', 'reason']", LOOP)


def test_canned_finding_covers_the_whole_handler():
    found = run("tool-returns-canned", AFHAM)
    assert found and all(f.end_line and f.end_line > f.line for f in found)


def test_prompt_rule_gives_the_tool_span():
    found = [f for f in run("prompt-limit-not-in-code", LOOP, TOOLS) if f.related_file]
    assert found and found[0].related_end_line > found[0].related_line


def _line_after(key: str, section: str) -> int:
    lines = fx(key).text.splitlines()
    return next(i for i, x in enumerate(lines, 1) if section in x) + 1


def test_verify_jwt_off_is_flagged_for_a_function_that_writes_with_no_auth_in_code():
    cfg = "workfamilai/supabase/config.toml"
    src = "workfamilai/supabase/functions/create-donation/index.ts"
    found = run("auth-disabled-flag", cfg, src)
    assert _line_after(cfg, "[functions.create-donation]") in {f.line for f in found}


def test_verify_jwt_off_is_clean_when_the_function_checks_the_caller():
    found = run("auth-disabled-flag", EAA_CFG, EAA_OPEN, EAA_HOOK)
    assert _line_after(EAA_CFG, "[functions.auth-email-hook]") not in {f.line for f in found}


def test_admin_page_wrapped_in_a_protected_route_is_clean():
    page = "workfamilai/src/pages/Admin.tsx"
    assert run("admin-route-no-guard", page, "workfamilai/src/App.tsx") == []


def test_settings_page_in_an_app_with_no_login_is_clean():
    assert run("admin-route-no-guard", "cal-ai-clone/src/pages/Settings.tsx") == []
