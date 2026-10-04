"""The scan lists the prompt, knowledge-base, and data files that the app loads."""

from pathlib import Path

import pytest
from conftest import corpus_repo

from vibexray.parts import context_files
from vibexray.walker import collect_files

FIXTURES = Path(__file__).parent / "fixtures"


def test_a_json_file_in_a_data_folder_is_a_context_file():
    found = context_files(collect_files(FIXTURES / "MIND-MIRROR"))
    assert "src/data/dummyUsers.json" in found
    assert not any(p.endswith("package.json") for p in found)


@pytest.mark.corpus
def test_a_knowledge_base_folder_is_read_and_agent_folders_are_not():
    found = context_files(collect_files(corpus_repo("R3108__Customer_Support_Agent")))
    assert "backend/knowledge_base/returns_refunds.md" in found
    assert "backend/data/orders.json" in found
    assert not any(p.startswith(".") for p in found)


@pytest.mark.corpus
def test_a_data_file_that_the_code_opens_by_name_is_a_context_file():
    found = context_files(collect_files(corpus_repo("solusops__MyGPU")))
    assert "monitor/vram_caps.json" in found


@pytest.mark.corpus
def test_spec_kit_and_test_files_are_not_context_files():
    assert context_files(collect_files(corpus_repo("yedlurisrinu__reno-compass"))) == []
    found = context_files(collect_files(corpus_repo("mentee-global__mentee")))
    assert not any("test" in p for p in found)
