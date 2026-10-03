from rule_helpers import hit_with, run

ROLES = "EAA-Chapter-84-Connect/src/pages/UserRoles.tsx"
ADMIN_PAGE = "ai-customer-support-agent/src/app/admin/(dashboard)/page.tsx"
ADMIN_LAYOUT = "ai-customer-support-agent/src/app/admin/(dashboard)/layout.tsx"


def test_localstorage_flag_decides_access():
    assert hit_with("localstorage-auth-gate", "isLoggedIn", "cal-ai-clone/src/pages/Index.tsx")


def test_auth_disabled_flag_finds_verify_jwt_false_in_config():
    found = hit_with(
        "auth-disabled-flag", "verify_jwt = false", "EAA-Chapter-84-Connect/supabase/config.toml"
    )
    assert found and found[0].label == "check"


def test_hardcoded_admin_fallback_is_flagged():
    assert hit_with(
        "hardcoded-role-or-user", "isAdmin = true", "yana-contabila/src/pages/StrategicAdvisor.tsx"
    )


def test_role_type_union_is_not_a_hardcoded_role():
    assert run("hardcoded-role-or-user", ROLES) == []


def test_admin_page_with_no_guard_in_the_file_set_is_flagged():
    assert run("admin-route-no-guard", ADMIN_PAGE)


def test_admin_page_covered_by_layout_session_check_is_clean():
    assert run("admin-route-no-guard", ADMIN_PAGE, ADMIN_LAYOUT) == []


def test_public_chat_route_that_writes_is_flagged_for_a_check():
    found = run("api-route-no-auth", "ai-customer-support-agent/src/app/api/chat/route.ts")
    assert found and found[0].label in ("check", "rewrite")


def test_routes_with_a_role_check_are_clean():
    for key in (
        "nexora-ai/app/api/admin/tickets/[id]/route.ts",
        "nexora-ai/app/api/documents/route.ts",
        "ai-customer-support-agent/src/app/api/tickets/route.ts",
    ):
        assert run("api-route-no-auth", key) == [], key


def test_rules_without_a_corpus_hit_stay_quiet():
    for rid in ("client-password-check", "client-only-role-gate", "fake-login-handler"):
        assert run(rid, ROLES) == [], rid
