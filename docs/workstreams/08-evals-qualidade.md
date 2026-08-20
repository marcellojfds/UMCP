# W08 — Evals e qualidade

## Objetivo

Construir a infraestrutura de avaliação que decide se writer, retrieval, lifecycle e consolidation melhoram a utilidade sem elevar intrusão, custo ou risco. Evals começam antes da implementação e produzem gates reprodutíveis, não apenas demos favoráveis.

## Contexto mínimo

OMP precisa medir write precision/recall, retrieval precision/recall, intrusion rate, cross-domain discovery e consolidation quality. O north-star qualitativo é o momento “eu tinha esquecido que sabia disso”; o proxy quantitativo precisa distinguir memória útil de semelhança textual.

Leia todos os workstreams; esta frente é transversal, mas não possui código de produção das outras frentes.

## Escopo

### Dentro

- taxonomia de tarefas e failure modes;
- datasets sintéticos/consentidos, splits e versionamento;
- labels, rubrics e adjudicação;
- eval harness, runners, baselines e relatórios;
- métricas de writer, retrieval, lifecycle e consolidation;
- medições de custo, latência e stability;
- regression suite e critérios dos Gates B–F;
- protocolo de revisão humana e judge model quando usado.

### Fora

- alterar produção para melhorar score, owned pela frente correspondente;
- coletar conversas pessoais reais sem consentimento/governança;
- escolher sozinho thresholds de produto finais;
- observabilidade online, owned por W11;
- security testing especializado, owned por W07, embora resultados possam entrar no gate.

## Decisões já tomadas

- Dataset existe antes de tuning e possui train/development/holdout separados.
- Dados são sintéticos por default; dados reais exigem consentimento, minimização e revisão W07.
- Toda métrica reporta tamanho da amostra, distribuição por categoria e configuração exata.
- Baselines mínimos: no-memory, vector-only e, nas fases relevantes, single-stage writer/no consolidation.
- “Nenhuma memória relevante” é uma classe de primeira importância.
- Intrusion é medida separadamente de precision.
- Cross-domain cases não dependem apenas de overlap lexical.
- LLM-as-judge nunca é a única evidência para gates críticos; há rubric e amostra humana.
- Thresholds abaixo são alvos iniciais, alteráveis somente por ADR com evidência.

## Dataset inicial

O corpus versionado deve conter no mínimo:

- 25 episódios de usuário sintético coerente;
- 100 memórias distribuídas entre types/states/spaces;
- 50 queries, incluindo pelo menos 15 sem memória relevante;
- 10 casos cross-domain com pouco overlap lexical;
- mudanças de preferência/decisão, duplicatas, contradições e obsolete memories;
- hard negatives com palavras iguais e finalidade diferente;
- o cenário canônico MBA market density -> estratégia GTM.

Isso é suficiente para um gate inicial, não para claims estatísticos amplos. O corpus cresce com failure cases e mantém holdout não usado no tuning.

## Métricas e gates iniciais

### Writer — Gate C

- write precision >= 0,85;
- write recall >= 0,65;
- unsupported-memory rate = 0 nos casos críticos e <= 0,02 no conjunto;
- duplicate-create rate <= 0,05;
- métricas também reportadas por type.

### Retrieval baseline — Gate B

- precision@5 >= 0,80;
- intrusion@5 <= 0,10;
- abstention em negative queries >= 0,90;
- lifecycle/isolation correctness = 100% nos casos determinísticos;
- latência/custo são medidos, com budget aprovado antes do gate.

### Retrieval avançado — Gate D

- melhora predefinida em cross-domain recall/utilidade versus vector-only;
- queda de precision dentro do limite aprovado;
- aumento de intrusion <= 0,02 absoluto;
- custo/latência dentro do budget.

### Consolidation — Gate E

- todas as claims derivadas têm evidence support;
- factual support rate = 1,00 no conjunto crítico;
- human useful-abstraction acceptance >= 0,75;
- generic/tautological output rate <= 0,10;
- reexecução não duplica resultados.

## Decisões abertas

- métrica primária de utilidade end-to-end e escala da rubric;
- budgets p95 e custo por operação;
- número e perfil de avaliadores humanos;
- judge models e política de versionamento;
- datasets públicos versus privados;
- longitudinal simulation e feedback do usuário após alpha;
- critérios de promotion de feature flags.

## Dependências

- W02 fornece fixtures e comportamentos determinísticos.
- W05/W06/W10 fornecem configs e outputs versionados.
- W07 aprova data handling.
- W09 fornece jornada E2E.
- W11 fornece medições operacionais.

Todas as frentes dependem dos gates/report templates desta frente.

## Entregáveis

- `evals/README.md` com metodologia e reprodução;
- datasets, datasheets e splits versionados;
- rubrics, label guidelines e adjudication log;
- runners para cada capacidade e comparação de baselines;
- relatórios machine-readable e Markdown;
- CI regression subset determinístico;
- suite offline completa acionável manualmente/schedule;
- failure taxonomy e changelog de datasets.

## Etapas

1. Definir tarefas, unidade de julgamento e failure taxonomy.
2. Criar corpus inicial e rotular antes das implementações avançadas.
3. Implementar baselines e relatório reproduzível.
4. Validar inter-annotator agreement em amostra.
5. Conectar cada frente por adapter de eval, não import interno frágil.
6. Executar regression subset na CI e suite completa nos gates.
7. Adicionar falhas reais sem mover silenciosamente os targets.

## Critérios de aceite verificáveis

- Um comando documentado reconstrói cada relatório a partir de versão/config fixa.
- Relatório contém commit/config, dataset version, provider/profile, amostra, métricas, custo e latência.
- Nenhum exemplo do holdout aparece nos prompts de tuning.
- Casos negativos, hard negatives e cross-domain aparecem como slices separados.
- Resultados de LLM-as-judge podem ser auditados contra rubric e amostra humana.
- CI falha quando uma regression determinística ultrapassa o limite aceito.
- Uma feature não atravessa gate apenas com média agregada que esconde um type crítico.

## Testes do harness

- datasets inválidos, IDs duplicados e leakage entre splits;
- métricas calculadas contra exemplos manuais conhecidos;
- determinismo com providers fake/recordings sanitized;
- timeout, partial result e unavailable judge;
- seed/control de randomness quando suportado;
- reprodução em ambiente limpo;
- validação de que relatórios não contêm dados proibidos.

## Riscos e mitigação

- **Goodhart/overfit:** holdout, slices e revisão de falhas qualitativas.
- **Corpus pequeno:** claims limitados e expansão progressiva.
- **Judge bias:** rubric, vários julgadores e amostra humana cega.
- **Dados sensíveis:** sintéticos por default e revisão W07.
- **Benchmarks desconectados do produto:** cenário E2E e uplift da resposta final.
- **Threshold arbitrário:** marcar como inicial e mudar apenas com evidência registrada.

## Handoff

Para cada gate, entregar relatório, comando, configuração, baseline, deltas, failure cases e recomendação objetiva de go/no-go. A decisão final pertence ao mantenedor; W08 não altera produção para forçar aprovação.

## Perfil sugerido do executor

P3 com experiência em evaluation science, IR metrics, datasets e experimentos com LLM. Revisão P4 para dados e P5 para tornar relatórios compreensíveis.
