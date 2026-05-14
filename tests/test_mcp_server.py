import json
import os
import tempfile
import pytest
from tools.mcp_server import AnsaApiSearcher


@pytest.fixture
def sample_index():
    data = {
        "metadata": {"api_version": "test", "total_functions": 3, "modules": ["ansa.mesh", "ansa.base"]},
        "functions": [
            {
                "name": "DeleteElements",
                "module": "ansa.mesh",
                "signature": "ansa.mesh.DeleteElements(elements, fix_free_edges=False) -> int",
                "description": "Delete the given elements from the model.",
                "parameters": [
                    {"name": "elements", "type": "Entity | list", "desc": "Elements to delete"},
                    {"name": "fix_free_edges", "type": "bool", "desc": "Fix free edges after deletion"},
                ],
                "returns": "int — Number of deleted elements",
                "examples": "import ansa\nansa.mesh.DeleteElements(elems)",
                "keywords": ["delete", "remove", "elements", "mesh", "删除", "网格", "单元"],
                "category": "mesh_edit",
            },
            {
                "name": "CreateMesh",
                "module": "ansa.mesh",
                "signature": "ansa.mesh.CreateMesh(entities, target_length) -> list",
                "description": "Create mesh on the given entities.",
                "parameters": [
                    {"name": "entities", "type": "Entity | list", "desc": "Entities to mesh"},
                    {"name": "target_length", "type": "float", "desc": "Target element length"},
                ],
                "returns": "list — Created elements",
                "examples": "ansa.mesh.CreateMesh(parts, 5.0)",
                "keywords": ["create", "mesh", "generate", "创建", "网格", "生成"],
                "category": "mesh_edit",
            },
            {
                "name": "GetEntity",
                "module": "ansa.base",
                "signature": "ansa.base.GetEntity(solver, type_, id_) -> Entity",
                "description": "Get an entity by solver type and ID.",
                "parameters": [
                    {"name": "solver", "type": "int", "desc": "Solver constant"},
                    {"name": "type_", "type": "str", "desc": "Entity type name"},
                    {"name": "id_", "type": "int", "desc": "Entity ID"},
                ],
                "returns": "Entity — The found entity or None",
                "examples": "e = ansa.base.GetEntity(constants.ABAQUS, 'SHELL_SECTION', 1)",
                "keywords": ["get", "entity", "find", "lookup", "获取", "实体", "查找"],
                "category": "base_query",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        tmp_path = f.name
    yield tmp_path
    os.unlink(tmp_path)


def test_searcher_loads_index(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    assert len(searcher.functions) == 3


def test_search_keyword_match(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("删除网格")
    names = [r["name"] for r in results]
    assert "DeleteElements" in names


def test_search_english(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("delete elements")
    names = [r["name"] for r in results]
    assert "DeleteElements" in names


def test_search_module_filter(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("get", module="ansa.base")
    names = [r["name"] for r in results]
    assert "GetEntity" in names
    assert "DeleteElements" not in names


def test_search_category_filter(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("mesh", category="mesh_edit")
    assert all(r["category"] == "mesh_edit" for r in results)


def test_search_top_n(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("mesh", top_n=1)
    assert len(results) <= 1


def test_search_fuzzy_fallback(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("entities")
    assert len(results) > 0


def test_search_no_results(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("xyznonexistent123")
    assert len(results) == 0


def test_search_result_format(sample_index):
    searcher = AnsaApiSearcher(sample_index)
    results = searcher.search("delete")
    assert len(results) > 0
    r = results[0]
    for key in ("name", "module", "signature", "description", "parameters", "returns", "examples"):
        assert key in r
