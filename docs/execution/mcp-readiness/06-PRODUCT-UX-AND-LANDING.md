---
title: 06 — Entregar UX do produto e Landing pública
status: landing-authorized-product-controls-after-05
order: 6
owner: Luna high
depends_on: 05-REAL-CLIENT-CONNECTORS.md for authenticated controls
unlocks: 07-TRUSTED-RECALL.md
---

# 06 — Entregar UX do produto e Landing pública

## Resultado esperado

A Landing pública explica o produto em menos de 30 segundos e não promete
capacidades ainda não comprovadas. Depois dos contratos anteriores, a
experiência autenticada oferece Connections, Memory Inbox, Memories, Concepts,
Mental Notes, Activity, export, revoke e forget.

## Fatiamento obrigatório

### Fatia A — autorizada imediatamente

Publicar a Landing institucional já desenhada no projeto, mantendo:

- “Your memory should outlive the model”;
- Remember → Retrieve → Correct → Forget;
- estética editorial papel/tinta/laranja;
- compatibility matrix conservadora;
- claims explícitas de Alpha/preview;
- login e dashboard como indisponíveis enquanto o backend não estiver pronto;
- nenhum formulário que finja envio de e-mail;
- nenhum link quebrado para arquivos internos do repositório.

### Fatia B — depois dos documentos 03–05

Conectar auth, consentimento, vault e controles ao Admin API server-side. O
browser não recebe token, owner, tenant, regra de autorização ou acesso direto
ao banco.

## Rotas de produto

- `/`: Landing;
- `/login`: identidade e estados de magic link;
- `/dashboard`: overview audit-safe;
- `/memories` e detalhe;
- `/memory-inbox`;
- `/concepts` e detalhe;
- `/notes`;
- `/activity` e “why recalled?”;
- `/connections`;
- `/settings/security`;
- `/docs`, `/status`, privacy e security.

## Tarefas executáveis

1. Congelar claim matrix e copy da Landing.
2. Corrigir links para destinos públicos válidos ou removê-los.
3. Validar responsividade, teclado, contraste e reduced motion.
4. Publicar Landing como preview honesto.
5. Congelar schemas do Admin API.
6. Integrar sessão server-side, nunca auth client-side.
7. Implementar Inbox confirm/edit/discard/never-category.
8. Implementar Memories com provenance/version/update/forget.
9. Implementar Connections/scopes/revoke.
10. Implementar Concepts, Mental Notes e Activity acessíveis.
11. Implementar export/delete com reauth e idempotency.
12. Executar browser E2E desktop/mobile e claim/link checker.

## Acceptance test da Landing

- hero, tese e lifecycle visíveis;
- compatibility sem claim universal;
- segurança declara que v1 não é E2EE/zero knowledge;
- CTA não promete conta funcional antes do backend;
- nenhum link aponta para path local inexistente no deploy;
- página funciona em mobile, teclado e reduced motion;
- build e deploy terminam com URL acessível.

## Acceptance test do produto autenticado

- usuário entra por sessão server-side;
- confirma uma candidate na Inbox;
- recall real muda no segundo cliente;
- inspeciona provenance e conceitos de suporte;
- corrige, pin/unpin, exporta, revoga e esquece;
- forget invalida derivados;
- tenant B recebe zero;
- falha do backend produz estado de erro, não dados inventados.

## Comandos de aceitação

```bash
npm --prefix apps/web run check
npm --prefix apps/web run test
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e
python scripts/check-claims-and-links --strict
python scripts/demo-m04-atlas --synthetic
```

## Gate de saída

- Landing publicada com claims honestas;
- web build/test/check atuais;
- auth e destructive actions server-side;
- Inbox afeta o recall real;
- teclado/mobile/WCAG AA;
- nenhuma visualização fabrica dado;
- visual graph, se houver, possui alternativa textual.

## Rollback

- manter Landing estática e retirar CTAs inoperantes;
- desligar rotas autenticadas por feature flag;
- voltar para estados `unavailable` sem expor mocks como reais;
- rebaixar claims/conectores imediatamente;
- reimplantar a última versão validada.

## Prompt de execução

```text
Execute docs/execution/mcp-readiness/06-PRODUCT-UX-AND-LANDING.md. A Fatia A
da Landing está autorizada agora e deve ser publicada com claims honestas.
Não finja login, e-mail, backend ou compatibilidade. A Fatia B só começa após
os contratos 03–05. Preserve a estética existente, valide links, build,
acessibilidade e mobile. Feche cada fatia com demo, handoff e rollback.
```
