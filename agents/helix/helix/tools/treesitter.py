"""AST-aware code intelligence using Tree-sitter.

Twist over Coda: instead of plain grep, these tools understand code structure.
  - find_symbol: find function/class definitions by name across all files
  - find_callers: find all call sites of a function
  - outline: get a structural outline (all symbols) of a file
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings


def _get_parser(language: str):
    """Return a tree-sitter parser for the given language."""
    try:
        import tree_sitter_python as tspython  # type: ignore
        import tree_sitter_javascript as tsjs  # type: ignore
        from tree_sitter import Language, Parser  # type: ignore

        lang_map = {
            "python": Language(tspython.language()),
            "javascript": Language(tsjs.language()),
        }
        lang = lang_map.get(language)
        if not lang:
            return None
        parser = Parser(lang)
        return parser
    except Exception:
        return None


def _detect_language(path: Path) -> str | None:
    ext_map = {".py": "python", ".js": "javascript", ".ts": "javascript",
               ".tsx": "javascript", ".jsx": "javascript"}
    return ext_map.get(path.suffix)


def _iter_source_files(repo: str, path: str = "") -> list[Path]:
    base = (settings.repos_dir / repo / path).resolve() if path else settings.repos_dir / repo
    files = []
    for ext in (".py", ".js", ".ts", ".tsx", ".jsx"):
        files.extend(
            f for f in base.rglob(f"*{ext}")
            if not any(p in f.parts for p in (".git", "node_modules", "__pycache__", ".venv"))
        )
    return files


@tool
def find_symbol(
    repo: Annotated[str, "Repository name"],
    name: Annotated[str, "Function or class name to locate"],
    path: Annotated[str, "Sub-path to restrict search"] = "",
) -> str:
    """Find where a function or class is defined using AST parsing (not grep)."""
    results: list[str] = []
    for file in _iter_source_files(repo, path):
        lang = _detect_language(file)
        parser = _get_parser(lang) if lang else None
        source = file.read_bytes()
        rel = file.relative_to(settings.repos_dir / repo)

        if parser:
            try:
                tree = parser.parse(source)

                def walk(node):
                    if node.type in ("function_definition", "class_definition",
                                     "function_declaration", "class_declaration",
                                     "method_definition"):
                        for child in node.children:
                            if child.type == "identifier" and child.text.decode() == name:
                                line = node.start_point[0] + 1
                                results.append(f"{rel}:{line} — {node.type}")
                    for child in node.children:
                        walk(child)

                walk(tree.root_node)
                continue
            except Exception:
                pass

        # Fallback: regex
        import re
        for i, line in enumerate(source.decode(errors="replace").splitlines(), 1):
            if re.search(rf"\b(def|class|function|const|let|var)\s+{re.escape(name)}\b", line):
                results.append(f"{rel}:{i} — {line.strip()}")

    return "\n".join(results) if results else f"Symbol '{name}' not found."


@tool
def find_callers(
    repo: Annotated[str, "Repository name"],
    function_name: Annotated[str, "Function name to find call sites for"],
    path: Annotated[str, "Sub-path to restrict search"] = "",
) -> str:
    """Find all places in the codebase that call a specific function."""
    import re
    results: list[str] = []
    pattern = re.compile(rf"\b{re.escape(function_name)}\s*\(")
    for file in _iter_source_files(repo, path):
        rel = file.relative_to(settings.repos_dir / repo)
        try:
            for i, line in enumerate(file.read_text(errors="replace").splitlines(), 1):
                if pattern.search(line):
                    results.append(f"{rel}:{i}: {line.strip()}")
        except Exception:
            continue
    return "\n".join(results) if results else f"No callers of '{function_name}' found."


@tool
def file_outline(
    repo: Annotated[str, "Repository name"],
    path: Annotated[str, "File path relative to repo root"],
) -> str:
    """Return a structural outline of a file: all classes, functions, and methods."""
    file = (settings.repos_dir / repo / path).resolve()
    if not file.exists():
        return f"ERROR: {path} not found"

    lang = _detect_language(file)
    parser = _get_parser(lang) if lang else None
    source = file.read_bytes()

    if parser:
        try:
            tree = parser.parse(source)
            symbols: list[tuple[int, str, str]] = []

            def walk(node, depth=0):
                if node.type in ("function_definition", "class_definition",
                                 "function_declaration", "class_declaration",
                                 "method_definition"):
                    for child in node.children:
                        if child.type == "identifier":
                            line = node.start_point[0] + 1
                            symbols.append((line, "  " * depth + node.type.split("_")[0],
                                            child.text.decode()))
                            break
                for child in node.children:
                    walk(child, depth + (1 if node.type in ("class_definition", "class_declaration") else 0))

            walk(tree.root_node)
            if symbols:
                return "\n".join(f"{line:4d}  {kind:<10} {name}" for line, kind, name in sorted(symbols))
        except Exception:
            pass

    # Fallback regex
    import re
    lines = []
    for i, line in enumerate(source.decode(errors="replace").splitlines(), 1):
        if re.match(r"\s*(def |class |function |const |let |var )", line):
            lines.append(f"{i:4d}  {line.strip()}")
    return "\n".join(lines) if lines else "(no symbols found)"


ALL_TOOLS = [find_symbol, find_callers, file_outline]
