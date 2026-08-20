# W00 — Contrato operacional para executores

## Objetivo

Permitir que modelos diferentes executem as frentes com baixo acoplamento, resultados revisáveis e handoffs consistentes. Este documento é obrigatório para todos os executores e não autoriza implementação fora do workstream recebido.

## Contexto mínimo

No momento deste planejamento, o diretório local contém apenas `manifest.md`, `project-context.md` e estes documentos de execução; não há produto implementado nem Git inicializado. O repositório remoto informado está vazio. Inicialização de versionamento, publicação remota e definição de branches pertencem ao coordenador/mantenedor e não devem ser presumidas por um executor isolado.

## Leitura mínima antes de começar

1. `manifest.md` — princípios e ambição do produto.
2. `project-context.md` — hipóteses, stack e questões abertas.
3. `docs/workstreams/README.md` — fases, gates e ownership.
4. O contrato da frente atribuída.
5. ADRs e contratos compartilhados que já existirem.

Se documentos divergirem, a ordem de precedência é: ADR aceito mais recente, contrato da frente, índice de workstreams, project context, manifesto. O manifesto continua soberano sobre a direção do produto; um ADR não pode transformar OMP em chat history ou CRUD de vetores sem decisão explícita do mantenedor.

## Escopo

### Dentro

- regras de preparação, implementação, validação e entrega;
- formato de decisões e handoff;
- limites de ownership entre frentes;
- protocolo para mudanças incompatíveis;
- perfis sugeridos de executor.

### Fora

- arquitetura de produto específica;
- schemas de domínio, banco ou MCP;
- priorização comercial;
- escolha automática de decisões marcadas para o mantenedor.

## Regras de execução

1. Inspecionar estado e mudanças existentes antes de editar; mudanças do usuário ou de outra frente devem ser preservadas.
2. Declarar a fase e o gate atendido. Não implementar itens de uma fase futura apenas porque parecem fáceis.
3. Trabalhar contra contracts/ports. Um fake pode desbloquear um adapter dependente, mas não deve virar contrato paralelo.
4. Não modificar artefato de ownership alheio sem registrar a necessidade e obter alinhamento do coordenador.
5. Todo comportamento público nasce com caso positivo, negativo, de autorização/isolamento e de erro.
6. Toda chamada de LLM, embedding ou reranker fica atrás de interface substituível e registra modelo/perfil sem registrar conteúdo sensível.
7. Defaults devem ser conservadores: não gravar automaticamente quando há dúvida e não recuperar quando o score não atinge o limiar.
8. Não alegar privacidade além do que W07 comprovar.
9. Não inserir dados pessoais reais em testes, examples ou fixtures.
10. Dependência nova precisa de justificativa de função, licença e custo operacional.

## Decisões já tomadas

- O MVP é um monólito modular, não microservices.
- O servidor, os use cases e os adapters são camadas distintas.
- PostgreSQL/pgvector é a única persistência primária inicial.
- MCP é a superfície de interoperabilidade; FastAPI oferece hosting/health e composição quando necessário.
- Evals são parte do produto e bloqueiam gates.
- Ambientes locais e CI usam dados sintéticos.

## Decisões abertas e autoridade

| Decisão | Quem prepara evidência | Quem aprova |
|---|---|---|
| versão mínima de Python e dependency manager | W01 | mantenedor |
| SDK MCP e estratégia de transporte | W04 | mantenedor/arquitetura |
| modelo e dimensão de embedding | W06 com W03 | mantenedor/arquitetura |
| thresholds e budgets iniciais | W08 com frente dona | mantenedor/produto |
| licença open source | W12 | mantenedor |
| criptografia e key management | W07 | mantenedor após review de segurança |
| provedor/modelo para writer/reranker | W05/W06 | mantenedor com dados de eval |

Questões abertas que não bloqueiam o incremento devem permanecer configuráveis ou adiadas; não devem virar abstrações especulativas.

## Artefatos compartilhados esperados

Os nomes exatos podem ser ajustados por W01, preservando as responsabilidades:

