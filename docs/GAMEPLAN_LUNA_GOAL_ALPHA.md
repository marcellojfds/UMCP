# OMP Alpha — Gameplan de execução contínua com GPT-5.6 Luna e `/goal`

**Criado em:** 2026-08-20
**Executor planejado:** `gpt-5.6-luna`
**Modo recomendado:** reasoning `high`
**Ponto de partida local:** `main` em `4947ebfb3789558892c242e0d7a8743256f3656d`
**Worktree S08 existente:** `/private/tmp/umcp-s08-semantic-embedding-selection`
**Branch S08 existente:** `s08-semantic-embedding-selection`
**Estado geral inicial:** engineering preview; **NO-GO** para publicação

## 1. Objetivo durável

Levar o Open Memory Protocol do estado atual até um release candidate Alpha
local/self-hosted reproduzível, semanticamente útil, auditável e pronto para
uma decisão humana de publicação no GitHub, sem enfraquecer os gates, abrir o
holdout durante tuning, perder a evidência S08, prometer segurança hosted ou
publicar qualquer release sem autorização explícita.

O trabalho termina somente quando existir um SHA candidato limpo que:

1. preserve e corrija a experiência S08;
2. implemente o embedding E5 no runtime com migration e rollback seguros;
3. passe quality, unit, contract, integration, E2E, privacy/ops e packaging;
4. tenha avaliação development e holdout reproduzível associada ao SHA;
5. tenha documentação coerente com o comportamento executável;
6. tenha build reproduzível, inventário de dependências e auditoria de
   vulnerabilidades/licenças;
7. tenha uma nova auditoria independente S07-R2 com decisão GO; e
8. deixe tag/GitHub Release como a única ação restante, claramente separada e
   dependente de autorização do mantenedor.

## 2. Comando `/goal` recomendado

Selecionar `gpt-5.6-luna`, reasoning `high`, abrir a raiz do repositório e
enviar o bloco abaixo. O texto é deliberadamente autocontido para sobreviver a
compaction e múltiplos turnos.

```text
/goal Leve o Open Memory Protocol do estado atual até um release candidate Alpha local/self-hosted reproduzível, semanticamente útil e auditado, seguindo integralmente docs/GAMEPLAN_LUNA_GOAL_ALPHA.md. Trabalhe continuamente em checkpoints até existir um SHA candidato limpo com todos os gates obrigatórios verdes e uma auditoria S07-R2 GO. Não reduza thresholds ou gates, não use o holdout para tuning, não exponha dados sensíveis, não faça operações destrutivas sobre banco não descartável e não faça commit, push, tag, GitHub Release ou mudança remota sem a autorização explícita correspondente. Preserve primeiro a worktree S08 em /private/tmp/umcp-s08-semantic-embedding-selection. Se uma autorização externa for indispensável, conclua todo o trabalho seguro possível, registre exatamente o bloqueio e solicite somente a autorização mínima necessária. Não marque o goal como concluído enquanto qualquer critério da seção Definition of Done permanecer pendente.
```

## 3. Contrato operacional do executor

### 3.1 Regras invariantes

- Ler este gameplan, `project-context.md`, `README.md`, os ADRs, os planos de
  eval e release, e todos os handoffs S04–S08 antes de editar produção.
- Começar cada checkpoint com `git status --short --branch`, SHA, branch e
  `git worktree list --porcelain`.
- Preservar alterações do usuário e nunca sobrescrever trabalho fora do
  escopo.
- Usar `rg`/`rg --files` para descoberta e `apply_patch` para edição manual.
- Não usar `git reset --hard`, `git checkout --`, force-push ou exclusão ampla.
- Não usar `git add .`, `git add -A` ou `git add --all`.
- Não baixar modelos/dependências ou acessar Docker silenciosamente quando o
  ambiente exigir aprovação.
- Nunca executar migration destrutiva em URL não comprovadamente descartável.
- Nunca executar `alembic downgrade base` em banco real, compartilhado ou cuja
  identidade não esteja validada.
- Não baixar o threshold `0.78`, alterar o corpus ou relaxar gates para obter
  resultado verde.
