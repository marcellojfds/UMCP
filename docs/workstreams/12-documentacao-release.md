# W12 — Documentação e release open source

## Objetivo

Publicar um alpha compreensível, reproduzível e honesto: explicar o que OMP é, instalar/usar o MVP, integrar via MCP, avaliar suas limitações e contribuir com segurança. Esta frente organiza o release; não declara concluídas capacidades ainda experimentais.

## Contexto mínimo

O manifesto apresenta a tese. O project context é deliberadamente exploratório. A documentação pública precisa separar visão, comportamento disponível, roadmap e limitações, principalmente em privacidade e qualidade probabilística.

Leia W00, o índice e os handoffs de todas as frentes concluídas.

## Escopo

### Dentro

- README público e quickstart verificado;
- manifesto preservado e claramente identificado;
- architecture, memory model, protocol, retrieval e privacy docs;
- exemplos SDK/CLI/MCP executáveis;
- eval methodology e release report;
- contribution guide, code of conduct, security policy e governance mínima;
- licença, após decisão do mantenedor;
- changelog, versioning e release checklist;
- roadmap que distingue committed, experimental e future.

### Fora

- implementar features faltantes para melhorar narrativa;
- inventar benchmarks ou claims;
- definir licença sem aprovação do mantenedor;
- criar website/UI/brand system antes do alpha;
- prometer hosting, E2EE, escala ou compatibilidade não testada;
- manter documentação de contratos que pertence à frente dona sem seu review.

## Decisões já tomadas

- O alpha pode ocorrer após Gate B; writer, reranking, consolidation e crypto podem permanecer no roadmap.
- README começa pela proposta de valor e por um quickstart real.
- `manifest.md` é fonte conceitual e deve ser preservado; renomear/mover exige links/redirects e decisão explícita.
- Documentação diferencia “disponível”, “experimental”, “planejado” e “fora de escopo”.
- Privacy docs mencionam conteúdo legível no modo atual e leakage potencial de embeddings.
- Protocol examples usam schemas reais/golden fixtures.
- Todos os snippets são testados ou derivados de exemplos executáveis.
- O release inclui limitations e security reporting.

## Decisões abertas

- nome/package/release version inicial;
- licença open source e política de contribuições;
- idioma principal e estratégia PT/EN;
- status do protocolo: experimental `v0`, draft ou outro termo;
- canal de security disclosure;
- release automation e artifact publishing;
- escopo da documentação hospedada versus Markdown do repo.

## Dependências

- Gate B e relatório W08.
- W04: protocol reference e compatibility.
- W07: threat model e claim matrix.
- W09: quickstart/examples.
- W11: setup/runbooks/support matrix.
- Demais frentes: seus docs técnicos e handoffs.

Nenhuma frente depende do release completo para implementar, mas todas fornecem documentação owned por elas antes da publicação.

## Entregáveis

- `README.md` com status, quickstart, demo e roadmap;
- manifesto acessível e linkado;
- docs de arquitetura, memory model, protocolo, retrieval, evals e privacy;
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`;
- `LICENSE` após decisão explícita;
- changelog/release notes e support matrix;
- examples executáveis e troubleshooting;
- release checklist e verificação de links/snippets;
- alpha tag/package apenas quando autorizado pelo mantenedor.

## Estrutura pública mínima

```text
README
  -> o problema e a demonstração
  -> status/limitações
  -> quickstart
  -> uso MCP/SDK
  -> avaliação
  -> privacy
  -> roadmap/contribuição
```

Documentação profunda deve ser linkada, não duplicada no README.

## Etapas

1. Inventariar somente capacidades verificadas no Gate B.
2. Decidir com o mantenedor licença, versão, idioma e naming.
3. Executar o quickstart do zero usando release candidate.
4. Gerar/validar protocol examples contra W04 e SDK examples contra W09.
5. Incorporar report W08 e claim matrix W07 sem inflar conclusões.
6. Revisar onboarding de contribuidor, segurança e support matrix.
7. Rodar release checklist e produzir notes; publicação externa exige autorização explícita.

## Critérios de aceite verificáveis

- Uma pessoa sem contexto prévio completa o quickstart em ambiente suportado e reproduz o E2E canônico.
- Todos os comandos/snippets/link targets passam verificação automatizada ou checklist reproduzível.
- Cada feature citada tem status e link para evidência/teste.
- README não chama o sistema de E2EE/zero-knowledge nem omite embedding leakage.
- A spec MCP e os exemplos usam a mesma protocol version do servidor/SDK.
- Limitações incluem modo local, auth, privacy, escala testada e natureza experimental dos modelos.
- Contribuição e security reporting têm canais e expectativas claros.
- Licença foi escolhida explicitamente pelo mantenedor e todos os assets/dependencies são compatíveis.
- Release notes listam breaking changes, known issues e upgrade path.

## Testes e verificações

- fresh-machine/clean-environment quickstart;
- link checker e spell/style check apropriado;
- docs snippet/contract tests;
- package/license/security file audit;
- secret/PII scan em docs e examples;
- comparação claim matrix W07 versus README/release notes;
- matriz de compatibilidade servidor/SDK/transports;
- revisão por leitor que não participou da implementação.

## Riscos e mitigação

- **Visão confundida com produto atual:** status badges/seções explícitas e roadmap separado.
- **Docs drift:** exemplos executáveis e contrato como fonte.
- **Claim de privacy exagerada:** review obrigatório W07.
- **Quickstart só funciona no ambiente do autor:** clean-environment test.
- **Licença tardia bloqueia contribuição:** decisão do mantenedor antes do alpha.
- **Release precipitado:** Gate B, known issues e checklist obrigatório.

## Handoff

Entregar ao mantenedor release candidate com checklist, decisões ainda necessárias, artifacts, comandos de verificação, eval report, claim matrix e known issues. Não publicar tag/package ou alterar repositório remoto sem autorização explícita.

## Perfil sugerido do executor

P5 com excelência em technical writing, developer onboarding, open-source governance e release engineering. Reviews P2, P3 e P4 validam respectivamente exatidão técnica, eval claims e privacy/security.
