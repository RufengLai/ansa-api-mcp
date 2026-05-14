import os
import pytest
from tools.parse_html import parse_html_file, parse_all_html

DOCS_DIR = "C:/Users/MI/AppData/Local/Apps/BETA_CAE_Systems/ansa_v24.1.1/docs/extending/python_api/html/reference/api_ref_ansa/generated"


def test_parse_html_file_returns_list():
    path = os.path.join(DOCS_DIR, "ansa.mesh.html")
    result = parse_html_file(path)
    assert isinstance(result, list)
    assert len(result) > 0


def test_parse_html_file_function_fields():
    path = os.path.join(DOCS_DIR, "ansa.mesh.html")
    result = parse_html_file(path)
    func = result[0]
    for key in ("name", "module", "signature", "description", "parameters", "returns", "examples"):
        assert key in func


def test_parse_html_file_module_name():
    path = os.path.join(DOCS_DIR, "ansa.mesh.html")
    result = parse_html_file(path)
    assert all(f["module"] == "ansa.mesh" for f in result)


def test_parse_html_file_align_mesh():
    path = os.path.join(DOCS_DIR, "ansa.mesh.html")
    result = parse_html_file(path)
    align = [f for f in result if f["name"] == "AlignMeshToMesh"]
    assert len(align) == 1
    func = align[0]
    assert func["module"] == "ansa.mesh"
    assert "source_part" in func["signature"]
    assert len(func["parameters"]) >= 2


def test_parse_html_file_parameters_structure():
    path = os.path.join(DOCS_DIR, "ansa.mesh.html")
    result = parse_html_file(path)
    func = result[0]
    param = func["parameters"][0]
    assert "name" in param
    assert "type" in param
    assert "desc" in param


def test_parse_html_file_examples():
    path = os.path.join(DOCS_DIR, "ansa.mesh.html")
    result = parse_html_file(path)
    funcs_with_examples = [f for f in result if f["examples"]]
    assert len(funcs_with_examples) > 0
    assert "import" in funcs_with_examples[0]["examples"]


def test_parse_all_html():
    result = parse_all_html(DOCS_DIR)
    assert isinstance(result, list)
    assert len(result) > 100
    modules = set(f["module"] for f in result)
    assert "ansa.mesh" in modules
    assert "ansa.base" in modules
