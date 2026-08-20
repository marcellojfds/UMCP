# W09 — SDK, CLI e integração

## Objetivo

Oferecer o caminho mínimo para desenvolvedores e clientes MCP usarem OMP, depurarem o servidor e demonstrarem portabilidade. O primeiro deliverable é um SDK Python fino, uma CLI e uma jornada E2E reproduzível com dois clientes independentes.

## Contexto mínimo

MCP dá interoperabilidade, mas o projeto precisa de ferramentas de desenvolvimento e testes que provem a experiência sem UI. O cliente não deve duplicar regras do servidor. No MVP 4, esta frente receberá requisitos de criptografia client-side de W07.

Leia W00, W02, W04, W07, W08 e W11.

## Escopo

### Dentro

- SDK Python fino a partir do contrato MCP;
- CLI para operações MVP e diagnóstico;
- configuração de endpoint/transport/identity local;
- export/import em formato aberto versionado;
- exemplos de integração e cenário Modelo A -> Modelo B;
- erros amigáveis, exit codes e output machine-readable;
- compatibility tests servidor/SDK;
- futura implementação client-side de crypto após Gate F ADR.

### Fora

- regra de negócio do servidor;
- schemas canônicos duplicados manualmente, owned por W04;
- UI gráfica;
- SDKs para outras linguagens antes de demanda comprovada;
- auth hosted antes do threat model;
- desenho criptográfico, owned por W07.

## Decisões já tomadas

- Python é o primeiro SDK; demais linguagens ficam no backlog.
- CLI é ferramenta de DX/admin local, não interface principal do produto.
- SDK depende do contrato MCP, não acessa Postgres diretamente.
- Output JSON estável existe para automação; output humano pode ser formatado.
- Export usa formato aberto, versionado e documentado, incluindo provenance/lifecycle permitido.
- Exports são sensíveis por default; warnings e permissões seguras são obrigatórios.
- Import valida tudo antes de commit, suporta dry-run e idempotência.
- Client-side crypto só entra após ADR W07 e não será simulada por encoding superficial.

## Comandos mínimos propostos

```text
omp status
omp memory write
omp memory search
omp memory update
omp memory forget
omp export
omp import --dry-run
omp eval smoke
```

Nomes finais seguem a convenção W01/W04 e não devem criar semântica diferente das tools MCP.

## Decisões abertas

- package distribution e nome disponível;
- transport default e discovery local;
- owner identity/config do modo local;
- formato de export: JSONL/package com manifest e checksums;
- política de conflitos/import e remapeamento de IDs;
- inclusão de embeddings no export por default, provavelmente não;
- SDK sync, async ou ambos;
- secure local key storage e recovery no MVP 4.

## Dependências

- W01: packaging/config.
- W04: schemas, transport, errors e versioning.
- W07: export handling e crypto futuro.
- W08: scenario fixtures.
- W11: ambiente local/status.

W12 consome quickstarts e exemplos desta frente.

## Entregáveis

- pacote SDK Python e API reference;
- CLI com operações do MVP;
- golden compatibility tests;
- formato de export/import e schema versionado;
- cenário E2E automatizado entre dois clientes;
- exemplos para ao menos dois clientes MCP ou um cliente MCP + CLI independente;
- troubleshooting de conexão/configuração;
- no MVP 4, módulo crypto e migration tool conforme W07.

## Etapas

1. Gerar/consumir schemas W04 sem duplicação manual.
2. Implementar cliente mínimo e erros tipados.
3. Implementar CLI e outputs humano/JSON.
4. Criar E2E com ambiente descartável e dois client identities.
5. Implementar export, dry-run import e conflito/idempotência.
6. Rodar smoke contra transports suportados.
7. Entregar exemplos a W12 e, mais tarde, integrar crypto aprovada.

## Critérios de aceite verificáveis

- SDK e CLI completam write/search/update/forget sem acesso ao banco.
- `--json` produz output parseável e estável; erros têm exit codes documentados.
- O E2E grava com cliente A, reinicia/reconecta o servidor e recupera com cliente B.
- O cenário inclui busca positiva, negativa, update com conflito e forget seguido de busca vazia.
- Export seguido de import em instância vazia preserva memórias/provenance/states declarados.
- Import dry-run não altera estado; execução repetida não duplica memórias.
- Export não inclui embeddings ou secrets salvo opt-in explícito e documentado.
- Incompatibilidade de versão gera mensagem acionável.
- Nenhum exemplo requer dados pessoais ou credenciais reais.

## Testes

- unit de serialization, errors e CLI parsing;
- golden tests contra schemas W04;
- E2E em transports suportados;
- server restart/persistence;
- export/import round-trip, corrupt package e conflict policy;
- permissões/redaction de arquivos exportados;
- futura crypto: wrong key, rotation, tamper, recovery e mixed-version migration.

## Riscos e mitigação

- **Cliente ganha regra de negócio:** SDK fino e contract tests.
- **Schema diverge:** generation/import de fonte canônica.
- **Export vaza memória:** warning, secure defaults, permissions e sem embedding por default.
- **CLI vira UI prematura:** foco em DX e automação.
- **Auth local confundida com hosted:** documentação separa claramente os modos.
- **Crypto prejudica portabilidade:** formato versionado e migração antes de release.

## Handoff

Entregar a W08 o E2E e a W12 quickstart/examples reais. Entregar a W11 comandos de status/smoke. Informar matriz de versões SDK-servidor, transports testados e limitações de export.

## Perfil sugerido do executor

P5 com boa engenharia Python/API e experiência em CLI/DX; capacidade P2 para tests E2E. No MVP 4, implementação crypto exige especificação e revisão P4.