- Não abrir nem avaliar o holdout antes do checkpoint específico autorizado.
- Nunca misturar vetores de dimensões/perfis diferentes na mesma busca.
- Não criar fallback remoto ou envio de conteúdo para APIs externas.
- Não alegar E2EE, zero knowledge, hosted auth, tenant isolation ou escala.
- Commits, push, tag, release e mudanças de configurações GitHub são ações
  independentes e exigem autorização explícita correspondente.

### 3.2 Ritmo de trabalho para Luna

- Executar uma fase por vez; não combinar migration, tuning e auditoria num
  único lote opaco.
- Manter `docs/handoffs/alpha/GOAL-PROGRESS.md` com: checkpoint, SHA, arquivos,
  comandos, resultados, riscos, próximo passo e autorizações pendentes.
- Rodar o gate mais barato após cada mudança local e o gate PostgreSQL somente
  depois que unit/contract estiver verde.
- Quando uma hipótese falhar, registrar evidência e ajustar a implementação;
  não alterar a métrica de sucesso.
- Em caso de três falhas consecutivas pela mesma causa externa, registrar o
  bloqueio de forma reproduzível e parar somente aquele ramo de trabalho.
- Antes de cada compaction ou pausa, atualizar o progress log com o próximo
  comando exato.

## 4. Estado inicial que deve ser revalidado

O executor não deve confiar cegamente nestes fatos; deve confirmá-los:

- `main` aponta para `4947ebf` e está limpa.
- O remoto `marcellojfds/UMCP` está público, mas sem commits ou PRs.
- A worktree S08 possui oito grupos de paths não rastreados.
- `./scripts/gate-fast` passa com 44 testes e um warning Starlette/httpx.
- `./scripts/scan-ci-safety` passa na `main`.
- S04 registrou `hash/v1` com `precision@5 = 0.0` e NO-GO.
- S05 registrou GO condicional apenas para Alpha local/self-hosted.
- S07 atual é obsoleto: auditou estado `UNBORN` anterior ao commit inicial.
- S08 selecionou provisoriamente `intfloat/e5-small-v2`, 384 dimensões, mas o
  harness usa `query: ` apenas na consulta e omite `passage: ` nas memórias.
- `README.md`, `docs/known-issues.md`, `docs/roadmap.md`, S06 e S07 contêm
  claims históricas que precisam ser reconciliadas.
- O schema PostgreSQL continua fixado em `vector(64)` e o repository rejeita
  dimensão diferente de 64.
- Não existe lock/constraints completo, SBOM ou release audit final por SHA.

## 5. Fases e checkpoints

---

## Fase 0 — Baseline, proteção e inventário

### Objetivo

Criar uma fotografia confiável antes de qualquer alteração e garantir que a
S08 temporária não seja perdida.

### Ações

1. Inspecionar `main`, worktrees, branches, remotes e status.
2. Inventariar exatamente os arquivos S08, tamanho e checksums.
3. Confirmar que caches/pesos de modelos não serão versionados.
4. Validar checksums do corpus e dos relatórios históricos S04/S08.
5. Executar na `main`:

   ```bash
   ./scripts/gate-fast
   pytest -q tests/evals
   ./scripts/scan-ci-safety
   ```

6. Executar os mesmos gates não destrutivos na worktree S08.
7. Criar `docs/handoffs/alpha/GOAL-PROGRESS.md` na branch de trabalho.
8. Registrar qualquer divergência do inventário inicial deste documento.

### Aceite

- Nenhum arquivo S08 perdido.
- Corpus byte-a-byte preservado.
- Baseline e falhas existentes reproduzidos ou explicitamente classificados.
- Nenhuma escrita remota.

---

## Fase 1 — Correção e fechamento metodológico da S08

### Objetivo

Transformar a seleção E5 de evidência promissora em experimento development
metodologicamente correto e revisável.

### Ações obrigatórias

1. Ler o model card pinado e o paper E5. Confirmar a convenção para retrieval
   assimétrico: `query: ` nas consultas e `passage: ` nos documentos.
