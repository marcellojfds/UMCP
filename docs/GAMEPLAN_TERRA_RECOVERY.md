# OMP Alpha — Terra Recovery Gameplan

> **Gameplan histórico.** A investigação de thresholds ajudou a identificar o
> defeito atual, mas estas instruções não são mais uma fila ativa. Consulte
> [`known-issues.md`](known-issues.md).

**Criado em:** 2026-08-20
**Executor recomendado:** `gpt-5.6-terra`
**Reasoning recomendado:** `xhigh` para as fases de eval/arquitetura; `high`
para implementação e fechamento
**Base conhecida:** `4947ebfb3789558892c242e0d7a8743256f3656d`
**Estado:** goal Luna pausado corretamente; release **NO-GO**

## 1. Tese de recuperação

Não iniciar tentando um quarto embedding. O estado atual sugere que o
protocolo de comparação mistura duas decisões diferentes:

1. qualidade da ordenação semântica produzida pelo modelo; e
2. calibração do threshold absoluto usado para servir ou abster resultados.

O threshold `0.78` nasceu no plano do baseline `hash/v1`. E5 e BGE possuem
distribuições de cosine distintas. O BGE retornou zero positivos em
development exatamente nesse threshold, enquanto seu model card alerta que
thresholds absolutos dependem da distribuição do modelo e dos dados. Isso não
prova que BGE ordena bem, mas também não prova que ordena mal.

O Terra deve primeiro auditar a avaliação e estabelecer um protocolo de
calibração por profile usando somente development. O gate público não será
reduzido: `precision@5 >= 0.80`, `intrusion@5 <= 0.10`, abstention `>= 0.90`,
isolamento/lifecycle `= 1.00` e p95 `< 2500 ms` permanecem fixos.

Se nenhum profile existente passar um protocolo development honesto, a segunda
opção é experimentar retrieval híbrido com os componentes já locais, ainda
sem abrir holdout. Um novo modelo é apenas a terceira opção e exige nova
autorização.

## 2. Resultado final desejado

Chegar a um dos dois estados honestos:

### Estado A — Alpha semanticamente aprovado

- um profile existente ou híbrido passa development pré-registrado;
- configuração e código são congelados num SHA limpo;
- o mantenedor autoriza uma única execução selada do holdout;
- holdout passa;
- CI remoto e controles GitHub ficam verdes;
- auditoria independente S07-R2 conclui GO.

### Estado B — Engineering preview publicável, sem claim semântica

- nenhum candidato passa development;
- semantic retrieval é removido do escopo do Alpha público ou mantido apenas
  como experimental, disabled-by-default;
- `hash/v1` não é apresentado como retrieval de qualidade;
- holdout continua fechado porque não existe candidato elegível;
- toda a engenharia já concluída é preservada;
- uma auditoria redefine o release como engineering preview com limites
  explícitos.

O Terra não pode decidir sozinho entre Estado A e B. Se a trilha semântica
continuar vermelha após as experiências autorizadas, deve apresentar a decisão
ao mantenedor em vez de continuar testando modelos indefinidamente.

## 3. Prompt recomendado para a sessão Terra

Usar uma nova tarefa/worktree baseada no estado de trabalho atual somente após
preservar o diff. Selecionar `gpt-5.6-terra`, reasoning `xhigh`, e enviar:

```text
Execute docs/GAMEPLAN_TERRA_RECOVERY.md como coordenador técnico do recovery do OMP Alpha. Comece auditando o protocolo de retrieval e a integridade do diff atual; não adquira outro modelo, não leia holdout e não altere gates públicos. Use somente development para determinar se E5 ou BGE falham por ranking ou por calibração do threshold. Pré-registre qualquer calibração por profile e valide-a por episódios/folds, sem medir e selecionar no mesmo conjunto. Se um candidato existente passar, congele config e código antes de solicitar autorização de holdout. Se nenhum passar, avalie uma única experiência híbrida previamente especificada usando componentes locais; não faça busca aberta de modelos. Preserve toda evidência histórica. Stage, commit, push, PR, holdout, configurações GitHub, tag e release exigem autorizações explícitas separadas. Não declare GO sem SHA limpo, CI remoto verde e auditoria independente S07-R2.
```

## 4. Regras invariantes

