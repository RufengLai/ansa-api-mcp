"""Parse ANSA Sphinx HTML API documentation into structured function dicts."""

from __future__ import annotations

import os
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag


def _extract_signature(dt: Tag) -> str:
    """Build a clean signature string from the <dt class='sig sig-object py'> tag."""
    prename = dt.find("span", class_="sig-prename descclassname")
    name = dt.find("span", class_="sig-name descname")
    params = dt.find_all("em", class_="sig-param")
    ret_type = dt.find("span", class_="sig-return-typehint")

    module_prefix = prename.get_text(strip=True) if prename else ""
    func_name = name.get_text(strip=True) if name else ""
    param_parts = [p.get_text(strip=True) for p in params]
    ret = ret_type.get_text(strip=True) if ret_type else ""

    sig = f"{module_prefix}{func_name}({', '.join(param_parts)})"
    if ret:
        sig += f" -> {ret}"
    return sig


def _extract_function_name(dt: Tag) -> str:
    """Extract the bare function name from the <dt> tag."""
    name_span = dt.find("span", class_="sig-name descname")
    if name_span:
        return name_span.get_text(strip=True)
    # Fallback: use the id attribute
    func_id = dt.get("id", "")
    return func_id.rsplit(".", 1)[-1] if func_id else ""


def _extract_description(dd: Tag) -> str:
    """Extract the description text from the <dd> block of a function."""
    line_block = dd.find("div", class_="line-block")
    if not line_block:
        return ""
    lines = []
    for div in line_block.find_all("div", class_="line", recursive=False):
        text = div.get_text(strip=True)
        if text:
            lines.append(text)
    return "\n".join(lines)


def _extract_parameters(dd: Tag) -> list[dict]:
    """Extract parameter list from the <dd> block."""
    params = []
    field_list = dd.find("dl", class_="field-list")
    if not field_list:
        return params

    # Find the Parameters section
    for dt_field in field_list.find_all("dt", recursive=False):
        dt_text = dt_field.get_text(strip=True)
        if dt_text.startswith("Parameters"):
            # The next sibling <dd> contains the parameter <dl>
            dd_params = dt_field.find_next_sibling("dd")
            if not dd_params:
                continue
            param_dl = dd_params.find("dl")
            if not param_dl:
                continue

            # Each parameter is a <dt> followed by a <dd>
            children = list(param_dl.children)
            i = 0
            while i < len(children):
                child = children[i]
                if isinstance(child, Tag) and child.name == "dt":
                    param_name = ""
                    param_type = ""
                    # <strong>param_name</strong><span class="classifier">type</span>
                    strong = child.find("strong")
                    if strong:
                        param_name = strong.get_text(strip=True)
                    classifier = child.find("span", class_="classifier")
                    if classifier:
                        param_type = classifier.get_text(strip=True)

                    param_desc = ""
                    # Next sibling should be <dd> with description
                    j = i + 1
                    while j < len(children):
                        next_child = children[j]
                        if isinstance(next_child, Tag) and next_child.name == "dd":
                            param_desc = _extract_description(next_child)
                            i = j  # skip past this dd
                            break
                        j += 1

                    if param_name:
                        params.append({
                            "name": param_name,
                            "type": param_type,
                            "desc": param_desc,
                        })
                i += 1
            break

    return params


def _extract_returns(dd: Tag) -> str:
    """Extract return value description from the <dd> block."""
    field_list = dd.find("dl", class_="field-list")
    if not field_list:
        return ""

    for dt_field in field_list.find_all("dt", recursive=False):
        dt_text = dt_field.get_text(strip=True)
        if dt_text.startswith("Returns"):
            dd_ret = dt_field.find_next_sibling("dd")
            if not dd_ret:
                continue
            ret_dl = dd_ret.find("dl")
            if not ret_dl:
                continue
            # The <dd> inside the returns <dl> has the description
            ret_dd = ret_dl.find("dd")
            if ret_dd:
                return _extract_description(ret_dd)
            # Fallback: get all text
            return ret_dl.get_text(strip=True)
    return ""


def _extract_examples(dd: Tag) -> str:
    """Extract example code from the <dd> block."""
    # Look for the Examples rubric
    rubric = dd.find("p", class_="rubric")
    if not rubric:
        return ""

    rubric_text = rubric.get_text(strip=True)
    if "Examples" not in rubric_text and "Example" not in rubric_text:
        return ""

    # The code block follows the rubric
    highlight = rubric.find_next_sibling("div", class_=re.compile(r"highlight"))
    if not highlight:
        return ""

    pre = highlight.find("pre")
    if pre:
        return pre.get_text()
    return highlight.get_text()


def _parse_function_block(func_dl: Tag, module_name: str) -> dict | None:
    """Parse a single <dl class='py function'> block into a function dict."""
    dt = func_dl.find("dt", class_="sig sig-object py", recursive=False)
    if not dt:
        return None

    dd = func_dl.find("dd", recursive=False)
    if not dd:
        return None

    name = _extract_function_name(dt)
    signature = _extract_signature(dt)
    description = _extract_description(dd)
    parameters = _extract_parameters(dd)
    returns = _extract_returns(dd)
    examples = _extract_examples(dd)

    return {
        "name": name,
        "module": module_name,
        "signature": signature,
        "description": description,
        "parameters": parameters,
        "returns": returns,
        "examples": examples,
    }


def parse_html_file(html_path: str) -> list[dict]:
    """Parse one ANSA Sphinx HTML file into a list of function dicts.

    Args:
        html_path: Path to an HTML file (e.g., ansa.mesh.html).

    Returns:
        List of dicts, one per function found in the file.
    """
    path = Path(html_path)
    # Derive module name from filename: "ansa.mesh.html" -> "ansa.mesh"
    module_name = path.stem

    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    results = []
    for func_dl in soup.find_all("dl", class_="py function"):
        func_dict = _parse_function_block(func_dl, module_name)
        if func_dict:
            results.append(func_dict)

    return results


def parse_all_html(html_dir: str) -> list[dict]:
    """Parse all HTML files in a directory.

    Args:
        html_dir: Path to directory containing ANSA Sphinx HTML files.

    Returns:
        Combined list of function dicts from all HTML files.
    """
    results = []
    dir_path = Path(html_dir)
    for html_file in sorted(dir_path.glob("*.html")):
        results.extend(parse_html_file(str(html_file)))
    return results
