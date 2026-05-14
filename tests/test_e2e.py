"""End-to-end integration tests for the ANSA API search pipeline.

These tests exercise the full flow from HTML parsing through index generation
to search, using a small subset (ansa.mesh.html) to keep runtime fast.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from tools.parse_html import parse_html_file
from tools.generate_index import assign_categories, save_index
from tools.mcp_server import AnsaApiSearcher

# Path to the real ANSA HTML documentation
_HTML_DOCS_DIR = (
    "C:/Users/MI/AppData/Local/Apps/BETA_CAE_Systems/"
    "ansa_v24.1.1/docs/extending/python_api/html/reference/"
    "api_ref_ansa/generated"
)
_MESH_HTML = os.path.join(_HTML_DOCS_DIR, "ansa.mesh.html")


def _fake_keywords(func_name: str) -> list[str]:
    """Generate simple fake keywords based on tokens in the function name.

    Maps common English substrings to both English and Chinese equivalents so
    that Chinese-language queries (e.g. "网格") can be tested without an LLM.
    """
    mapping = {
        "mesh": ["mesh", "网格"],
        "delete": ["delete", "删除"],
        "remove": ["remove", "删除"],
        "create": ["create", "创建"],
        "element": ["element", "单元"],
        "node": ["node", "节点"],
        "align": ["align", "对齐"],
        "merge": ["merge", "合并"],
        "quality": ["quality", "质量"],
        "check": ["check", "检查"],
        "fix": ["fix", "修复"],
        "free": ["free", "自由"],
        "edge": ["edge", "边"],
        "face": ["face", "面"],
        "surface": ["surface", "曲面"],
        "shrink": ["shrink", "收缩"],
        "wrap": ["wrap", "包裹"],
    }
    keywords: list[str] = []
    lower = func_name.lower()
    for token, kws in mapping.items():
        if token in lower:
            keywords.extend(kws)
    return keywords


@pytest.fixture()
def mini_index():
    """Build a minimal search index from ansa.mesh.html only.

    Steps:
      1. Parse ansa.mesh.html into function dicts.
      2. Add fake keywords derived from each function name.
      3. Overwrite category to "mesh_edit" (simplified rule).
      4. Save to a temporary JSON file.

    Yields the path to the temporary index file, then removes it.
    """
    functions = parse_html_file(_MESH_HTML)
    assert len(functions) > 0, "ansa.mesh.html produced no functions"

    for func in functions:
        func["keywords"] = _fake_keywords(func["name"])
        func["category"] = "mesh_edit"

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        save_index(functions, tmp.name, api_version="test-mini")
        tmp.close()
        yield tmp.name
    finally:
        if not tmp.closed:
            tmp.close()
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_e2e_search_by_keyword(mini_index: str):
    """Search for the Chinese keyword "网格" (mesh) and verify that
    functions whose names contain "mesh" are returned."""
    searcher = AnsaApiSearcher(mini_index, txt_docs_path="")
    results = searcher.search("网格", top_n=10)
    assert len(results) > 0, "Expected at least one result for '网格'"

    # Every result should be mesh-related (name contains "mesh", case-insensitive,
    # or module is ansa.mesh).
    for r in results:
        assert r["module"] == "ansa.mesh", (
            f"Non-mesh function {r['name']} returned for query '网格'"
        )

    # At least one result should have "mesh" (case-insensitive) in its name
    assert any("mesh" in r["name"].lower() for r in results), (
        "Expected at least one result with 'mesh' in the function name"
    )


def test_e2e_search_by_function_name(mini_index: str):
    """Search for the exact function name 'AlignMeshToMesh' and verify it appears."""
    searcher = AnsaApiSearcher(mini_index, txt_docs_path="")
    results = searcher.search("AlignMeshToMesh", top_n=20)
    names = [r["name"] for r in results]
    assert "AlignMeshToMesh" in names, (
        f"AlignMeshToMesh not found; got: {names}"
    )


def test_e2e_search_result_has_example(mini_index: str):
    """Search for 'mesh' and verify at least one result includes example code."""
    searcher = AnsaApiSearcher(mini_index, txt_docs_path="")
    results = searcher.search("mesh", top_n=10)
    assert len(results) > 0, "Expected at least one result for 'mesh'"

    has_example = any(r.get("examples") for r in results)
    assert has_example, "None of the search results contained example code"


def test_e2e_full_pipeline(tmp_path):
    """Exercise the full pipeline: parse -> categorize -> save -> search.

    Uses the real parse_html_file -> assign_categories -> save_index path
    without hand-editing fields, to verify the assembled pipeline works end-to-end.
    """
    # 1. Parse
    functions = parse_html_file(_MESH_HTML)
    assert len(functions) > 0

    # 2. Categorize
    assign_categories(functions)
    for func in functions:
        assert "category" in func
        # ansa.mesh functions should get a mesh_* category
        assert func["category"].startswith("mesh_"), (
            f"Unexpected category '{func['category']}' for {func['name']}"
        )

    # Inject keywords so the searcher can find things
    for func in functions:
        func["keywords"] = _fake_keywords(func["name"])

    # 3. Save
    index_path = str(tmp_path / "index.json")
    save_index(functions, index_path, api_version="e2e-test")
    assert os.path.exists(index_path)

    # Verify structure
    with open(index_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["metadata"]["api_version"] == "e2e-test"
    assert data["metadata"]["total_functions"] == len(functions)
    assert "ansa.mesh" in data["metadata"]["modules"]

    # 4. Search
    searcher = AnsaApiSearcher(index_path, txt_docs_path="")
    results = searcher.search("mesh", top_n=5)
    assert len(results) > 0, "Full pipeline produced no search results"

    # Verify result structure
    for r in results:
        for key in ("name", "module", "signature", "description", "category"):
            assert key in r, f"Missing key '{key}' in result"