- Não ler, listar resultados por query ou executar o holdout.
- Não alterar corpus, labels ou gates para obter verde.
- Não sobrescrever relatórios anteriores.
- Não tratar threshold de um profile como universal sem evidência.
- Não escolher threshold e declarar resultado final sobre os mesmos episódios.
- Fazer splits/calibração por episódio, nunca por linha.
- Não adquirir novo modelo sem autorização específica de ID, revisão e escopo.
- Não integrar BGE em runtime se ele não passar development.
- Não misturar perfis/dimensões em uma busca.
- Não fazer fallback silencioso entre E5, BGE e hash.
- Não executar downgrade ou reset em banco não comprovadamente descartável.
- Não stagear caches, venvs, pesos, dumps ou artifacts de `/private/tmp`.
- Stage, commit, push, PR, holdout, settings GitHub, tag e release são
  autorizações diferentes.
- Manter `docs/handoffs/alpha/TERRA-RECOVERY-PROGRESS.md` atualizado a cada
  checkpoint.

## 5. Fases

---

## T0 — Preservar o estado e auditar o diff

### Objetivo

Converter o worktree grande e não commitado em inventário revisável antes de
qualquer nova experiência.

### Ações

1. Registrar SHA, branch, remotes e todos os worktrees.
2. Gerar inventário de modified/untracked com classificação:
   - eval/harness/reports;
   - provider/re-embedding;
   - schema/migrations;
   - packaging/supply chain;
   - docs/governança;
   - caches/pesos proibidos.
3. Verificar que os artifacts externos citados em `/private/tmp` ainda existem
   e conferir seus checksums.
4. Inspecionar cada diff; não assumir que gate verde substitui code review.
5. Rodar gates não destrutivos:

   ```bash
   ./scripts/gate-fast
   pytest -q tests/evals
   ./scripts/scan-ci-safety
   ```

6. Rodar o gate PostgreSQL apenas em compose descartável cuja URL seja
   confirmada antes do downgrade.
7. Criar uma matriz “entregável → teste → handoff → status”.

### Aceite

- Nenhuma evidência perdida.
- Nenhum arquivo proibido incluído no escopo de Git.
- Diff explicado por conjuntos lógicos.
- Gates atuais reproduzidos.

---

## T1 — Auditoria matemática e semântica do eval

### Objetivo

Determinar se E5/BGE falharam por baixa qualidade de ranking, por threshold ou
por uma combinação dos dois.

### Trabalho somente com development

1. Para cada query development e cada profile já adquirido, gerar um artifact
   diagnóstico separado contendo somente IDs e scores:
   - top-50 antes do threshold;
   - rank do primeiro relevante;
   - scores de relevantes;
   - scores de irrelevantes/hard negatives;
   - melhor score de queries negativas;
   - filtros owner/state/space aplicados.
2. Calcular métricas independentes de threshold:
   - Recall@1/@5/@10/@50;
   - MRR;
   - nDCG@5;
   - coverage de positivos no candidate set;
   - separação de score relevante vs negativo.
3. Recalcular as métricas públicas no threshold `0.78` apenas como baseline.
4. Auditar manualmente a implementação de `precision@5`, denominator, labels e
   slices contra exemplos pequenos calculados à mão.
5. Verificar se filtros são aplicados antes do ranking nos dois caminhos.
6. Verificar se harness e PostgreSQL usam exatamente:
   - pooling;
   - normalização;
   - prefixos/instruções;
   - cosine/operator pgvector;
   - candidate/result limits;
   - mesma versão do texto.
7. Comparar scores harness vs PostgreSQL para fixtures idênticas dentro de
   tolerância explícita.

### Classificação obrigatória

Para cada profile, concluir uma destas categorias:

- `RANKING_NO-GO`: relevantes não aparecem bem mesmo antes do threshold.
- `CALIBRATION_NO-GO`: ranking é suficiente, mas `0.78` elimina resultados.
- `MIXED_NO-GO`: ranking e calibração falham.
- `IMPLEMENTATION_BUG`: divergência de pooling, prefixo, filtro ou operador.
- `INCONCLUSIVE`: evidência insuficiente.

### Aceite

- Relatório `docs/handoffs/alpha/T01-eval-diagnostic.md`.
- Nenhum holdout tocado.
- Causa de cada NO-GO estabelecida com métricas, não impressão subjetiva.

---

## T2 — ADR de calibração por profile

### Pré-condição

Executar somente se T1 mostrar ranking development potencialmente suficiente.

### Objetivo

Corrigir o protocolo sem reduzir os gates públicos ou viciar o holdout.

### Protocolo proposto

1. Criar `docs/adr/0008-profile-threshold-calibration.md` antes de executar o
   sweep.
2. Registrar que `0.78` continua sendo o threshold histórico de `hash/v1`, mas
   não um universal físico entre embedding spaces.
3. Congelar uma grade finita de thresholds antes de medir. Exemplo:
   - quantis derivados somente do fold de calibração; ou
   - grade explícita `0.50..0.90` com passo `0.01`.
