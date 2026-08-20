# Plano de execução do Open Memory Protocol

## Propósito

Este diretório transforma `manifest.md` e `project-context.md` em contratos de trabalho delegáveis. Cada frente tem ownership, entradas, saídas, dependências e critérios de aceite próprios. O plano prioriza um MVP que prove utilidade antes de investir em automação sofisticada ou infraestrutura de escala.

Os documentos daqui orientam implementação futura; eles não significam que o código descrito já exista.

## Resultado que o primeiro release precisa provar

```text
Cliente / Modelo A
    -> escreve uma memória útil e explícita
    -> OMP persiste conteúdo, metadados e proveniência

Cliente / Modelo B
    -> consulta a memória em outro contexto
    -> OMP retorna apenas memória relevante, ou se abstém
    -> o cliente consegue usar a memória e explicar sua origem
```

O MVP não será considerado bem-sucedido apenas porque um vetor semelhante foi encontrado. A demonstração precisa mostrar persistência entre clientes, recuperação útil, ciclo de vida correto e ausência de intrusões óbvias.

## Decisões de programa

Estas decisões valem para todas as frentes até serem substituídas por um ADR aceito:

- O produto é uma camada de memória pertencente ao usuário, não um arquivo de conversas.
- A interface principal expõe semântica de memória via MCP, não primitivas de banco.
- O MVP usa Python, FastAPI, PostgreSQL e pgvector, com uma única base de dados.
- A lógica de domínio e os casos de uso não dependem de MCP, FastAPI, Postgres nem de um provedor de modelo específico.
- O primeiro release é local/self-hosted e pode operar sem criptografia client-side. Ele não fará alegação de E2EE.
- Identidade de owner, proveniência, versionamento, exclusão e isolamento lógico entram no modelo desde o início, porque são caros de acrescentar depois.
- Recuperação privilegia precisão e pode retornar zero resultados.
- Escrita inteligente, reranking por LLM, consolidação e arquitetura criptográfica hospedada entram em fases posteriores, sempre medidos por evals.
- Graph database, UI completa, multi-region, billing, colaboração entre usuários e features enterprise estão fora do horizonte do MVP.

## Frentes e ownership

| ID | Frente | Ownership exclusivo | Primeiro marco |
|---|---|---|---|
| W00 | [Contrato operacional](./00-contrato-operacional.md) | regras de execução, handoff e integração | antes de qualquer código |
| W01 | [Fundação e arquitetura](./01-fundacao-arquitetura.md) | estrutura do projeto, boundaries, configuração e quality gates | Gate A |
| W02 | [Domínio, schema e lifecycle](./02-dominio-schema-lifecycle.md) | modelo canônico e transições de memória | Gate A |
| W03 | [Storage e migrations](./03-storage-migrations.md) | Postgres/pgvector, migrations e repositories | MVP 0 |
| W04 | [Protocolo MCP](./04-protocolo-mcp.md) | contratos públicos e adapters MCP | MVP 0 |
| W05 | [Memory Writer](./05-memory-writer.md) | extração, seleção, dedupe e proposta de atualização | MVP 1 |
| W06 | [Retrieval e reranking](./06-retrieval-reranking.md) | geração de candidatos, ranking, abstention e `related` | MVP 0/MVP 2 |
| W07 | [Privacy e threat model](./07-privacy-threat-model.md) | classificação de dados, ameaças e arquitetura criptográfica | Gate A/MVP 4 |
| W08 | [Evals e qualidade](./08-evals-qualidade.md) | datasets, harness, métricas e gates quantitativos | Gate A e contínuo |
| W09 | [SDK, CLI e integração](./09-sdk-cli-integracao.md) | cliente Python, CLI, export/import e jornada E2E | MVP 0 |
| W10 | [Consolidação](./10-consolidacao.md) | formação auditável de conhecimento derivado | MVP 3 |
| W11 | [Observabilidade e operações](./11-observabilidade-operacoes.md) | telemetria, redaction, execução local e runbooks | MVP 0 |
| W12 | [Documentação e release open source](./12-documentacao-release.md) | documentação pública, governança e release | Alpha público |

Se uma mudança tocar um artefato de outra frente, o executor propõe a mudança no handoff e não altera unilateralmente o contrato alheio.

## Fases, paralelismo e gates

### Fase 0 — Alinhamento e contratos

Podem avançar em paralelo depois de W00:

- W01 define boundaries e esqueleto.
- W02 fecha o modelo canônico e lifecycle.
- W04 rascunha o protocolo a partir do modelo de W02.
- W07 produz threat model e requisitos irreversíveis.
- W08 cria datasets e baselines antes da otimização.

**Gate A — Contract freeze:** modelo de domínio, contratos de repository e application service, schemas MCP v0, data classification e métricas do MVP aprovados. Nenhum contrato precisa ser perfeito, mas mudanças posteriores devem ser versionadas.

### Fase 1 — MVP 0: vertical slice persistente

Depois do Gate A:

- W03 implementa persistência e migrations.
- W06 implementa busca vetorial baseline e abstention.
- W04 conecta os casos de uso às tools `memory.write`, `memory.search`, `memory.update` e `memory.forget`.
- W09 constrói SDK/CLI e o teste entre dois clientes.
- W11 entrega ambiente local, health checks, redaction e telemetria mínima.
- W08 executa regressões e publica o primeiro relatório.