- `docs/adr/` — decisões arquiteturais versionadas;
- `docs/contracts/` — schemas públicos e exemplos canônicos;
- `src/.../domain/` — entidades e políticas sem adapters;
- `src/.../application/` — ports e casos de uso;
- `src/.../adapters/` — MCP, Postgres, embedding e LLM;
- `tests/` — unit, integration, contract e E2E;
- `evals/` — datasets, runners e relatórios reproduzíveis.

## Processo de mudança de contrato

1. Registrar problema concreto, consumidor afetado e evidência.
2. Propor a menor mudança possível em ADR curto.
3. Marcar compatibilidade: aditiva, deprecada ou breaking.
4. Atualizar primeiro o schema/contract test compartilhado.
5. Coordenar producers e consumers.
6. Para breaking change pública, versionar o protocolo e manter uma janela de migração quando já houver release.

## Dependências

- Fonte de produto: `manifest.md` e `project-context.md`.
- Autoridade de priorização e aprovação: mantenedor/coordenador.
- Contratos técnicos: W01–W12 conforme ownership no índice.

W00 não depende de implementação e deve ser lido antes de todas as outras frentes.

## Entregáveis

- regras comuns de execução e limites de ownership;
- matriz de autoridade para decisões abertas;
- processo de mudança de contrato;
- template de handoff;
- perfis de executor que permitam delegação sem amarrar o plano a um modelo específico.

## Etapas de aplicação

1. Coordenador escolhe fase, gate e frente pronta conforme o índice.
2. Executor lê o contexto mínimo e confirma dependências disponíveis.
3. Executor produz o incremento apenas no ownership recebido.
4. Executor executa critérios/testes da frente e registra evidência.
5. Coordenador revisa o handoff, integra e libera dependentes.

## Handoff obrigatório

Cada entrega termina com:

```text
Frente e fase:
Resultado entregue:
Arquivos criados/alterados:
Contratos públicos alterados:
Decisões/ADRs:
Comandos e testes executados:
Resultados de eval e baseline:
Riscos ou débitos conhecidos:
Itens explicitamente não feitos:
Próxima frente consumidora:
```

Relatos como “testes passaram” sem comando e escopo não satisfazem o handoff.

## Critérios de aceite deste contrato

- Cada workstream referencia este documento e possui ownership não ambíguo.
- Nenhum artefato crítico tem duas frentes como dona.
- Toda decisão cross-cutting tem uma autoridade de aprovação.
- Todo gate do índice pode ser demonstrado por evidência reprodutível.
- Um executor novo consegue identificar contexto, dependências, entrega e limite de atuação sem reler a conversa que originou o projeto.

## Testes do processo

- Dry run de planejamento: escolher W04 e listar todas as suas entradas sem assumir detalhes de W03.
- Dry run de conflito: simular mudança no campo `state` e verificar que W02 altera o contrato antes de W03/W04.
- Dry run de release: reconstruir o checklist do Gate B apenas com documentos do repositório.

## Riscos e mitigação

- **Contratos desatualizados:** contract tests e ADRs fazem parte do mesmo change set.
- **Implementações divergentes:** schemas canônicos são consumidos, não duplicados.
- **Overengineering:** cada frente separa MVP de futuro e precisa justificar qualquer item futuro antecipado.
- **Handoff opaco:** template obrigatório com evidência e riscos residuais.
- **Alterações simultâneas:** ownership e contratos primeiro; integração depois.

## Perfil sugerido do executor

Use o menor perfil capaz de concluir a frente:

- **P1 — execução determinística:** scaffolding, configuração, documentação mecânica e testes simples.
- **P2 — engenharia backend:** domínio, banco, concorrência, APIs e integração.
- **P3 — sistemas com modelos:** prompting estruturado, embeddings, ranking e evals probabilísticos.
- **P4 — segurança/privacidade:** threat modeling, criptografia, isolamento e revisão de claims.
- **P5 — DX e comunicação técnica:** SDK, CLI, exemplos, documentação e release.

Frentes podem pedir revisão por outro perfil, mas continuam com uma única ownership.

## Handoff deste workstream

W00 é consumido por todas as frentes. Mudanças nele exigem revisão do coordenador e devem informar quais contratos em andamento foram afetados.