4. Fazer validação cruzada por episódio dentro de development:
   - folds determinísticos e versionados;
   - em cada rodada, selecionar threshold apenas nos folds de calibração;
   - avaliar métricas no fold development-validation não usado na seleção;
   - agregar somente resultados out-of-fold.
5. Regra de seleção pré-registrada:
   - primeiro satisfazer abstention >= 0.90 e intrusion <= 0.10;
   - entre thresholds elegíveis, maximizar precision@5;
   - desempatar pelo threshold maior e depois por valor determinístico.
6. Exigir também o floor de slices previsto no EVALS_PLAN.
7. Preservar todos os sweeps e failures por IDs.
8. Não promover o threshold até o out-of-fold development passar integralmente.

### Observação importante

Isso não “baixa o gate”. O target de qualidade continua idêntico; muda apenas
a calibração operacional do profile, feita sem acesso ao holdout. Se o
mantenedor considerar `0.78` uma decisão imutável para todos os modelos, T2
deve ser bloqueada e o projeto seguirá para T3/T4 ou Estado B.

### Aceite

- ADR anterior ao resultado.
- Testes do calibrador e folds.
- Métricas out-of-fold verdes para um profile ou NO-GO objetivo.

---

## T3 — Fechar bugs ou promover o melhor profile existente

### Caminhos

#### Se T1 encontrar bug

1. Corrigir em commit lógico separado após autorização.
2. Adicionar regressão mínima.
3. Reexecutar development com config original e relatório novo.
4. Não reinterpretar relatório antigo.

#### Se T2 aprovar E5

1. Manter E5 como único candidato de produção.
2. Configurar threshold versionado no `EmbeddingProfile`.
3. Reexecutar caminho PostgreSQL/gateway real.
4. Confirmar migrations, re-embedding, cutover e rollback já implementados.
5. Atualizar ADR 0007 e handoff S09.

#### Se T2 aprovar BGE

1. Primeiro implementar provider BGE específico com CLS e query instruction.
2. Não reutilizar mean pooling E5.
3. Rodar unit/contract/integration e re-embedding.
4. Somente depois medir PostgreSQL/gateway.

### Aceite

- Exatamente um profile candidato.
- Development harness e PostgreSQL/gateway verdes.
- Configuração/pesos/revisão/threshold congelados.
- Holdout ainda fechado.

---

## T4 — Uma experiência híbrida, somente se necessária

### Pré-condição

Executar apenas se nenhum profile existente passar T2 e após autorização do
mantenedor para esta experiência algorítmica.

### Hipótese

Combinar o ranking E5, que ficou próximo do gate, com sinal lexical local pode
recuperar queries de alto overlap sem sacrificar cross-domain.

### Escopo fechado

- Sem novo modelo.
- PostgreSQL full-text search ou sinal lexical determinístico já disponível.
- Fusão pré-especificada, preferencialmente Reciprocal Rank Fusion.
- Mesmos owner/state/space/profile filters antes da fusão.
- Pesos/constante RRF congelados antes da avaliação final ou selecionados pelo
  mesmo protocolo cross-validation de T2.
- Threshold/abstention calibrados somente por folds development.
- Sem reranker LLM/API externa.

### Gates

Os gates públicos e floors de slices permanecem iguais. Comparar E5 puro vs
híbrido nos mesmos folds e publicar custo/latência.

### Aceite

- Híbrido passa out-of-fold development e PostgreSQL real; ou NO-GO formal.
- Uma única experiência híbrida; não abrir busca combinatória.

---

## T5 — Decisão do mantenedor: candidato ou preview

### Pacote de decisão

O Terra deve apresentar uma tabela:

| Opção | Evidência | Risco | Próximo passo |
| --- | --- | --- | --- |
| E5 calibrado | development OOF + PG | generalização | congelar e pedir holdout |
| BGE calibrado | development OOF + PG | nova integração | congelar e pedir holdout |
| Híbrido | development OOF + PG | maior complexidade | congelar e pedir holdout |
| Engineering preview | nenhum candidato passa | sem claim semântica | retirar Gate B do release público |
| Novo modelo | experiência ainda necessária | tempo/custo/Goodhart | pedir autorização específica |

O mantenedor escolhe uma rota. O executor não testa automaticamente outro
modelo.

---

## T6 — Higiene Git e criação do SHA limpo

### Pré-condição

Code review do diff T0–T5 e autorização explícita.

### Estratégia

