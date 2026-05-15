"""Assemble the ANSA API search index from parsed HTML and keyword generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from tools.parse_html import parse_all_html
from tools.generate_keywords import generate_keywords_for_functions


# ---------------------------------------------------------------------------
# Category assignment
# ---------------------------------------------------------------------------

_MESH_EDIT_KEYWORDS = ("delete", "remove", "clear")
_MESH_QUALITY_KEYWORDS = ("check", "quality", "length", "angle", "warpage", "aspect")
_MESH_CFD_KEYWORDS = ("cfd", "boundary", "inflation")

_BASE_QUERY_KEYWORDS = ("get", "collect", "find", "filter")
_BASE_MODIFY_KEYWORDS = ("set", "create", "delete", "remove")
_BASE_CHECK_KEYWORDS = ("check", "quality")
_BASE_TRANSFORM_KEYWORDS = ("transform", "move", "rotate", "mirror")


def _name_matches(name: str, keywords: tuple[str, ...]) -> bool:
    """Return True if the lowercased function name contains any of the keywords."""
    lower = name.lower()
    return any(kw in lower for kw in keywords)


def assign_categories(functions: list[dict]) -> None:
    """Assign a ``category`` field to each function dict in-place.

    Rules
    -----
    - **ansa.mesh**: mesh_edit, mesh_quality, mesh_cfd, mesh_other
    - **ansa.base**: base_query, base_modify, base_check, base_transform, base_other
    - **All other modules**: category = module name (e.g. ``morph``, ``connection``)
    - **Fallback**: ``"other"``
    """
    for func in functions:
        module: str = func.get("module", "")
        name: str = func.get("name", "")

        if module == "ansa.mesh":
            if _name_matches(name, _MESH_EDIT_KEYWORDS):
                func["category"] = "mesh_edit"
            elif _name_matches(name, _MESH_QUALITY_KEYWORDS):
                func["category"] = "mesh_quality"
            elif _name_matches(name, _MESH_CFD_KEYWORDS):
                func["category"] = "mesh_cfd"
            else:
                func["category"] = "mesh_other"

        elif module == "ansa.base":
            if _name_matches(name, _BASE_QUERY_KEYWORDS):
                func["category"] = "base_query"
            elif _name_matches(name, _BASE_MODIFY_KEYWORDS):
                func["category"] = "base_modify"
            elif _name_matches(name, _BASE_CHECK_KEYWORDS):
                func["category"] = "base_check"
            elif _name_matches(name, _BASE_TRANSFORM_KEYWORDS):
                func["category"] = "base_transform"
            else:
                func["category"] = "base_other"

        else:
            # Strip the "ansa." prefix if present to get the bare module name.
            bare = module.replace("ansa.", "") if module.startswith("ansa.") else module
            func["category"] = bare if bare else "other"


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_index(html_dir: str, api_key: str | None = None) -> list[dict]:
    """Orchestrate the full index build pipeline.

    Steps:
    1. Parse all ANSA HTML documentation files.
    2. Assign categories to every function.
    3. Generate search keywords (requires an API key).
    4. Return the enriched function list.

    Args:
        html_dir: Path to directory containing ANSA Sphinx HTML files.
        api_key: Anthropic API key for keyword generation.  When ``None`` the
            keyword generation step is skipped.

    Returns:
        List of function dicts with category and keywords fields populated.
    """
    functions = parse_all_html(html_dir)
    assign_categories(functions)

    import os
    effective_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if effective_key:
        functions = generate_keywords_for_functions(functions, api_key=effective_key)
    else:
        for func in functions:
            func.setdefault("keywords", [])

    return functions


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def save_index(
    functions: list[dict],
    output_path: str,
    api_version: str = "v24.1.1",
) -> None:
    """Save the function index to a JSON file with metadata.

    Args:
        functions: List of function dicts (as returned by :func:`build_index`).
        output_path: Destination file path.
        api_version: Version label to embed in the metadata.
    """
    modules = sorted({func["module"] for func in functions})

    data = {
        "metadata": {
            "api_version": api_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_functions": len(functions),
            "modules": modules,
        },
        "functions": functions,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import sys

    _DOCS_DIR = (
        "C:/Users/MI/AppData/Local/Apps/BETA_CAE_Systems/"
        "ansa_v24.1.1/docs/extending/python_api/html/reference/"
        "api_ref_ansa/generated"
    )
    _OUTPUT = os.path.join(os.path.dirname(__file__), "ansa_api_index.json")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    print(f"Parsing HTML from {_DOCS_DIR} ...", flush=True)
    functions = parse_all_html(_DOCS_DIR)
    print(f"  Found {len(functions)} functions.", flush=True)

    print("Assigning categories ...", flush=True)
    assign_categories(functions)

    if api_key:
        print(f"Generating keywords via API (batches of 25) ...", flush=True)
        functions = generate_keywords_for_functions(functions, api_key=api_key, batch_size=10)
        funcs_kw = sum(1 for f in functions if f.get("keywords"))
        print(f"  {funcs_kw}/{len(functions)} functions have keywords.", flush=True)
    else:
        print("No API key found, skipping keyword generation.", flush=True)
        for f in functions:
            f.setdefault("keywords", [])

    save_index(functions, _OUTPUT)
    print(f"Index saved to {_OUTPUT}")
