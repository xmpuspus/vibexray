"""redact() hides key-shaped strings and leaves ordinary words alone."""

import pytest

from vibexray.rules.base import redact


@pytest.mark.parametrize(
    "text",
    [
        "risk-enhanced onboarding flow",
        "task-runner-config",
        "disk-usage-alert",
        "const ask-question-handler = () => {}",
    ],
)
def test_words_that_contain_sk_dash_stay_visible(text):
    assert redact(text) == text


@pytest.mark.parametrize(
    "text",
    [
        'const k = "sk-proj-a1b2c3d4e5"',
        "OPENAI_API_KEY=sk-a1b2c3d4e5f6",
        "Authorization: Bearer sk_live_a1b2c3d4e5",
    ],
)
def test_key_shaped_values_are_hidden(text):
    out = redact(text)
    assert "[hidden]" in out
    assert "a1b2c3d4e5" not in out