2. Alterar o harness experimental para suportar prefixos separados e explícitos
   (`query_prefix` e `passage_prefix`).
3. Fazer a ausência de ambos os prefixos falhar de forma clara para modelos E5.
4. Não alterar `retrieval-v0`, labels, gates, threshold ou split.
5. Adicionar testes para:
   - prefixo de query;
   - prefixo de passage;
   - nenhuma leitura de holdout;
   - dimensão e revisão pinadas;
   - falha sem cache/revisão local correta;
   - artifacts contendo apenas IDs de falha;
   - determinismo da ordenação.
6. Reexecutar exatamente dois candidatos no split development.
7. Produzir novo diretório de relatório com SHA/base e timestamp, sem
   sobrescrever o relatório S08 anterior.
8. Comparar o resultado corrigido com o relatório anterior e explicar qualquer
   mudança.
9. Atualizar ADR 0006 e handoff S08 para distinguir:
   - primeira execução metodologicamente incompleta;
   - execução corrigida;
   - candidato final para S09 ou NO-GO.
10. Validar links, checksums, secrets/canário e `gate-fast`.

### Decisão

- Se E5 continuar atendendo todos os gates de development, avançar para S09.
- Se E5 falhar, encerrar a linha E5 com NO-GO e criar uma experiência separada;
  não introduzir um terceiro modelo silenciosamente.

### Aceite

- Relatório corrigido imutável e associado ao SHA/base.
- Holdout comprovadamente não executado.
- Decisão reproduzível e sem tuning de gate.

### Checkpoint de Git

Preparar uma lista exata de paths. Solicitar autorização explícita para stage e
commit da S08 corrigida. Não fazer push neste checkpoint sem autorização
separada.

---

## Fase 2 — Arquitetura S09 e plano de compatibilidade

### Objetivo

Definir a mudança de produção antes de tocar em dados ou migrations.

### Entregáveis

- `docs/adr/0007-e5-runtime-and-reembedding.md`.
- `docs/handoffs/alpha/S09-design-review.md`.
- Matriz de compatibilidade e rollback.

### Decisões obrigatórias

1. Runtime de inferência:
   - comparar `torch + transformers`, ONNX Runtime e outra opção local mínima
     somente se necessário;
   - medir tamanho instalado, cold start, memória, licença e plataformas;
   - escolher uma única implementação suportada para Alpha;
   - manter dependências semânticas em extra explícito se o pacote base não
     precisar carregar centenas de MB.
2. Aquisição de pesos:
   - revisão imutável;
   - hashes verificados;
   - cache configurável;
   - modo offline fail-closed;
   - download inicial explícito do operador;
   - nenhuma telemetria de conteúdo.
3. Modelo de dados:
   - permitir coexistência controlada de `hash/v1` 64d e E5 384d;
   - impedir busca cross-profile/cross-dimension;
   - evitar conversão destrutiva in-place sem rollback;
   - escolher tabela paralela, coluna paralela ou migration forward equivalente.
4. Re-embedding:
   - job retomável e idempotente;
   - execução por owner/lote;
   - checkpoint e contagem;
   - preservação de lifecycle/state/space/provenance;
   - nenhuma reativação de memória esquecida;
   - reconciliação de writes concorrentes;
   - verificação antes do cutover.
5. Cutover/rollback:
   - configuração/feature gate explícita;
   - E5 somente após cobertura completa;
   - `hash/v1` legível durante janela definida;
   - rollback por forward-fix/configuração ou restore verificado;
   - nunca depender de downgrade destrutivo em dados reais.

### Aceite

- ADR aprovado internamente pelos testes de contrato propostos.
- Nenhuma migration executada em banco real.
- Caminho de upgrade e rollback compreensível sem conhecimento implícito.

---

## Fase 3 — Provider E5 de produção

### Objetivo

Implementar o provider local semântico isolado atrás do port existente.

### Ações

