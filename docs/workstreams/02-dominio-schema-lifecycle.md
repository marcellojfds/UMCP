# W02 — Domínio, schema e lifecycle

## Objetivo

Definir a linguagem canônica de memória e suas invariantes: identidade, owner, conteúdo, tipo, proveniência, versão, relações, estado e transições. O resultado deve sustentar o MVP sem reduzir memória a CRUD e sem exigir graph database.

## Contexto mínimo

Memórias podem ser fatos, preferências, decisões, insights, hipóteses, lições, goals, project context, conceitos, relações e perguntas abertas. Elas ganham evidência, mudam, contradizem outras, são substituídas e podem ser esquecidas. Proveniência e portabilidade são requisitos centrais.

Leia W00, W03, W04, W05, W06 e W07.

## Escopo

### Dentro

- entidades/value objects e invariantes;
- vocabulário inicial de tipos e estados;
- versionamento lógico e optimistic concurrency;
- lifecycle transitions;
- relações e proveniência;
- comandos/resultados internos para write, update e forget;
- serialização canônica independente de transporte;
- políticas de exclusão sem conteúdo residual.

### Fora

- DDL, ORM e índices, owned por W03;
- JSON schemas MCP, owned por W04;
- heurísticas de dedupe/contradição, owned por W05;
- scoring/ranking, owned por W06;
- criptografia, owned por W07;
- UI e taxonomias arbitrárias criadas por usuário.

## Decisões já tomadas

### Agregado mínimo

Uma memória tem, conceitualmente:

- `id` opaco e estável;
- `owner_id` obrigatório, mesmo no modo local;
- `space` lógico opcional, sem isolamento criptográfico próprio no MVP;
- `type` de vocabulário controlado;
- `content` textual não vazio;
- `importance` e `confidence` normalizados em `[0, 1]`;
- `state` e `version` monotônica;
- `created_at`, `updated_at` e, quando aplicável, `occurred_at`;
- proveniência mínima;
- descriptor do embedding, sem colocar vetor no domínio;
- zero ou mais relações tipadas.

Tipos iniciais:

```text
fact, preference, decision, insight, hypothesis, lesson,
goal, project_context, concept, relationship, open_question
```

Estados iniciais:

```text
active, superseded, contradicted, archived
```

`forgotten` é um resultado terminal de exclusão, não uma linha contendo o conteúdo original. Pode existir um tombstone mínimo sem conteúdo apenas se W07 aprovar sua finalidade e retenção.

Relações iniciais:

```text
supports, contradicts, derived_from, related_to, supersedes, applies_to
```

### Proveniência mínima

- tipo de fonte;
- identificador externo opcional, nunca obrigatório para conteúdo sensível;
- modelo/agente de origem opcional;
- timestamp de captura;
- excerto/evidência apenas quando permitido pela data classification;
- `idempotency_key` separada de conteúdo.

### Atualização

Uma atualização não destrói silenciosamente a história. O aggregate mantém versão corrente e histórico suficiente para auditoria. Escritas concorrentes usam `expected_version`; conflito retorna erro explícito. Supersede cria relação entre memórias quando o conhecimento novo substitui o antigo.

## Matriz inicial de transições

| De | Para | Permitido no MVP | Observação |
|---|---|---:|---|
| active | active | sim | nova versão de conteúdo/metadados |
| active | superseded | sim | exige referência ao sucessor |
| active | contradicted | sim | exige evidência ou memória conflitante |
| active | archived | sim | removida da busca default |
| contradicted | active | sim | exige nova evidência e versão |
| archived | active | sim | restauração explícita |
| superseded | active | não por default | requer operação de reparo/auditoria |
| qualquer | forgotten | sim | exclusão de conteúdo, versões, vetor e relações privadas |

## Decisões abertas

- se `importance`/`confidence` são obrigatórios do caller ou recebem defaults;
- extensão livre de tipos versus enum versionado;
- retenção de tombstone não sensível após forget;
- distinção futura entre evento observado e crença atual;
- quando contradições podem coexistir ativas por contexto/tempo;
- granularidade de evidence/provenance no MVP.

Essas decisões devem ser fechadas no Gate A apenas até o necessário para migration e protocol v0. Extensões posteriores devem ser aditivas.

## Dependências

- W00 e boundaries de W01.
- Requisitos irreversíveis de W07.

W03 e W04 não congelam schema antes desta frente. W05, W06 e W10 consomem o vocabulário; não criam enums paralelos.

## Entregáveis

- especificação `docs/memory-model.md` ou equivalente;
- entidades/value objects e erros de domínio;
- state machine explícita;
- serialização canônica versionada;
- ports de repository e unit of work em conjunto com W01;
- fixtures válidas e inválidas compartilhadas;
- ADRs para versionamento, forget e tombstones.

## Etapas

1. Catalogar invariantes e operações do MVP 0.
2. Modelar aggregate, versão, provenance e relations sem detalhes SQL.
3. Definir state machine e semântica de forget.
4. Criar serialização e fixtures canônicas.
5. Revisar o modelo com W03, W04, W07 e W08.
6. Congelar v0 no Gate A e registrar extensões futuras.

## Critérios de aceite verificáveis

- É impossível construir memória sem `owner_id`, conteúdo válido, type, state e timestamps coerentes.
- Valores fora de `[0, 1]`, transições inválidas e update stale falham com erros estáveis.
- Duas tentativas com a mesma idempotency key para o mesmo owner não criam duas memórias.
- Serializar e desserializar uma memória preserva significado e versão.
- Busca default pode excluir archived, superseded e contradicted sem conhecer SQL.
- Forget define exatamente quais dados desaparecem e quais metadados mínimos podem permanecer.
- Toda memória derivada aponta para ao menos uma evidência/proveniência.
- Fixtures canônicas são reutilizadas por contract tests de W03 e W04.

## Testes

- property tests para limites, timestamps e round-trip de serialização;
- table-driven tests para todas as transições;
- concorrência lógica com `expected_version` correto/incorreto;
- idempotência por owner;
- exclusão e cascade definidos por exemplos;
- compatibilidade de schema canônico entre versões aditivas.

## Riscos e mitigação

- **Schema grande demais:** separar required MVP, optional metadata e extensões futuras.
- **Enums rígidos:** versionar e prever extensão controlada sem aceitar strings arbitrárias silenciosamente.
- **Forget ambíguo:** ADR orientado pelo threat model e testes de cascade.
- **Histórico conflita com privacidade:** apagar versões sensíveis no forget; auditoria nunca justifica conservar conteúdo contra a intenção do usuário.
- **Contradição binária demais:** preservar evidence e contexto; não resolver automaticamente no domínio.

## Handoff

Entregar a W03/W04 um schema canônico, fixtures, tabela de erros e transições. Entregar a W05/W06/W10 vocabulário e invariantes. Informar explicitamente campos opcionais, defaults e decisões adiadas.

## Perfil sugerido do executor

P2 com experiência em domain modeling, versionamento e APIs. Revisão P4 obrigatória para forget/tombstone; revisão P3 útil para garantir que tipos atendem writer/retrieval sem incorporar heurísticas no domínio.
