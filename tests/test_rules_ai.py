from rule_helpers import hit_with, run

LOOP = "SliceIQ/backend/src/agent/react-loop.ts"
TOOLS = "SliceIQ/backend/src/agent/tools.ts"
AFHAM = "afhamahmed1__ai-support-agent/src/agent/tools.service.ts"
DB_TOOLS = "ai-customer-support-agent/src/lib/agent/tools.ts"
VOCAL = "vocal-note-keeper-ai/src/lib/summaryService.ts"


def test_openai_client_in_browser_code_is_flagged():
    found = hit_with("ai-browser-sdk", "dangerouslyAllowBrowser", VOCAL)
    assert found and found[0].category == "ai_browser_call"


def test_server_side_client_is_not_a_browser_call():
    assert run("ai-browser-sdk", LOOP) == []


def test_refund_limit_in_prompt_only_links_to_the_tool_code():
    found = run("prompt-limit-not-in-code", LOOP, TOOLS)
    hit = [f for f in found if f.related_file and f.related_file.endswith("tools.ts")]
    assert hit and hit[0].file.endswith("react-loop.ts") and hit[0].related_line


def test_refund_amount_has_no_bound():
    found = run("tool-number-unbounded", LOOP, TOOLS)
    assert any("refund" in f.snippet.lower() or "amount" in f.snippet for f in found)
    assert all(f.category == "ai_tool_unbounded" for f in found)


def test_refund_tool_has_no_approval_gate():
    found = run("tool-action-no-approval", LOOP, TOOLS)
    assert any("refund" in (f.snippet + f.engineer_text).lower() for f in found)
    assert all(f.category == "ai_no_human_review" for f in found)


def test_canned_order_lookup_is_a_fake_tool():
    found = run("tool-returns-canned", AFHAM)
    assert found and found[0].category == "ai_fake_tool" and found[0].label == "throwaway"


def test_database_backed_tools_are_not_fake():
    assert run("tool-returns-canned", DB_TOOLS) == []


def test_llm_call_without_eval_files_is_reported_at_the_call():
    found = run("ai-no-eval-files", LOOP, TOOLS)
    assert found and found[0].file.endswith("react-loop.ts")


def test_llm_call_without_max_tokens_is_reported():
    assert run("ai-cost-controls", LOOP, TOOLS)


def test_key_in_client_env_name_stays_quiet_on_server_code():
    assert run("ai-key-in-client-env", LOOP) == []