1. Implementar provider com:
   - metadata de profile/version/dimension;
   - mean pooling e normalização idênticos ao harness validado;
   - prefixos corretos;
   - local-files-only após provisionamento;
   - limites de tokens documentados;
   - erros estáveis sem payload sensível;
   - thread/process safety compatível com a composição.
2. Adicionar seleção explícita por configuração.
3. Manter `hash/v1` como fallback somente quando selecionado, nunca como
   fallback silencioso após falha E5.
4. Não importar torch/transformers no caminho base quando o extra semântico não
   estiver selecionado.
5. Testar:
   - vetores normalizados 384d;
   - determinismo dentro da tolerância definida;
   - prefixes;
   - ausência de pesos;
   - revisão/hash incorretos;
   - erro opaco;
   - config segura sem caminhos/secrets em status.
6. Medir cold start, warm latency e memória local.

### Aceite

- Unit e contract verdes.
- Import do pacote base continua funcionando sem dependências semânticas.
- Nenhuma chamada de rede no runtime normal/offline.

---

## Fase 4 — Migration e coexistência de embeddings

### Objetivo

Adicionar armazenamento 384d e preservar rollback sem corromper o perfil 64d.

### Regras de segurança

- Usar somente banco descartável identificado pelo compose do projeto durante
  desenvolvimento.
- Antes de qualquer ensaio com dados persistentes: backup, hash do dump,
  restore em banco separado e smoke verificado.
- Não aprovar uma migration cujo downgrade apague dados silenciosamente.

### Cobertura mínima

1. Upgrade zero → head em banco vazio.
2. Upgrade `0002` → nova head com dados `hash/v1` existentes.
3. Coexistência 64d/384d sem busca cruzada.
4. Unique constraints por owner/memory/profile/version.
5. Forget removendo/cascateando todos os perfis online.
6. Export default ainda sem embeddings.
7. Import compatível ou erro versionado explícito.
8. Backup/restore com os dois perfis.
9. Downgrade apenas em fixture descartável, documentando perda potencial.
10. Índices pgvector adequados à métrica escolhida e plano de query validado.

### Aceite

- Gate PostgreSQL integral verde, sem skips.
- Migration head única e reproduzível.
- Dados `hash/v1` preservados após upgrade.
- Nenhuma busca aceita dimensão incompatível.

---

## Fase 5 — Job de re-embedding e cutover

### Objetivo

Materializar embeddings E5 com retomada segura e ativar o profile somente após
verificação.

### Ações

1. Criar comando administrativo explícito, nunca automático no startup.
2. Implementar dry-run, owner scope, batch size e resume cursor.
3. Registrar somente IDs/contagens/tempo; nunca conteúdo.
4. Tratar memória atualizada durante o job com version check/retry limitada.
5. Ignorar/reconciliar estados forgotten/superseded conforme contrato.
6. Tornar rerun idempotente.
7. Produzir relatório de cobertura:
   - elegíveis;
   - concluídas;
   - desatualizadas;
   - falhas;
   - órfãs;
   - duração e throughput.
8. Bloquear cutover se cobertura/correção não forem 100% para o escopo.
9. Exercitar rollback de configuração para `hash/v1`.

### Aceite

- Interrupção e retomada testadas.
- Writes concorrentes testados.
- Forget durante/depois do job testado.
- Cutover e rollback testados via MCP/SDK/CLI.

---

## Fase 6 — Avaliação end-to-end em development

### Objetivo

Confirmar que o ganho offline existe no caminho real PostgreSQL/gateway.

### Ações

1. Executar o corpus development via provider, repository e gateway reais.
2. Usar threshold `0.78`, mesmos gates e labels congelados.
3. Medir:
   - precision@5;
   - intrusion@5;
   - abstention;
   - owner/state/space/profile/lifecycle;
   - slices positivos e cross-domain;
   - p50/p95 end-to-end;
   - cold start/memória;
   - custo externo zero.
4. Comparar harness vs caminho real e investigar divergência.
5. Não tocar no holdout.
6. Se development falhar, corrigir implementação e repetir development,
   preservando todos os relatórios; não ajustar gates.

### Aceite

