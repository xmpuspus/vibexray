from rule_helpers import hit_with, run

SURVEY = "EAA-Chapter-84-Connect/drizzle/migrations/0000_survey_responses.sql"
EAA_MIGRATION = "EAA-Chapter-84-Connect/supabase/migrations/20260228011510_2e8af2f8-2ab1-4382-b8e8-c1636a06aeef.sql"
BASELINE = "milk-me-not/supabase/migrations/00000000000000_baseline.sql"
ROLES = "EAA-Chapter-84-Connect/src/pages/UserRoles.tsx"


def test_policy_with_check_true_for_anon_insert_is_flagged():
    found = hit_with("policy-using-true", "with check (true)", SURVEY)
    assert found and found[0].severity == "high"


def test_policy_using_true_in_migration_is_flagged():
    assert hit_with("policy-using-true", "USING (true)", EAA_MIGRATION)


def test_function_with_search_path_is_not_a_policy_finding():
    assert run("policy-using-true", BASELINE) == []


def test_grant_to_anon_is_flagged():
    assert hit_with("rls-enabled-no-policy-or-grants", "to anon", SURVEY)


def test_table_with_rls_enabled_is_not_missing_rls():
    assert run("rls-missing", SURVEY) == []


def test_security_definer_with_search_path_is_not_open():
    assert run("rpc-or-function-open", BASELINE) == []


def test_client_write_to_user_roles_is_flagged():
    assert hit_with("client-write-sensitive-table", "user_roles", ROLES)


def test_rules_without_a_corpus_hit_stay_quiet():
    for rid in ("service-role-in-client", "supabase-client-key-kind"):
        assert run(rid, ROLES) == [], rid
