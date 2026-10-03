from rule_helpers import hit_with, run

PURCHASE = "yana-contabila/src/components/AICreditsPurchase.tsx"


def test_localhost_fallback_in_server_cors_is_flagged_medium():
    found = hit_with("localhost-url", "localhost:5173", "SliceIQ/backend/src/index.ts")
    assert found and found[0].severity == "medium"


def test_localhost_in_a_dev_only_allow_list_is_ignored():
    assert (
        run(
            "localhost-url",
            "EAA-Chapter-84-Connect/src/integrations/supabase/previewAuthStorage.ts",
        )
        == []
    )


def test_stripe_price_id_literal_is_flagged():
    assert hit_with("stripe-id-literal", "price_1SIsUM", PURCHASE)


def test_price_literal_is_flagged():
    assert hit_with("hardcoded-price-or-limit", "price: 10", PURCHASE)


def test_feature_flag_literal_is_flagged():
    assert hit_with(
        "feature-flag-literal", "ENABLE_ANALYTICS", "workfamilai/src/config/production.ts"
    )


def test_preview_host_in_native_config_is_flagged():
    assert hit_with(
        "preview-or-tunnel-url", "lovableproject.com", "milk-me-not/capacitor.config.ts"
    )


def test_preview_host_in_page_meta_is_flagged():
    assert hit_with("preview-or-tunnel-url", "lovable.app", "my-wealth-view/src/routes/__root.tsx")


def test_fixed_user_uuid_in_query_is_flagged():
    path = "yana-contabila/supabase/functions/consciousness-engine/index.ts"
    assert hit_with("hardcoded-record-id", "a0eebc99", path)


def test_all_zero_singleton_row_id_is_ignored():
    assert (
        run("hardcoded-record-id", "yana-contabila/supabase/functions/capture-soul-state/index.ts")
        == []
    )


def test_magic_number_conflict_stays_quiet_when_values_agree():
    assert run("magic-number-conflict", "workfamilai/src/config/production.ts", PURCHASE) == []
