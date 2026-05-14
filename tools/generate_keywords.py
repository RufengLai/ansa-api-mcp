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
Generate search keywords for each API function below so users can find them via English queries.

For each function, generate 5-10 English keywords including:
- Words from the function name and description
- Common synonyms (e.g., "delete" also matches "remove", "erase")
- Related technical terms

Functions:
{functions_text}

Return ONLY a JSON array (no explanation), in this exact format:
[{{"name": "FuncName", "module": "ansa.module", "keywords": ["kw1", "kw2", ...]}}]

Each entry must have "name", "module", and "keywords" (a list of English strings only).
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


# English → Chinese keyword mapping for CAE/ANSA domain
_EN_TO_CN: dict[str, str] = {
    "delete": "删除", "remove": "删除", "erase": "删除", "clear": "清除",
    "create": "创建", "new": "新建", "add": "添加",
    "get": "获取", "find": "查找", "search": "搜索", "query": "查询", "collect": "收集", "filter": "筛选", "select": "选择",
    "set": "设置", "update": "更新", "modify": "修改", "change": "改变",
    "mesh": "网格", "element": "单元", "node": "节点", "face": "面", "edge": "边",
    "property": "属性", "part": "部件", "section": "截面", "material": "材料",
    "surface": "曲面", "curve": "曲线", "point": "点", "geometry": "几何",
    "connection": "连接", "contact": "接触", "constraint": "约束", "boundary": "边界",
    "load": "载荷", "force": "力", "pressure": "压力", "displacement": "位移",
    "check": "检查", "quality": "质量", "fix": "修复", "repair": "修复",
    "measure": "测量", "calculate": "计算", "compute": "计算",
    "transform": "变换", "move": "移动", "rotate": "旋转", "mirror": "镜像", "scale": "缩放",
    "merge": "合并", "split": "分割", "trim": "裁剪", "extend": "延伸",
    "export": "导出", "import": "导入", "save": "保存", "load": "加载", "read": "读取", "write": "写入",
    "group": "组", "set": "集合", "list": "列表",
    "align": "对齐", "project": "投影", "offset": "偏移",
    "penetration": "穿透", "intersection": "交叉", "overlap": "重叠",
    "thickness": "厚度", "length": "长度", "angle": "角度", "area": "面积", "volume": "体积",
    "display": "显示", "hide": "隐藏", "show": "显示", "view": "视图",
    "run": "运行", "execute": "执行", "script": "脚本",
    "solver": "求解器", "analysis": "分析", "simulation": "仿真",
    "model": "模型", "entity": "实体", "type": "类型",
    "configure": "配置", "setting": "设置", "option": "选项",
    "report": "报告", "result": "结果", "output": "输出",
    "batch": "批量", "macro": "宏", "function": "函数",
    "coordinate": "坐标", "system": "系统",
    "free": "自由", "fixed": "固定", "rigid": "刚性",
    "shell": "壳", "solid": "体", "beam": "梁",
    "tetra": "四面体", "hexa": "六面体", "penta": "五面体",
    "morph": "变形", "morphing": "变形",
    "kinematics": "运动学", "joint": "关节", "spring": "弹簧", "damper": "阻尼",
}


def _is_clean_ascii(s: str) -> bool:
    """Check if string is clean ASCII (no garbled encoding artifacts)."""
    return all(ord(c) < 128 for c in s)


def _add_chinese_keywords(keywords: list[str]) -> list[str]:
    """Add Chinese translations for English keywords using the mapping table.

    Filters out any non-ASCII keywords from the API (which may be garbled)
    and replaces them with proper Chinese translations from the mapping.
    """
    # Keep only clean ASCII keywords
    clean = [kw for kw in keywords if _is_clean_ascii(kw)]
    result = list(clean)
    seen = set(k.lower() for k in result)

    for kw in clean:
        kw_lower = kw.lower()
        if kw_lower in _EN_TO_CN:
            cn = _EN_TO_CN[kw_lower]
            if cn.lower() not in seen:
                result.append(cn)
                seen.add(cn.lower())

    return result


def generate_keywords_for_functions(
    functions: list[dict],
    api_key: str | None = None,
    model: str = "xiaomi/mimo-v2.5-pro",
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
                    func_lookup[key]["keywords"] = _add_chinese_keywords(item["keywords"])

        except Exception:
            # On any failure, functions keep their default empty keywords
            pass

    return functions
