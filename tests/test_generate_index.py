import json
import os
import tempfile
import pytest
from tools.generate_index import assign_categories, build_index, save_index


def test_assign_categories_mesh():
    func = {"name": "DeleteElements", "module": "ansa.mesh", "description": "Delete elements"}
    assign_categories([func])
    assert func["category"] in ("mesh_edit", "mesh_quality", "mesh_cfd", "mesh_other")


def test_assign_categories_base():
    func = {"name": "GetEntity", "module": "ansa.base", "description": "Get an entity"}
    assign_categories([func])
    assert func["category"].startswith("base_")


def test_save_index():
    functions = [
        {
            "name": "TestFunc", "module": "ansa.test", "signature": "ansa.test.TestFunc()",
            "description": "Test", "parameters": [], "returns": "", "examples": "",
            "keywords": ["test"], "category": "test",
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name
    try:
        save_index(functions, tmp_path, api_version="test_v1")
        with open(tmp_path) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "functions" in data
        assert data["metadata"]["api_version"] == "test_v1"
        assert data["metadata"]["total_functions"] == 1
        assert len(data["functions"]) == 1
    finally:
        os.unlink(tmp_path)
