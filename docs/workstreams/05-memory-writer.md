# W05 — Memory Writer

## Objetivo

Transformar interações em propostas de memória estruturadas, conservadoras e auditáveis, decidindo o que vale lembrar sem armazenar conversas indiscriminadamente. Esta frente começa no MVP 1 e deve provar qualidade antes de habilitar persistência automática.

## Contexto mínimo

O writer conceitual segue `interaction -> candidate extraction -> importance -> dedupe -> contradiction/update detection -> persistence`. Má memória escrita contamina toda recuperação futura. A meta inicial é alta precisão, com abstention explícita.

Leia W00, W02, W03, W04, W07 e W08.

## Escopo

### Dentro

- contrato de entrada para interação/contexto permitido;
- extração estruturada de zero ou mais candidatos;
- classificação de type, importance, confidence e provenance;
- decisão `ignore|create|update_candidate|contradiction_candidate`;
- candidate dedupe contra memória existente;
- provider/model adapter, prompt versioning e output validation;
- modos `propose` e `commit` feature-flagged;
- telemetria de decisão sem conteúdo sensível;
- dataset e experimentos com W08.

### Fora

- persistência e transação, owned por W03;
- state transitions definitivas, owned por W02;
- ranking de memórias para uso em respostas, owned por W06;
- schemas das tools públicas existentes, owned por W04;
- consolidação de muitas memórias, owned por W10;
- treino/fine-tuning de modelo no MVP.

## Decisões já tomadas

- Writer inteligente não bloqueia o MVP 0.
- Primeira entrega opera em `propose`: retorna candidatos e razões, sem gravar.
- `commit` usa exatamente os mesmos application services de escrita/update explícitos; não contorna invariantes.
- Persistência automática fica desligada por default até o Gate C.
- Nenhuma interação deve necessariamente produzir memória.
- O pipeline conserva provenance e não inventa evidence ausente.
- Outputs de modelo passam por schema validation e política determinística.
- Model/provider, prompt e policy version são registrados para reprodução.

## Decisões abertas

- unidade de entrada: mensagem, turn, janela resumida ou evento do cliente;
- um passo de validação versus dois passos e seu custo marginal;
- thresholds por type;
- regras determinísticas antes/depois do modelo;
- estratégia de dedupe: embedding, lexical, structured match ou combinação;
- contradição temporal/contextual e quando sugerir supersede;
- se/como a funcionalidade será exposta via MCP depois do Gate C.

## Dependências

- Gate B concluído.
- W02: types, provenance e lifecycle.
- W03: repository/search ports para candidatos de dedupe.
- W07: data minimization e policy de provedores.
- W08: dataset, labels e gates.

W04 só expõe uma nova tool depois que este workstream tiver contrato e evidência aceitos.

## Entregáveis

- spec do writer e decision taxonomy;
- pipeline versionado com provider abstraction;
- prompt(s)/policy versionados e schemas de output;
- modo `propose` e modo `commit` protegido por feature flag;
- dedupe e contradiction candidate detection;
- unit/integration tests com provider fake;
- relatório experimental contra baseline;
- guia para revisão/feedback de propostas.

## Etapas

1. Com W08, rotular interações positivas, negativas, ambíguas, duplicadas e contraditórias.
2. Implementar baseline determinístico ou single-pass estruturado.
3. Validar schema e aplicar policy conservadora.
4. Buscar possíveis duplicatas/contradições dentro do owner/space.
5. Comparar single-stage e validation-stage por qualidade, custo e latência.
6. Integrar `propose`; somente depois experimentar `commit` em ambiente controlado.
7. Documentar falhas por type e calibrar thresholds sem overfit no test set.

## Critérios de aceite verificáveis

- Interações sem conhecimento durável retornam zero candidatos.
- Todo candidato referencia trecho/evidência disponível e não adiciona afirmação não suportada.
- Output inválido do provider não é persistido.
- Duplicata exata e paráfrase óbvia não criam nova memória no cenário de aceite.
- Mudança explícita de preferência gera `update_candidate`/`contradiction_candidate`, não duas preferências ativas silenciosas.
- `propose` não causa escrita; `commit` exige flag/configuração explícita.
- Resultado registra versões de provider, prompt e policy.
- No dataset holdout inicial, write precision >= 0,85 e write recall >= 0,65, com intervalos/amostra reportados; thresholds podem mudar por ADR baseado em evidência.
- Custos e latências p50/p95 são publicados por configuração testada.

## Testes e evals

- unit com provider fake para cada decision type;
- golden tests de output parsing e prompt injection content;
- dataset rotulado com casos negativos em maioria realista;
- precision/recall geral e por type;
- taxa de duplicatas e taxa de contradições perdidas;
- comparação single-stage vs validation-stage;
- testes de indisponibilidade, timeout, retry seguro e idempotência;
- revisão humana cega de uma amostra de candidatos.

## Riscos e mitigação

- **Guardar demais:** abstention default e precision como gate primário.
- **LLM inventar memória:** evidence binding e validation policy.
- **Dedupe fundir coisas distintas:** propostas, não merge destrutivo automático.
- **Custo/latência:** baseline simples e experimento que justifique segunda chamada.
- **Provider recebe conteúdo sensível:** policy W07, opt-in/configuração e documentação clara.
- **Benchmark leakage:** split fixo e novos casos adversariais contínuos.

## Handoff

Entregar a W04 somente uma proposta de API após Gate C. Entregar a W08 configs/resultados reproduzíveis e failure taxonomy. Entregar a W11 métricas sem conteúdo. Toda automatização ainda desabilitada deve estar visível no handoff.

## Perfil sugerido do executor

P3 com experiência em structured generation, classificação, evals e sistemas tolerantes a output probabilístico. Revisão P4 para data handling e P2 para integração transacional.
