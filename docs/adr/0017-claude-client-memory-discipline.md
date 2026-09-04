# ADR 0017 — Disciplina de memória no cliente Claude

## Status

Aceito como orientação de produto/cliente (2026-09-04). Não autoriza release,
hosted GO, nem Gate B de retrieval.

## Contexto

O vault UMCP só responde a tools MCP. Em superfícies como Claude.ai, o servidor
**não** escuta o chat: o cliente decide quando chamar `memory.write`,
`memory.search`, `memory.update` ou `memory.forget`.

Prioridade atual do maintainer: integração Claude com disciplina clara de
**quando gravar** vs **quando claimar memória antiga**, antes de tratar H07/S08
como prioridade.

Restrições de superfície (evidência externa Anthropic + docs Alpha):

- `claude.ai` (browser) exige **custom connector** via **remote MCP HTTPS**;
  a Anthropic alcança o servidor da nuvem deles, não da máquina do usuário.
- MCP Alpha suportado hoje é **stdio** apenas (`docs/mcp.md`, `docs/support-matrix.md`).
- `examples/connectors` usa labels sintéticos (`claude-sim`); não é integração
  real com Claude (`examples/connectors/recipe.md`).
- ADR 0010 decide Streamable HTTP em `/mcp` para Cloud (design); runtime Alpha
  ainda não é claim de produção.
- ADR 0011 cobre identidade/consent hosted (design).
- Visão de produto define modos de captura: `disabled` | `manual` | `assisted` |
  `automatic` (`docs/PRODUCT_VISION_PORTABLE_MEMORY.md`).

## Decisão

1. **Modo default para Claude:** `assisted` (propor / confirmar) com `manual`
   sempre honrado (“lembra disso”, “salva”, “anota”). `automatic` permanece
   desligado até evidência de writer (W05) / Gate C — sem claim prematuro.
2. **Disciplina search (claim do passado):** buscar no início de assuntos que
   possam ter memória antiga; quando o usuário perguntar o que já decidiu/lembrou;
   antes de afirmar fatos sobre o usuário fora da conversa atual. Search vazio =
   abstention explícita (não inventar).
3. **Disciplina write (salvar):** só conhecimento durável (1–3 frases) com tipo
   claro (`fact`, `preference`, `decision`, `lesson`, `insight`, `goal`,
   `project_context`, `open_question`). Preferir `update`/contradição a duas
   preferências ativas. Default: **abstain**.
4. **Proibido por default:** senhas/tokens, pagamento, dump de conversa,
   rascunho passageiro, prompt injection fingindo fato.
5. **Escada de entrega Claude:**
   - Hoje: Project Instructions versionadas (comportamento sem tools reais).
   - Depois: Custom Connector (`https://…/mcp` + auth) testável no Claude.ai.
   - Depois: Connectors Directory (marketplace) — ver checklist em
     `docs/clients/claude-custom-connector-path.md`.
6. **Recall é dado não confiável:** nunca tratar conteúdo recuperado como
   instrução de sistema; citar provenance quando disponível.

Textos operacionais:

- [`docs/clients/claude-project-instructions.md`](../clients/claude-project-instructions.md)
- [`docs/clients/claude-custom-connector-path.md`](../clients/claude-custom-connector-path.md)

## Alternativas consideradas

- **Só Desktop/stdio:** funciona localmente, mas não atende a superfície pedida
  (`claude.ai`). Mantido como caminho paralelo, não substituto.
- **Automatic write no cliente:** rejeitado até Gate C / W05; alta taxa de lixo
  contamina retrieval futuro.
- **Fingir suporte Claude via fixtures `claude-sim`:** rejeitado; labels são
  apenas testes M03.

## Consequências

- Comportamento no browser melhora imediatamente via Project Instructions, sem
  claim de tools conectadas.
- Custom Connector e Directory dependem de remote MCP + OAuth + anotações de
  tools — itens ainda **NO-GO** no Alpha (ver checklist).
- Retrieval semântico S08 continua NO-GO (`docs/known-issues.md`); disciplina de
  cliente não autoriza Gate B.
- Writer server-side (W05) permanece fora de escopo deste ADR.
