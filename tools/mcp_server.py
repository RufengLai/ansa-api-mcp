"""MCP Server for searching ANSA Python API documentation.

Provides a three-layer search (keyword, fuzzy, txt fallback) over
a pre-built index of ANSA API functions.
"""

import json
import os
import re
import unicodedata
from importlib.resources import files
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP


def _tokenize(text: str) -> list[str]:
    """Split text into tokens: words, individual CJK chars, punctuation-separated segments."""
    tokens: list[str] = []
    current: list[str] = []
    for ch in text:
        # CJK Unified Ideographs and extensions
        if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿":
            if current:
                tokens.append("".join(current))
                current = []
            tokens.append(ch)
        elif ch.isalnum() or ch == "_":
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return [t.lower() for t in tokens if t]


class AnsaApiSearcher:
    """Search ANSA API functions using a pre-built index with txt fallback."""

    def __init__(self, index_path: str, txt_docs_path: str = ""):
        self.txt_docs_path = txt_docs_path
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        self.metadata = data.get("metadata", {})
        self.functions: list[dict] = data.get("functions", [])
        # Pre-compute lowercased keywords for each function
        for func in self.functions:
            func["_keywords_lower"] = [kw.lower() for kw in func.get("keywords", [])]

    def search(
        self,
        query: str,
        module: Optional[str] = None,
        category: Optional[str] = None,
        top_n: int = 5,
    ) -> list[dict]:
        """Three-layer search: keyword -> fuzzy -> txt fallback."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Apply filters
        candidates = self.functions
        if module:
            candidates = [f for f in candidates if f.get("module") == module]
        if category:
            candidates = [f for f in candidates if f.get("category") == category]

        # Layer 1: keyword match — check if keywords appear as substrings of the query
        query_lower = query.lower()
        scored: list[tuple[int, dict]] = []
        for func in candidates:
            kw_lower = func["_keywords_lower"]
            match_count = sum(1 for kw in kw_lower if kw in query_lower)
            if match_count == 0:
                # Also check if query tokens appear as keywords
                match_count = sum(1 for tok in query_tokens if tok in kw_lower)
            if match_count > 0:
                scored.append((match_count, func))
        scored.sort(key=lambda x: -x[0])
        results = [func for _, func in scored]

        # Layer 2: fuzzy fallback on description + signature
        if len(results) < top_n:
            already = {id(f) for f in results}
            for func in candidates:
                if id(func) in already:
                    continue
                searchable = (func.get("description", "") + " " + func.get("signature", "")).lower()
                if any(tok in searchable for tok in query_tokens):
                    results.append(func)

        # Layer 3: txt file fallback
        if len(results) < top_n and self.txt_docs_path and os.path.isdir(self.txt_docs_path):
            already = {id(f) for f in results}
            found_names = {f["name"] for f in results}
            query_lower = query.lower()
            for fname in os.listdir(self.txt_docs_path):
                if not fname.endswith(".txt"):
                    continue
                fpath = os.path.join(self.txt_docs_path, fname)
                try:
                    with open(fpath, encoding="utf-8") as tf:
                        content = tf.read()
                except Exception:
                    continue
                if query_lower not in content.lower():
                    continue
                # Extract function names near matches
                for func in candidates:
                    if id(func) in already or func["name"] in found_names:
                        continue
                    if func["name"].lower() in content.lower():
                        results.append(func)
                        found_names.add(func["name"])

        # Trim to top_n
        results = results[:top_n]

        # Strip internal fields before returning
        clean: list[dict] = []
        for func in results:
            clean.append({k: v for k, v in func.items() if not k.startswith("_")})
        return clean


# Default paths
_INDEX_PATH = str(files("tools").joinpath("ansa_api_index.json"))
_TXT_DOCS_PATH = os.environ.get("ANSA_TXT_DOCS_PATH", "")

# MCP server instance
mcp = FastMCP("ansa-api")

# Module-level searcher (initialized if index exists)
_searcher: Optional[AnsaApiSearcher] = None


def _get_searcher() -> AnsaApiSearcher:
    global _searcher
    if _searcher is None:
        if not os.path.exists(_INDEX_PATH):
            raise FileNotFoundError(f"Index file not found: {_INDEX_PATH}")
        _searcher = AnsaApiSearcher(_INDEX_PATH, _TXT_DOCS_PATH)
    return _searcher


def _format_result(func: dict) -> str:
    """Format a single search result as markdown."""
    lines = [f"### `{func['signature']}`"]
    lines.append(f"**Module:** {func.get('module', 'N/A')}")
    lines.append(f"**Category:** {func.get('category', 'N/A')}")
    lines.append("")
    lines.append(func.get("description", ""))
    lines.append("")

    params = func.get("parameters", [])
    if params:
        lines.append("**Parameters:**")
        for p in params:
            lines.append(f"- `{p['name']}` ({p.get('type', 'any')}): {p.get('desc', '')}")
        lines.append("")

    ret = func.get("returns", "")
    if ret:
        lines.append(f"**Returns:** {ret}")
        lines.append("")

    examples = func.get("examples", "")
    if examples:
        lines.append("**Example:**")
        lines.append("```python")
        lines.append(examples)
        lines.append("```")

    return "\n".join(lines)


@mcp.tool()
def search_ansa_api(
    query: str,
    module: Optional[str] = None,
    category: Optional[str] = None,
    top_n: int = 5,
) -> str:
    """Search the ANSA Python API documentation.

    Args:
        query: Search query (supports Chinese and English keywords)
        module: Filter by module name (e.g. "ansa.mesh", "ansa.base")
        category: Filter by category (e.g. "mesh_edit", "base_query")
        top_n: Maximum number of results to return (default 5)
    """
    searcher = _get_searcher()
    results = searcher.search(query, module=module, category=category, top_n=top_n)

    if not results:
        return f"No results found for query: `{query}`"

    header = f"## ANSA API Search Results for `{query}`\n"
    parts = [header]
    for i, func in enumerate(results, 1):
        parts.append(f"---\n\n**{i}. {func['name']}**\n")
        parts.append(_format_result(func))
        parts.append("")

    return "\n".join(parts)


def _install_mcp():
    """Register this MCP server in Claude Code settings."""
    import json as _json
    import shutil
    import subprocess

    settings_path = Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing settings
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            settings = _json.load(f)
    else:
        settings = {}

    servers = settings.setdefault("mcpServers", {})

    # Check if already registered
    if "ansa-api" in servers:
        print("ansa-api MCP server is already registered in Claude Code.")
        print(f"  Config: {settings_path}")
        return True

    # Find the installed executable
    exe = shutil.which("ansa-api-mcp")
    if not exe:
        print("Error: ansa-api-mcp executable not found in PATH.")
        print("  Make sure pip install completed successfully.")
        return False

    # Register the MCP server
    servers["ansa-api"] = {"command": exe}

    # Write settings back
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        _json.dump(settings, f, indent=2, ensure_ascii=False)

    print(f"Successfully registered ansa-api MCP server in Claude Code!")
    print(f"  Config: {settings_path}")
    print(f"  Command: {exe}")
    print()
    print("Restart Claude Code to start using it.")
    return True


def main():
    """Entry point for the MCP server.

    Usage:
        ansa-api-mcp          Start the MCP server (used by Claude Code)
        ansa-api-mcp install  Register this server in Claude Code settings
    """
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "install":
        success = _install_mcp()
        sys.exit(0 if success else 1)

    mcp.run()


if __name__ == "__main__":
    main()