W03 e a primeira metade de W06 podem avançar em paralelo após o contrato de repository. W04 pode implementar validação e serialização com fakes enquanto W03 evolui. W09 pode construir o cliente contra schemas congelados. W11 pode preparar o ambiente local sem assumir a lógica das outras frentes.

**Gate B — MVP 0 funcional:** a jornada E2E passa em ambiente limpo; update e forget são verificáveis; consultas irrelevantes se abstêm; migrations sobem e descem em banco descartável; logs não contêm conteúdo de memória.

### Fase 2 — MVP 1: escrita inteligente

- W05 adiciona extração conservadora, dedupe e detecção de possível contradição.
- W08 mede precisão/recall de escrita.
- W02 só muda se o experimento revelar uma lacuna real no domínio.

**Gate C — Writer:** modo `propose` atende os limiares de qualidade; persistência automática continua feature-flagged até haver evidência suficiente.

### Fase 3 — MVP 2: retrieval inteligente

- W06 compara vector-only, query expansion e reranking.
- W08 mede precision, recall, intrusion rate, cross-domain discovery, latência e custo.
- W09 expõe feedback e diagnóstico somente se o contrato for aceito por W04.

**Gate D — Retrieval:** a alternativa escolhida supera o baseline em utilidade sem ultrapassar os budgets acordados nem aumentar intrusion rate.

### Fase 4 — MVP 3: consolidação

- W10 cria jobs externos, propostas derivadas e rastreabilidade.
- W11 opera worker/scheduler externo.
- W08 mede fidelidade, novidade útil e taxa de abstrações genéricas.

**Gate E — Consolidation:** nenhuma conclusão sem evidência; reexecução idempotente; promoção automática permanece desligada no primeiro experimento.

### Fase 5 — MVP 4: privacidade para hospedagem

- W07 compara alternativas de criptografia e geração de embeddings.
- W09 implementa a parte client-side da alternativa aprovada.
- W03 e W06 só adaptam storage/retrieval depois de um ADR e de um protótipo medido.

**Gate F — Hosted privacy readiness:** threat model revisado, claims públicos aprovados, recuperação de chave definida, exclusão/backups testados e vazamento por embeddings explicitamente documentado.

### Fase 6 — Alpha público

W12 reúne documentação, licença, segurança, contribuição e release notes. O alpha pode acontecer depois do Gate B; MVPs 1–4 não bloqueiam o primeiro release se estiverem claramente marcados como roadmap.

## Grafo de dependências

```text
W00
 ├─> W01 ───────────────┬─> W03 ──┬─> W04 adapters ─┐
 ├─> W02 ──┬─> W03      │          ├─> W06 baseline  ├─> W09 E2E ─> Gate B
 │         ├─> W04 spec │          └─> W11 ops ─────┘
 │         ├─> W05      │
 │         └─> W10      │
 ├─> W07 ───────────────┴─> requisitos de storage/logging
 └─> W08 ─────────────────> gates de todas as fases

Gate B ─> W05 ─> Gate C ─> W06 avançado ─> Gate D ─> W10 ─> Gate E
Gate B + ADR de privacidade ─> W07/W09/W03/W06 ─> Gate F
Gate B + W11 + W12 ─> Alpha público
```

## Caminho crítico do MVP 0

1. Fechar domínio, interfaces internas e schemas MCP.
2. Criar migration inicial e repositories.
3. Implementar write/update/forget e busca vetorial com abstention.
4. Ligar application services ao servidor MCP.
5. Executar a jornada com dois clientes via SDK/CLI.
6. Rodar eval suite, privacy smoke tests e release checklist.

## Matriz de releases

| Capacidade | MVP 0 | MVP 1 | MVP 2 | MVP 3 | MVP 4 |
|---|---:|---:|---:|---:|---:|
| Escrita explícita estruturada | sim | sim | sim | sim | sim |
| Busca vetorial + filtros + abstention | sim | sim | sim | sim | sim |
| Update versionado e forget | sim | sim | sim | sim | sim |
| Extração automática de candidatos | não | sim | sim | sim | sim |
| Dedupe/contradição assistidos | não | sim | sim | sim | sim |
| Query expansion/reranking | não | não | sim | sim | sim |
| `memory.related` público | não | não | opcional | sim | sim |
| Consolidação programada | não | não | não | sim | sim |
| Criptografia client-side | não | não | não | não | protótipo |

## Integração e definição global de pronto

Uma frente só está pronta quando:

- seus critérios de aceite automatizáveis estão em testes;
- contratos públicos e exemplos foram atualizados;
- migrations e mudanças incompatíveis têm caminho de upgrade;
- dados sensíveis não aparecem em logs, traces, snapshots ou fixtures;
- decisões abertas que bloqueiam outra frente foram resolvidas em ADR;
- o handoff identifica arquivos alterados, comandos executados, riscos residuais e próximo consumidor;
- o relatório de W08 mostra a diferença contra o baseline relevante.

O cenário E2E canônico deve existir como fixture estável: uma memória sobre densidade geográfica nasce em um contexto de estudo e é recuperada em uma decisão posterior de GTM, junto com casos negativos que não devem retornar essa memória.

## Backlog deliberadamente posterior

- graph database e inferência complexa de relações;
- UI de consumo geral;
- colaboração e compartilhamento de memória;
- billing, quotas comerciais e administração enterprise;
- busca privada com garantias criptográficas fortes sem vazamento semântico;
- múltiplos stores especializados;
- sincronização offline-first e multi-device;
- marketplace de consolidadores ou rankers.

Esses itens só entram após dados do MVP mostrarem a necessidade.
