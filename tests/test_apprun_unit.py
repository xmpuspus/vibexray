"""Unit tests for app-run helpers. Input lines come from real Vite and Next.js runs."""

import pytest
from conftest import corpus_repo

from vibexray.apprun_boot import (
    detect_package_manager,
    detect_script,
    find_env_names,
    parse_url,
)
from vibexray.apprun_crawl import find_routes

# Captured from `npm run dev` in milk-me-not (Vite 8) and ai-customer-support-agent (Next 14).
VITE_LINE = "  \x1b[32m\u279c\x1b[39m  \x1b[1mLocal\x1b[22m:   \x1b[36mhttp://localhost:\x1b[1m3988\x1b[22m/\x1b[39m"
VITE_PLAIN = "  \u279c  Local:   http://localhost:3988/"
NEXT_LINE = "  - Local:        http://localhost:3987"
NETWORK_LINE = "  \u279c  Network: http://192.168.1.149:3988/  en0"


def test_parse_url_vite_plain():
    assert parse_url(VITE_PLAIN) == "http://localhost:3988"


def test_parse_url_vite_with_color_codes():
    assert parse_url(VITE_LINE) == "http://localhost:3988"


def test_parse_url_next():
    assert parse_url(NEXT_LINE) == "http://localhost:3987"


def test_parse_url_ignores_network_and_noise():
    assert parse_url(NETWORK_LINE) is None
    assert parse_url("  VITE v8.3.1  ready in 2991 ms") is None


def test_parse_url_accepts_127_and_0000():
    assert parse_url("Listening on http://127.0.0.1:8080") == "http://127.0.0.1:8080"
    assert parse_url("started at http://0.0.0.0:4000/") == "http://localhost:4000"


def test_package_manager_from_lockfile(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert detect_package_manager(tmp_path) == "npm"
    (tmp_path / "yarn.lock").write_text("")
    assert detect_package_manager(tmp_path) == "yarn"
    (tmp_path / "pnpm-lock.yaml").write_text("")
    assert detect_package_manager(tmp_path) == "pnpm"
    (tmp_path / "bun.lock").write_text("")
    assert detect_package_manager(tmp_path) == "bun"


def test_script_order_dev_start_preview():
    assert detect_script({"scripts": {"start": "x", "preview": "y", "dev": "z"}}) == "dev"
    assert detect_script({"scripts": {"start": "x", "preview": "y"}}) == "start"
    assert detect_script({"scripts": {"preview": "y"}}) == "preview"
    assert detect_script({"scripts": {"build": "y"}}) is None
    assert detect_script({}) is None


def test_script_list_that_is_not_an_object_finds_nothing():
    # "dev" in "dev" is True for a string, so a string must not count as a script table.
    assert detect_script({"scripts": "dev"}) is None
    assert detect_script({"scripts": ["dev"]}) is None


@pytest.mark.corpus
def test_env_names_from_real_repo():
    names = find_env_names(corpus_repo("ai-customer-support-agent"))
    assert "DATABASE_URL" in names
    assert "OPENAI_API_KEY" in names
    assert "PORT" not in names and "NODE_ENV" not in names


@pytest.mark.corpus
def test_routes_from_real_next_app():
    routes = find_routes(corpus_repo("ai-customer-support-agent"))
    assert routes[0] == "/"
    assert "/chat" in routes and "/admin/login" in routes
    assert not any("[" in r or r.startswith("/api") for r in routes)
