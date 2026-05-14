import pytest
from tools.generate_keywords import generate_keywords_for_functions, _build_prompt, _parse_keywords_response


def test_build_prompt():
    functions = [
        {
            "name": "DeleteElements",
            "module": "ansa.mesh",
            "description": "Delete the given elements from the model.",
            "parameters": [{"name": "elements", "type": "Entity", "desc": "Elements to delete"}],
        }
    ]
    prompt = _build_prompt(functions)
    assert "DeleteElements" in prompt
    assert "ansa.mesh" in prompt
    assert "Delete the given elements" in prompt
    assert "keywords" in prompt.lower()


def test_parse_keywords_response():
    response = """```json
[
  {"name": "DeleteElements", "module": "ansa.mesh", "keywords": ["delete", "remove", "elements", "mesh", "删除", "网格", "单元"]}
]
```"""
    result = _parse_keywords_response(response)
    assert len(result) == 1
    assert result[0]["name"] == "DeleteElements"
    assert "delete" in result[0]["keywords"]
    assert "删除" in result[0]["keywords"]


def test_parse_keywords_response_malformed():
    response = "This is not valid JSON"
    result = _parse_keywords_response(response)
    assert result == []