- Todos os gates development verdes no caminho suportado.
- Relatório associado ao SHA e ambiente.
- Nenhuma falha determinística de isolamento/lifecycle.

---

## Fase 7 — Holdout selado

### Pré-condições duras

- Development integralmente verde.
- Provider/migration/re-embedding congelados em commit revisável.
- Threshold, configs e gates congelados.
- Nenhuma mudança de produção planejada após ver o holdout.

### Protocolo

1. Registrar SHA, status limpo, checksums e configuração antes da execução.
2. Executar o holdout uma única vez.
3. Não fazer tuning pós-holdout no mesmo candidato/release.
4. Emitir métricas agregadas, slices e failures somente com IDs.
5. Se falhar, declarar NO-GO e abrir nova geração experimental; não reutilizar
   o holdout como development.

### Aceite

- Gate B GO objetivo ou NO-GO honesto.
- Relatório imutável, checksums e comandos reproduzíveis.

---

## Fase 8 — Privacy, operações e resiliência S05-R2

### Objetivo

Revalidar claims após introduzir modelo, cache e re-embedding.

### Cobertura

- Cache/pesos não contêm corpus nem conteúdo do usuário.
- Logs/traces/errors do provider e job não vazam texto, SQL, URL ou secret.
- Timeout não gera retry storm.
- Readiness falha fechada sem modelo/pesos/banco requeridos.
- Shutdown fecha engine e recursos do modelo.
- Backup/restore preserva perfis e permite reaplicar forget/tombstones.
- Forget remove embeddings 64d e 384d online.
- Export continua sensível e sem vetores por default.
- Outage do modelo/cache tem erro estável, sem fallback remoto/hash silencioso.
- Retenção de cache, dumps, exports, logs e artifacts documentada.
- Scanner de canário passa em runtime output e artifacts.

### Aceite

- Novo `docs/handoffs/alpha/S05-R2-semantic-privacy-ops.md` com GO condicional
  limitado a local/self-hosted.
- Threat model e privacy claim matrix atualizados.

---

## Fase 9 — Packaging e supply chain reproduzíveis

### Objetivo

Eliminar findings de build não reproduzível e instalação incompleta.

### Ações

1. Definir constraints/lock por Python/plataforma suportados.
2. Pin de build tools e hashes quando aplicável.
3. Definir extra semântico e comportamento sem ele.
4. Garantir que wheel/sdist contenham migrations, `alembic.ini` ou outro caminho
   de inicialização suportado sem exigir checkout implícito.
5. Construir wheel/sdist duas vezes em ambientes limpos e comparar conteúdo;
   documentar fontes legítimas de não determinismo se houver.
6. Instalar wheel em Python 3.11 limpo e executar:
   - `pip check`;
   - import/version;
   - `omp --help`;
   - migration zero → head;
   - status/readiness;
   - quickstart MCP;
   - smoke semântico quando o extra estiver instalado.
7. Gerar SBOM e inventário de licenças.
8. Auditar vulnerabilidades das dependências runtime, semantic extra e build
   tools atualizadas.
9. Scan de secrets, paths locais, dumps, corpus indevido e pesos acidentais.
10. Não incluir pesos grandes no pacote salvo decisão explícita documentada.

### Aceite

- Instalação limpa não depende do checkout.
- Nenhuma vulnerabilidade bloqueadora não aceita/documentada.
- Licenças compatíveis.
- Artifacts associados ao SHA e checksums publicados no handoff, não enviados
  externamente ainda.

---

## Fase 10 — Reconciliação documental e governança

### Objetivo

Fazer cada claim pública corresponder ao comportamento e à evidência atual.

### Arquivos mínimos

- `README.md`;
- `CHANGELOG.md`;
- `docs/known-issues.md`;
- `docs/roadmap.md`;
- `docs/support-matrix.md`;
- `docs/installation.md`;
- `docs/mcp.md`, `docs/sdk.md`, `docs/cli.md`;
- `docs/privacy.md`, `docs/threat-model.md`;
- runbook local;
- S04–S09 e handoffs R2.

### Correções obrigatórias

