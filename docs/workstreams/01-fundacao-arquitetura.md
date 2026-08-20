# W01 — Fundação e arquitetura

## Objetivo

Criar a fundação mínima de um monólito modular Python que permita evoluir domínio, storage, MCP, modelos e jobs sem acoplá-los. Esta frente deve tornar o repositório instalável, testável e navegável, sem implementar comportamento de memória pertencente a outras frentes.

## Contexto mínimo

OMP precisa começar pequeno, mas storage, protocolo e provedores devem ser substituíveis. O stack preferido é Python + FastAPI + PostgreSQL + pgvector + MCP. A camada HTTP não é o produto; MCP é a superfície de interoperabilidade e os application services são o núcleo reutilizável.

Leia também W00, W02, W04 e W07 antes de congelar boundaries.

## Escopo

### Dentro

- estrutura de pacotes e regras de dependência;
- `pyproject`, dependency groups, lint, typecheck e test runner;
- configuração tipada, composição e dependency injection simples;
- interfaces-base para clock, IDs e transações quando necessárias;
- entrypoints vazios/health checks para servidor e worker;
- convenções de erro, logging hook e feature flags;
- ADR da arquitetura inicial;
- CI mínima para checks determinísticos.

### Fora

- campos e transições do modelo de memória, owned por W02;
- tabelas, migrations e repositories concretos, owned por W03;
- schemas/tools MCP, owned por W04;
- algoritmos de writer/retrieval/consolidation;
- Docker/runtime operacional completo, owned por W11;
- documentação pública final, owned por W12.

## Decisões já tomadas

- Monólito modular com fluxo de dependência `transport/adapter -> application -> domain`.
- Domain não importa FastAPI, MCP SDK, ORM, cliente de LLM ou pgvector.
- Application define use cases e ports; adapters implementam ports.
- Configuração vem de environment/config file, nunca de constantes secretas.
- Operações I/O seguem um único modelo de concorrência, preferencialmente async end-to-end; qualquer exceção precisa de ADR.
- Testes unitários não exigem rede, banco real nem credenciais.

Estrutura de referência, ajustável por ADR:

```text
src/omp/
  domain/
  application/
  adapters/
    mcp/
    postgres/
    embeddings/
    models/
  server/
  workers/
  config.py
tests/{unit,integration,contract,e2e}/
evals/
docs/{adr,contracts,workstreams}/
```

## Decisões abertas

- versão mínima exata de Python;
- dependency/build manager;
- biblioteca ORM/query builder e estratégia async;
- ferramenta de lint/typecheck, desde que CI tenha uma fonte única de verdade;
- coexistência de MCP stdio e streamable HTTP no primeiro release.

O executor deve resolver essas decisões com um ADR curto que compare manutenção, maturidade e compatibilidade com o SDK MCP vigente.

## Dependências

- W00 define execução e handoff.
- W02 fornece os primeiros nomes de domain/application.
- W07 fornece requisitos de configuração, secrets e redaction.

W03, W04, W05, W06, W09, W10 e W11 dependem da estrutura produzida aqui.

## Entregáveis

- esqueleto instalável do projeto;
- comandos documentados para setup, lint, typecheck e testes;
- configuração tipada com validação antecipada;
- app factory/entrypoints sem side effects de import;
- health check básico sem expor configuração sensível;
- testes de arquitetura/boundaries;
- CI mínima;
- ADR `0001` com stack, boundaries e decisões de tooling.

## Etapas

1. Validar versão de runtime e compatibilidade das bibliotecas essenciais.
2. Definir árvore de pacotes e regra de imports.
3. Criar configuração e composição com adapters substituíveis.
4. Adicionar comandos de qualidade e CI.
5. Criar smoke tests de import, configuração e startup com fakes.
6. Publicar contrato para as frentes consumidoras e congelar nomes básicos no Gate A.

## Critérios de aceite verificáveis

- Um checkout limpo pode instalar dependências com o comando documentado.
- Importar o pacote não abre conexão, lê segredo remoto nem inicia servidor.
- Startup com adapters fake funciona sem Postgres ou provedor externo.
- Configuração inválida falha no início com mensagem acionável e sem imprimir secrets.
- Teste automatizado impede import de adapters dentro de domain.
- Lint, typecheck e unit tests executam por comandos únicos e passam na CI.
- O ADR explicita alternativas rejeitadas e custo de reversão.

## Testes

- smoke de package import e console entrypoint;
- unit de parsing/precedência de configuração;
- architecture tests para ciclos e imports proibidos;
- startup/shutdown repetido para detectar side effects;
- CI em runtime mínimo suportado.

## Riscos e mitigação

- **Framework dominar o domínio:** validar imports e manter DTOs de transporte nos adapters.
- **Tooling excessivo:** escolher um caminho por função e documentar um único comando.
- **Async inconsistente:** fechar estratégia antes de W03/W04.
- **Configuração insegura:** secrets redacted e falha antecipada.
- **Estrutura especulativa:** criar apenas pacotes exigidos pelo MVP 0.

## Handoff

Entregar a W02–W11: árvore final, dependency rules, comandos oficiais, mecanismo de configuração, extension points e ADR. Registrar qualquer nome ainda provisório para que outras frentes não o tratem como API pública.

## Perfil sugerido do executor

P2, com experiência forte em arquitetura Python, packaging, async I/O e testabilidade. Revisão P4 é útil apenas para configuração de secrets e redaction.
