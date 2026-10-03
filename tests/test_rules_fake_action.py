from rule_helpers import hit_with, run

SETTINGS = (
    "gpt-realtime-2-customer-support-voice-agent/apps/web/src/components/settings/settings-form.tsx"
)
UPDATE_BTN = "EAA-Chapter-84-Connect/src/components/CheckForUpdatesButton.tsx"
TOAST = "SliceIQ/frontend/src/components/Toast.tsx"
ROLES = "EAA-Chapter-84-Connect/src/pages/UserRoles.tsx"


def test_settimeout_success_flags_demo_only_save():
    assert hit_with("settimeout-success", "setTimeout(r, 400)", SETTINGS)


def test_settimeout_success_ignores_a_reload_after_a_wait():
    assert run("settimeout-success", UPDATE_BTN) == []


def test_settimeout_success_ignores_toast_auto_dismiss():
    assert run("settimeout-success", TOAST) == []


def test_fake_delay_flags_timer_inside_a_submit_handler():
    assert hit_with("fake-delay-loader", "setTimeout(r, 400)", SETTINGS)


def test_fake_delay_ignores_toast_auto_dismiss():
    assert run("fake-delay-loader", TOAST) == []


def test_toast_without_network_flags_saved_message():
    found = hit_with("toast-without-network", "Settings saved", SETTINGS)
    assert found and found[0].label == "rewrite"


def test_toast_without_network_ignores_handlers_that_call_supabase():
    assert run("toast-without-network", ROLES) == []


def test_todo_handler_flags_capture_handler():
    assert hit_with(
        "todo-handler-body",
        "TODO: Process the captured",
        "cal-ai-clone/src/components/Dashboard.tsx",
    )


def test_promise_resolve_success_ignores_function_that_awaits_a_call():
    assert run("promise-resolve-success", "milk-me-not/src/hooks/auth/useAuthOperations.ts") == []


def test_rules_without_a_corpus_hit_stay_quiet():
    for rid in ("console-log-as-send", "route-returns-ok-only", "localstorage-as-backend"):
        assert run(rid, ROLES, UPDATE_BTN) == [], rid