1. Criar branch de feature `terra-alpha-recovery` antes de commits.
2. Preparar commits pequenos e auditáveis:
   - `eval: preserve corrected semantic experiments and diagnostics`;
   - `feat: add semantic profile storage and re-embedding`;
   - `build: add packaged migrations constraints and supply-chain gates`;
   - `docs: reconcile alpha evidence and release boundaries`;
   - commit adicional para calibração/híbrido, se aplicável.
3. Para cada commit:
   - listar paths exatos;
   - mostrar diff/stat;
   - executar gates proporcionais;
   - solicitar autorização de stage;
   - solicitar autorização separada de commit.
4. Nunca versionar caches, pesos ou manifests temporários com paths locais.
5. Após os commits, exigir `git status --short` vazio.

### Aceite

- SHA limpo local.
- Histórico compreensível e bisectável.
- Relatórios apontam para o SHA correto ou registram claramente o SHA de
  produção que avaliaram.

---

## T7 — CI remoto e PR

### Autorizações separadas

1. Push da branch.
2. Criação de draft PR.
3. Alteração de branch protection.
4. Habilitação/verificação de PVR.

### Trabalho

- Push sem force.
- Draft PR contra `main`.
- Aguardar `quality`, `postgres-e2e`, `package` e `security-artifacts`.
- Adicionar gates semantic-development reproduzíveis sem baixar `main` mutável.
- Corrigir falhas em commits adicionais; não editar history publicada.
- Habilitar required checks pelos nomes reais observados.
- Habilitar Private Vulnerability Reporting e verificar `SECURITY.md`.

### Aceite

- SHA remoto igual ao local.
- Todos os required checks verdes.
- Branch protection/PVR comprovados.

---

## T8 — Pedido de autorização para holdout

### Só solicitar quando

- um candidato único passou out-of-fold development;
- o caminho PostgreSQL/gateway passou;
- config, threshold, pesos e código estão congelados;
- SHA local/remoto está limpo;
- CI está verde;
- não há tuning pendente.

### Pacote da solicitação

- SHA exato;
- model/revision/profile/threshold;
- checksums do corpus/config;
- métricas development e slices;
- declaração de que nenhum código mudará após ler holdout;
- comando exato que executará uma única vez;
- consequência automática: PASS continua; FAIL encerra candidato.

### Regra

Sem autorização explícita, não abrir holdout. A existência do gameplan não é
autorização implícita.

---

## T9 — Holdout selado

1. Confirmar SHA e tree limpa.
2. Executar uma única vez.
3. Gerar relatório/checksums sem conteúdo integral.
4. Não ajustar threshold/model/híbrido após resultado.
5. Se PASS, registrar Gate B GO.
6. Se FAIL, registrar NO-GO e voltar à decisão de produto, não ao tuning.

---

## T10 — Auditoria S07-R2 independente

Usar uma nova sessão Terra que não tenha escrito a implementação. Ela deve:

- partir do SHA remoto candidato;
- reexecutar quality, PG, E2E, package, privacy/ops e quickstart;
- validar development/holdout, migration e re-embedding;
- auditar SBOM/licenças/vulnerabilidades;
- verificar docs/links/snippets/claims;
- verificar CI, branch protection e PVR;
- não corrigir findings durante a auditoria;
- emitir `docs/handoffs/alpha/S07-R2-rc-audit.md` com GO/NO-GO.

Qualquer finding P0/P1 gera correção em outra sessão/commit e nova auditoria.

## 6. Autorizações mínimas previstas

O plano não as presume. O Terra deve pedi-las no momento certo:

1. experiência de calibração por profile, caso o mantenedor considere `0.78`
   universal e imutável;
2. experiência híbrida única, se necessária;
3. aquisição de novo modelo, somente se as rotas anteriores falharem;
4. acesso Docker/migration em banco descartável;
5. stage;
6. commit;
7. push;
8. draft PR;
9. branch protection/PVR;
10. execução única do holdout;
11. tag;
12. GitHub Release.

## 7. Stopping conditions

### O recovery pode avançar para holdout quando

- um candidato passa development out-of-fold e PG real;
- threshold/profile estão congelados;
- Git/CI estão limpos e verdes.

### O recovery deve parar para decisão do mantenedor quando

- E5, BGE e a experiência híbrida autorizada falham development;
- mudar o gate/corpus parece ser a única forma de obter verde;
- seria necessário reutilizar o holdout para desenvolvimento;
- um novo modelo precisa ser adquirido;
- a única alternativa é reduzir claims para engineering preview.

### O recovery está concluído quando

- holdout passa;
- S07-R2 é GO;
- CI/branch protection/PVR estão verdes;
- tag/release são as únicas ações restantes e aguardam autorização; ou
- o mantenedor escolhe formalmente engineering preview e a auditoria aprova
  esse escopo reduzido.
