# ADR 0001 — Arquitetura modular e tooling do MVP 0

## Status

Aceito para o MVP 0; sujeito a revisão por ADR.

## Contexto

O core precisa ser consumível por MCP, SDK, CLI e testes sem acoplar o domínio
a transporte, ORM ou provedor de embeddings. O contrato operacional pede um
monólito modular, async de ponta a ponta e instalação reproduzível.

## Decisão

- Python 3.11+ com `hatchling` para empacotamento.
- `domain` contém entidades, value objects, invariantes e erros puros.
- `application` contém commands/results, ports e casos de uso assíncronos.
- `adapters` implementa ports: PostgreSQL/pgvector e embeddings; MCP, SDK e
  CLI permanecem adapters externos ao core.
- SQLAlchemy Core assíncrono + asyncpg fornece acesso transacional; Alembic
  executa migrations reproduzíveis.
- Pydantic Settings lê somente configuração `OMP_*`; secrets são `SecretStr`
  e não aparecem em summaries.
- FastAPI, SDK oficial MCP para Python (`mcp`), Typer e HTTPX entram como
  dependências para desbloquear os consumidores previstos. O core não importa
  essas bibliotecas.
- Ruff é o lint único; mypy é o typecheck; pytest/pytest-asyncio são o runner.
- O perfil de embedding padrão do MVP é `hash/v1`, dimensão 64, métrica
  cosine. Ele é determinístico e não exige rede ou download de modelo; um
  provider real pode ser conectado pelo port.

## Alternativas consideradas

- **Poetry/PDM:** ambos são viáveis, mas o `pyproject` PEP 621 com Hatchling
  reduz a superfície de tooling para um pacote pequeno.
- **SQLModel/ORM declarativo:** não é necessário para as queries do MVP e
  aumentaria o acoplamento entre persistência e o modelo de domínio.
- **psycopg síncrono:** rejeitado porque quebraria o modelo async definido em
  W01 e exigiria thread pools nos serviços.
- **Qdrant separado:** rejeitado no MVP; relações, lifecycle e vetores ficam
  em PostgreSQL/pgvector para manter transações e ownership em um store.
- **Embeddings externos obrigatórios:** rejeitados nos testes; provedores
  externos são opcionais e substituíveis.

## Consequências

O pacote instala a stack necessária para o próximo executor, mas instalação de
dependências e Docker/PostgreSQL continuam pré-requisitos para a suíte real de
integração. A dimensão fixa do índice exige re-embedding explícito quando o
profile mudar; não há mistura silenciosa de profiles.