- Remover claims falsas de que S04/S05 estão ausentes.
- Marcar S07 original como auditoria histórica superada, sem apagá-la.
- Explicar `hash/v1` como baseline/rollback e E5 como profile candidato ou
  aprovado conforme o holdout real.
- Documentar download/cache/offline/model size/cold start.
- Documentar upgrade, re-embedding, rollback e impacto de backup/restore.
- Manter limites hosted/E2EE/zero knowledge/scale explícitos.
- Verificar todos os links e snippets executáveis.

### Aceite

- Nenhuma contradição conhecida entre README, known issues, roadmap, privacy,
  handoffs e reports.
- Quickstart copiado da documentação passa no wheel limpo.

---

## Fase 11 — CI, remoto e controles GitHub

### Objetivo

Obter evidência externa dos checks no SHA candidato.

### Autorizações

Antes de qualquer escrita GitHub, solicitar separadamente:

1. autorização para stage;
2. autorização para commit;
3. autorização para push da branch;
4. autorização para criar PR;
5. autorização para alterar branch protection/security settings.

Tag e GitHub Release não pertencem a esta fase.

### Checks obrigatórios

- `quality`;
- `postgres-e2e` sem skips;
- `package`;
- `security-artifacts`;
- semantic development/holdout verification apropriada sem baixar modelos de
  forma mutável;
- dependency/license/SBOM audit;
- link/snippet checks.

### Controles GitHub

- Private Vulnerability Reporting habilitado e verificado.
- PR obrigatório para `main`.
- Required checks com nomes reais observados após primeira execução.
- Sem aprovação administrativa que permita bypass silencioso.
- Artifacts com retenção mínima e sem dados sensíveis.

### Aceite

- SHA remoto correspondente ao local.
- Todos os checks obrigatórios verdes.
- Branch protection e canal de segurança verificados.

---

## Fase 12 — Auditoria independente S07-R2

### Objetivo

Executar auditoria final sem corrigir findings silenciosamente durante a
própria auditoria.

### Requisitos do auditor

- Trabalhar a partir do SHA candidato limpo.
- Reexecutar comandos, não confiar apenas em handoffs.
- Separar PASS, FAIL, INCONCLUSIVE e NOT APPLICABLE.
- Comparar artifacts locais e CI.
- Verificar que relatórios antigos `UNBORN` continuam históricos e que os
  relatórios atuais carregam SHA correto.

### Checklist final

- Git/worktree limpos.
- Quality completo.
- PostgreSQL/pgvector/migrations.
- MCP/SDK/CLI E2E.
- Development e holdout.
- Privacy/ops/backup/restore/forget/outage.
- Re-embedding/resume/cutover/rollback.
- Build limpo e instalação fora do checkout.
- Dependências/licenças/SBOM/vulnerabilidades.
- Secrets/canário/artifact contents.
- Docs/links/snippets/claims.
- GitHub CI/security settings.

### Saída

Criar `docs/handoffs/alpha/S07-R2-rc-audit.md` com:

- SHA e ambiente;
- tabela de gates;
- findings por severidade/owner;
- riscos aceitos;
- GO ou NO-GO objetivo;
- lista exata de ações exclusivas do mantenedor.

### Regra

Se houver blocker, voltar à fase responsável, corrigir em commit separado e
repetir a auditoria. Não declarar GO parcial.

---

## Fase 13 — Handoff de publicação

### Objetivo

Deixar o projeto pronto para decisão humana, sem publicar automaticamente.

### Entregáveis

- SHA candidato;
- versão/tag proposta;
- release notes finais;
- checksums wheel/sdist/SBOM;
- matriz de CI verde;
- S07-R2 GO;
- known issues residuais;
- comandos exatos para tag e GitHub Release;
- plano de rollback da release.

### Limite

O goal deve parar antes de criar tag ou GitHub Release e solicitar autorização
explícita. PyPI permanece fora do plano, salvo nova decisão explícita.

## 6. Matriz resumida de gates

