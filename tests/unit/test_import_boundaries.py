"""Guard the domain/application dependency direction."""

import ast
from pathlib import Path


def imported_top_level_modules(root: Path) -> set[str]:
    modules: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                modules.add(node.module)
    return modules


def test_domain_and_application_do_not_import_adapters() -> None:
    source_root = Path(__file__).parents[2] / "src" / "omp"
    domain_imports = imported_top_level_modules(source_root / "domain")
    application_imports = imported_top_level_modules(source_root / "application")
    assert all(not module.startswith("omp.adapters") for module in domain_imports)
    assert all(not module.startswith("omp.adapters") for module in application_imports)


def test_domain_does_not_import_application() -> None:
    source_root = Path(__file__).parents[2] / "src" / "omp"
    domain_imports = imported_top_level_modules(source_root / "domain")
    assert all(not module.startswith("omp.application") for module in domain_imports)
