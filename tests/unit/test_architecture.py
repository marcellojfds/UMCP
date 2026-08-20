from pathlib import Path


def test_domain_does_not_import_infrastructure_frameworks() -> None:
    domain_root = Path(__file__).parents[2] / "src" / "omp" / "domain"
    source = "\n".join(path.read_text() for path in domain_root.glob("*.py"))
    for forbidden in ("fastapi", "sqlalchemy", "pgvector", "mcp", "asyncpg"):
        assert forbidden not in source.lower()
