# W04 — Protocolo MCP

## Objetivo

Definir e implementar uma superfície MCP pequena, estável e semântica para que clientes independentes escrevam, busquem, atualizem e esqueçam memórias. Esta frente possui os schemas públicos, validação de transporte, compatibilidade e adapters; ela não reimplementa regras de domínio.

## Contexto mínimo

O protocolo deve permitir interoperabilidade entre modelos e evitar expor `database.insert` ou `vector.search`. O MVP 0 inclui `memory.write`, `memory.search`, `memory.update` e `memory.forget`. `memory.related` entra apenas após baseline de retrieval e contrato aprovado.

Leia W00, W01, W02, W06, W07 e W09.

## Escopo

### Dentro

- schemas versionados de input/output;
- nomes, descrições e semântica das tools MCP;
- adapter MCP para application services;
- validação, limites, erros e capability/version discovery;
- compatibilidade entre transports escolhidos;
- contract tests e exemplos públicos;
- política de deprecation e breaking changes.

### Fora

- entidades e lifecycle, owned por W02;
- persistência, owned por W03;
- seleção do que escrever, owned por W05;
- candidate retrieval/ranking, owned por W06;
- cliente/CLI, owned por W09;
- auth/hosting completos, fora do MVP local e coordenados com W07/W11.

## Contrato v0 proposto

Os nomes de campos serão congelados após fixtures W02; esta seção define a semântica mínima.

### `memory.write`

Input local v0: `content`, `type`, `owner_id`, `space?`, `importance?`, `confidence?`, `provenance`, `idempotency_key` e metadados opcionais permitidos. Output: memória canônica, versão e status `created|already_exists`.

No MVP 0 a tool recebe uma memória explícita já selecionada. Ela não aceita um dump de conversa para extração automática.

### `memory.search`

Input local v0: `query`, `owner_id`, filtros opcionais de space/type/state/time, `limit` limitado pelo servidor e `min_relevance?`. Output: lista ordenada com memória canônica, score normalizado, `reason_retrieved`, proveniência segura e versão do ranking/profile.

Zero resultados é sucesso. O caller não pode exigir que o servidor atravesse o threshold de segurança.

### `memory.update`

Input local v0: `id`, `owner_id`, `expected_version`, patch permitido, motivo/proveniência e idempotency key. Output: nova versão ou erro de conflito estável. Campos imutáveis e transições usam operações explícitas do domínio.

### `memory.forget`

Input local v0: `id`, `owner_id`, idempotency key e razão opcional não sensível. Output: `forgotten|already_absent`, sem ecoar conteúdo apagado. Forget é idempotente.

### `memory.related` — posterior ao MVP 0

Input local v0: memória origem, `owner_id`, filtros e limit. Output: relações explícitas e candidatos inferidos claramente diferenciados. A semântica de candidate generation pertence a W06.

## Envelope e erros

Todos os resultados devem carregar `protocol_version` e `request_id`; respostas model-based podem incluir `profile_version`. Erros públicos estáveis devem distinguir pelo menos:

```text
validation_error
not_found
version_conflict
forbidden
rate_limited
dependency_unavailable
internal_error
```

Erros não incluem conteúdo, SQL, stack trace, segredo ou existência de objeto de outro owner. `not_found` e `forbidden` podem ser deliberadamente indistinguíveis no boundary quando necessário ao threat model.

## Decisões já tomadas

- Tools expõem memória, não storage.
- Schemas são estritos e recusam campos desconhecidos onde isso reduzir ambiguidade.
- Inputs têm limites de tamanho, `limit` máximo e timeouts definidos.
- `reason_retrieved` fica no v0 para debug/eval; remover depois exigiria deprecation.
- Protocolo e application service usam DTOs distintos com mapping testado.
- Mudanças aditivas preservam clientes; mudanças incompatíveis incrementam versão pública.

## Decisões abertas

- transporte(s) oficiais do alpha: stdio, streamable HTTP ou ambos;
- mecanismo de discovery/version handshake;
- como owner identity é estabelecida no modo local versus hosted; no hosted, `owner_id` não pode ser confiado apenas porque veio no payload e deverá ser derivado do principal autenticado;
- representação final de timestamps, filtros e pagination cursor;
- exposição pública de history e consolidate após o MVP;
- limites default, fechados com W08/W11.

## Dependências

- W01: server composition e SDK/runtime MCP escolhido.
- W02: schema e erros de domínio.
- W03/W06: implementation ports para adapters.
- W07: limites, identity e tratamento de erros.

W09 e W12 consomem schemas e exemplos desta frente.

## Entregáveis

- especificação `docs/protocol.md` com exemplos;
- schemas machine-readable versionados;
- adapter MCP e entrypoint(s);
- mapping de domain/application errors para erros públicos;
- contract tests executáveis por servidor e SDK;
- capability/version response;
- política de compatibilidade/deprecation.

## Etapas

1. Fechar semântica e exemplos com W02/W09 antes de implementar adapter.
2. Escolher SDK/transports compatíveis com runtime W01.
3. Criar schemas e golden fixtures, incluindo respostas vazias/erros.
4. Implementar adapter contra fakes de application services.
5. Conectar implementações W03/W06 sem alterar contratos.
6. Rodar contract tests em todos os transports suportados.
7. Verificar descrições das tools com ao menos dois clientes MCP independentes ou simuladores conformes.

## Critérios de aceite verificáveis

- Quatro tools MVP aparecem com nomes, descrições e schemas corretos em capability discovery.
- Golden requests/responses validam no servidor e SDK sem schemas duplicados divergentes.
- Input inválido falha antes de chamar application service.
- Content size, limit, timeout e cancellation têm testes.
- Zero-result search retorna sucesso com lista vazia.
- Version conflict e forget idempotente preservam a semântica W02.
- Erros não vazam conteúdo ou existência cross-owner.
- A mesma suíte de contrato passa em cada transport declarado suportado.
- Um cliente compatível consegue completar o cenário E2E de W09.

## Testes

- schema/golden contract tests;
- fuzz de inputs, limites e campos desconhecidos;
- mapping de todos os erros conhecidos;
- cancellation e dependency timeout;
- testes cross-owner no boundary;
- backward compatibility a partir do primeiro release publicado;
- smoke com cliente MCP externo/simulador independente.

## Riscos e mitigação

- **Descrição induz chamadas agressivas:** linguagem conservadora e exemplos de abstention.
- **SDK MCP muda:** pin de dependência e adapter estreito; verificar versão no início da execução.
- **Contrato acoplado ao banco:** DTOs públicos não expõem colunas, operadores vetoriais ou ORM.
- **Owner enviado pelo caller é falsificável:** aceitável apenas local; hosted exige identidade confiável definida por W07.
- **Schemas expandem cedo demais:** apenas quatro tools no MVP 0.

## Handoff

Entregar a W09/W12 spec, schemas, golden fixtures, transports, limits e compatibility policy. Entregar a W11 entrypoints/health dependencies. Registrar claramente tools experimentais e recursos não suportados.

## Perfil sugerido do executor

P2 com experiência em protocolos, schema evolution, MCP e integração async. Revisão P5 para clareza das tool descriptions e P4 para identity/error leakage.