| Gate | Condição mínima |
| --- | --- |
| Git | SHA limpo, artifacts e reports atribuíveis |
| Ruff | zero violações |
| Mypy | zero issues em `src` |
| Unit/contract | 100% pass; warning conhecido documentado |
| PostgreSQL | 16 + pgvector pinado, migrations e testes sem skips |
| Retrieval development | precision@5 >= 0.80; intrusion <= 0.10; abstention >= 0.90; isolation/lifecycle = 1.00; p95 < 2500 ms |
| Holdout | mesmos gates, uma execução selada, sem tuning posterior |
| Privacy/ops | canário, forget, backup/restore, outage e retenção verificados |
| Re-embedding | resumível, idempotente, concorrência e rollback testados |
| Package | wheel/sdist limpos, instalação fora do checkout e migrations funcionais |
| Supply chain | constraints, SBOM, licenças e vulnerabilidades revisadas |
| Docs | claims, links, snippets e versões coerentes |
| CI | todos required checks verdes no SHA remoto |
| Audit | S07-R2 GO sem P0/P1 abertos |

## 7. Definition of Done

O goal somente pode ser marcado como concluído quando todos os itens abaixo
forem verdadeiros:

- [ ] S08 foi preservada em Git e corrigida com `query:`/`passage:`.
- [ ] O corpus congelado e os relatórios históricos foram preservados.
- [ ] O candidato E5 passou development corrigido ou houve NO-GO formal com
      substituição tratada em nova experiência autorizada.
- [ ] Provider de produção local implementado e configurável.
- [ ] Runtime não faz fallback remoto nem network call implícita.
- [ ] Storage suporta 384d sem corromper ou misturar 64d.
- [ ] Migration upgrade e rollback operacional foram testados com segurança.
- [ ] Re-embedding resumível/idempotente passou concorrência e forget.
- [ ] Cutover e rollback `E5 ↔ hash/v1` foram exercitados.
- [ ] Development end-to-end passou no caminho PostgreSQL/MCP real.
- [ ] Holdout selado foi executado uma vez e passou.
- [ ] Privacy/ops S05-R2 está verde no escopo local/self-hosted.
- [ ] Quality, integration e E2E estão verdes sem skips silenciosos.
- [ ] Wheel/sdist são instaláveis fora do checkout e inicializam o banco.
- [ ] Constraints/lock, SBOM, licenças e auditoria de vulnerabilidades existem.
- [ ] README, known issues, roadmap, privacy e handoffs estão reconciliados.
- [ ] GitHub contém o SHA candidato e todos os required checks estão verdes.
- [ ] Private Vulnerability Reporting e branch protection foram verificados.
- [ ] S07-R2 concluiu GO sem blockers P0/P1.
- [ ] Release notes, artifacts e checksums estão prontos.
- [ ] Nenhuma tag/release/PyPI foi criada sem autorização explícita.

## 8. Condições legítimas de bloqueio

O executor pode pausar um ramo somente quando precisar de:

- autorização de download/rede/Docker;
- autorização para migration destrutiva em fixture descartável;
- confirmação de que uma URL de banco é descartável;
- stage/commit/push/PR/settings GitHub;
- abertura do holdout após pré-condições;
- decisão de licença/model distribution com impacto material;
- tag/GitHub Release.

Ao bloquear, registrar:

1. fase e SHA;
2. trabalho concluído;
3. comando/ação exata pendente;
4. risco e escopo;
5. autorização mínima solicitada;
6. próximo passo automático após aprovação.

Não usar “preciso de confirmação” para decisões reversíveis já cobertas por
este plano.

## 9. Relatório final esperado do Luna

O relatório final deve começar pela decisão e conter apenas evidência
verificável:

1. `GO` ou `NO-GO`;
2. SHA candidato e status local/remoto;
3. tabela curta de gates;
4. métricas development/holdout;
5. migration/re-embedding/rollback;
6. package/supply-chain;
7. privacy/ops;
8. CI e auditoria S07-R2;
9. riscos residuais;
10. única ação humana restante.

Se a única ação restante for publicação, o relatório deve dizer claramente:
“RC auditado e pronto; tag e GitHub Release aguardam autorização explícita”.
