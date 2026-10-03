"""All rules in one list. Each category module exposes RULES."""

from __future__ import annotations

from vibexray.rules import (
    ai,
    auth,
    database,
    exposed_keys,
    fake_action,
    hardcoded,
    mock_data,
    security,
)
from vibexray.rules.base import Rule

MODULES = [mock_data, fake_action, auth, database, exposed_keys, hardcoded, ai, security]

RULES: list[Rule] = [rule for module in MODULES for rule in module.RULES]
