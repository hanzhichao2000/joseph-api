"""joseph_api imports no other joseph package."""

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "joseph_api"


def _imported_modules(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_no_other_joseph_package_is_imported():
    offenders = []
    for path in sorted(ROOT.glob("*.py")):
        for name in _imported_modules(ast.parse(path.read_text(encoding="utf-8"))):
            if name.startswith("joseph_") and name.split(".")[0] != "joseph_api":
                offenders.append(f"{path.name}: {name}")
    assert not offenders, offenders
