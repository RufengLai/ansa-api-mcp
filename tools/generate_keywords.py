"""Generate search keywords for ANSA API functions using Claude."""

from __future__ import annotations

import json
import os
import re


def _build_prompt(functions: list[dict]) -> str:
    """Build a prompt for Claude to generate keywords for ANSA API functions.

    Args:
        functions: List of function dicts with keys: name, module, description, parameters.

    Returns:
        A prompt string to send to Claude.
    """
    func_descriptions = []
    for func in functions:
        params_str = ", ".join(
            f"{p.get('name', '?')}:{p.get('type', '?')}" for p in func.get("parameters", [])
        )
        func_descriptions.append(
            f"- {func['name']} (module: {func['module']}): {func.get('description', '')}"
            + (f"  Parameters: {params_str}" if params_str else "")
        )

    functions_text = "\n".join(func_descriptions)

    return f"""You are an expert in ANSA (a pre-processing CAE software) Python API.
Generate search keywords for each API function below so users can find them via Chinese or English queries.

For each function, generate 5-10 keywords including:
- English words from the function name and description
- Chinese translations (e.g., "delete" -> "删除", "mesh" -> "网格", "element" -> "单元", "property" -> "属性", "part" -> "部件", "node" -> "节点", "face" -> "面", "curve" -> "曲线", "surface" -> "曲面", "constraint" -> "约束", "load" -> "载荷", "boundary" -> "边界", "material" -> "材料", "section" -> "截面", "group" -> "组", "set" -> "集合", "export" -> "导出", "import" -> "导入", "create" -> "创建", "get" -> "获取", "set" -> "设置", "calculate" -> "计算", "measure" -> "测量", "transform" -> "变换", "merge" -> "合并", "split" -> "分割", "connect" -> "连接", "check" -> "检查", "fix" -> "修复", "quality" -> "质量")
- Common synonyms (e.g., "delete" also matches "remove", "erase")

Functions:
{functions_text}

Return ONLY a JSON array (no explanation), in this exact format:
[{{"name": "FuncName", "module": "ansa.module", "keywords": ["kw1", "kw2", ...]}}]

Each entry must have "name", "module", and "keywords" (a list of strings).
"""


def _parse_keywords_response(response_text: str) -> list[dict]:
    """Parse Claude's JSON response containing generated keywords.

    Handles responses wrapped in markdown code fences (```json ... ```).

    Args:
        response_text: Raw response text from Claude.

    Returns:
        List of dicts with keys: name, module, keywords. Empty list on parse failure.
    """
    text = response_text.strip()

    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(parsed, list):
        return []

    # Validate structure
    result = []
    for item in parsed:
        if isinstance(item, dict) and "name" in item and "module" in item and "keywords" in item:
            result.append(
                {
                    "name": item["name"],
                    "module": item["module"],
                    "keywords": list(item["keywords"]),
                }
            )

    return result


def generate_keywords_for_functions(
    functions: list[dict],
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    batch_size: int = 25,
) -> list[dict]:
    """Generate search keywords for ANSA API functions using the Claude API.

    Processes functions in batches and merges keywords back into function dicts.
    Every function in the returned list will have a 'keywords' field (empty list if generation failed).

    Args:
        functions: List of function dicts with keys: name, module, description, parameters.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        model: Claude model identifier to use.
        batch_size: Number of functions to include per API call.

    Returns:
        List of function dicts, each augmented with a 'keywords' list.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    # Build a lookup from (name, module) -> function dict for merging
    func_lookup: dict[tuple[str, str], dict] = {}
    for func in functions:
        key = (func["name"], func["module"])
        func_lookup[key] = func
        func.setdefault("keywords", [])

    # Process in batches
    for i in range(0, len(functions), batch_size):
        batch = functions[i : i + batch_size]
        prompt = _build_prompt(batch)

        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text
            keywords_data = _parse_keywords_response(response_text)

            # Merge keywords back
            for item in keywords_data:
                key = (item["name"], item["module"])
                if key in func_lookup:
                    func_lookup[key]["keywords"] = item["keywords"]

        except Exception:
            # On any failure, functions keep their default empty keywords
            pass

    return functions
