# C03 — Capability preflight ChatGPT/Gemini

- **Data:** 2026-08-29
- **Work item:** W03 (`READY-PREFLIGHT-ONLY`)
- **Escopo:** somente pesquisa documental e preflight read-only; C03 não foi
  implementado e CP-4 continua humano.
- **Base observada:** `a9e7b5deefeb0f43799e95a09a263bea5a5757d6`
- **Contexto Git:** worktree `/Users/marcellojunqueirafranco/.codex/worktrees/3535/UMCP`,
  `HEAD detached`; o handoff recebido esperava `codex/fix-pr-1`. Nenhuma
  correção de branch, conta, cliente, credencial ou serviço foi feita.
- **Único path escrito:** este arquivo.

## Decisão executiva

Não há, nas fontes oficiais consultadas, uma superfície única em que tanto
ChatGPT quanto Gemini Apps aceitem o mesmo servidor MCP com a mesma jornada de
write/capture → recall → update → forget → revoke. A proposta segura para C03
é:

1. **Primária:** ChatGPT web Developer Mode/custom MCP app, somente depois de
   C02 fechado e CP-4 autorizar conta, cliente, escopos e teste controlado.
2. **Alternativa suportada:** Gemini CLI como cliente MCP real, com servidor
   remoto HTTP ou SSE e OAuth; ele é uma superfície de desenvolvimento local,
   não prova integração com Gemini Apps consumer.
3. **Transferência de dados:** usar os tools explícitos de export/import do
   UMCP quando implementados. Não chamar o export nativo de ChatGPT ou Gemini
   de migração de conta: ambos produzem arquivos/referência, não reidratam
   automaticamente a conversa no outro produto.

O requisito de C03 permanece **blocked/not-run**. Esta matriz não é um claim de
compatibilidade, não configura clientes e não autoriza qualquer login.

## Matriz de capability atual

| Superfície | MCP/connectividade oficial observada | Conta/plano e limites relevantes | Import/export nativo | Classificação para C03 |
| --- | --- | --- | --- | --- |
| **ChatGPT web — custom MCP app** | Conecta a servidor MCP **remoto**; o admin/owner cria a app, fornece endpoint/metadata, escolhe auth e faz Scan Tools. Servidor local não conecta diretamente; OpenAI indica Secure MCP Tunnel para servidor privado. | Apps, Developer Mode e full MCP estão disponíveis no web para **Business e Enterprise/Edu**; full MCP com write/modify está em beta. Pro pode conectar MCP com read/fetch, mas full MCP não está disponível para Pro. Mobile não suporta MCP apps. Business restringe criação/publicação a admin/owner; Enterprise/Edu adiciona RBAC. | Export de conta elegível gera ZIP, normalmente por e-mail/SMS. Upload de `conversations.json` em outra conta pessoal deixa dados como referência em uma nova conversa; não recria chats/sidebar, memória, GPTs, instruções ou assinatura. Business/Enterprise não têm self-service export; Edu depende de permissão admin e não pode ter data residency. | **Candidate primary — Unverified.** O protocolo e o fluxo administrativo são suportados, mas a jornada UMCP real não foi executada e depende de CP-4/C02. |
| **Gemini Apps web — Connected Apps** | Google documenta apps conectados por MCP para **Gemini Spark**; custom connected apps estão, no momento, limitados a usuários com acesso ao Spark e dentro de Spark tasks. Disponibilidade varia por localização, idioma, dispositivo e app Gemini. | Requer acesso ao Spark para custom app; a documentação consultada não estabelece suporte geral a qualquer endpoint MCP para Gemini Apps fora dessa superfície. | Importa memória/histórico de outra plataforma via ZIP. Exige conta Google pessoal, idade ≥18 e acesso à plataforma de origem; não aceita conta de trabalho/escola/supervisionada. Limite do arquivo: 5 GB; até 5 ZIP/dia. Indisponível no EEE, Suíça e Reino Unido. | **Not suitable as primary C03 surface.** **Unverified** para UMCP; não prometer “Gemini Apps MCP” genérico. |
| **Gemini CLI — cliente MCP** | Suporta servidores locais `stdio` e remotos por HTTP/SSE; descobre tools e executa chamadas. OAuth 2.0 é documentado para servidores remotos. | Requer instalação do Gemini CLI e método de autenticação Gemini configurado; configurações podem ser user/workspace/system e políticas corporativas podem impor OAuth. Não é a mesma superfície ou UX de Gemini Apps. | A documentação oficial consultada cobre configuração MCP e OAuth, não uma migração nativa de chats equivalente ao import de Gemini Apps. | **Fallback supported candidate — Unverified.** É a alternativa mais concreta para validar o servidor MCP sem alegar suporte Gemini Apps. |

Fontes oficiais: [ChatGPT Apps](https://help.openai.com/en/articles/11487775-connectors-in),
[Developer Mode e full MCP no ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta),
[exportação ChatGPT](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpthistory-and-data),
[transferência de conversas entre contas ChatGPT](https://help.openai.com/en/articles/9106926-transferring-conversations-between-chatgpt-team-workspaces-and-personal-workspaces%25252525252525252525252525252525253F.pls),
[Connected Apps/Gemini Spark](https://support.google.com/gemini/answer/13695044?co=GENIE.Platform%3DDesktop),
[importação de dados para Gemini](https://support.google.com/gemini/answer/16868299?hl=en),
[Gemini CLI — servidores MCP](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md),
[Gemini CLI — setup MCP](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/tutorials/mcp-setup.md).

## Requisitos de conexão e OAuth

### ChatGPT custom MCP app

Owner/admin actions, still blocked by CP-4:

1. Confirmar workspace ChatGPT web Business ou Enterprise/Edu e habilitar
   Developer Mode conforme o papel. Em Enterprise/Edu, conceder RBAC apenas ao
   testador; em Business, o admin/owner executa a criação/publicação.
2. Disponibilizar endpoint MCP remoto HTTPS e metadata exigida pelo cliente;
   o endpoint e a configuração não podem ser inferidos a partir de `/health`.
3. Escolher auth. Para OAuth/OIDC, o provider deve publicar discovery em
   `.well-known/openid-configuration` ou `.well-known/oauth-authorization-server`,
   anunciar `offline_access` (ou equivalente) e emitir refresh token se a
   conexão precisar sobreviver à expiração do access token.
4. Registrar no provider o redirect URI que o fluxo do ChatGPT efetivamente
   solicitar e restringir por cliente/ambiente. A fonte oficial consultada não
   fornece um URI fixo universal; portanto não inventar um URI nem scopes.
5. Usar somente scopes mínimos definidos pelo contrato UMCP e pelo provider,
   confirmar consentimento e testar Scan Tools antes de qualquer chamada de
   escrita. A fonte oficial diz que cada usuário autentica a app antes do uso;
   write/modify pode exigir confirmação.

O comportamento de refresh sem `offline_access`, o fato de que apps publicados
usam snapshot congelado de tools e a limitação web-only devem entrar no teste e
na matriz de compatibilidade.

### Gemini CLI remote MCP

1. Configurar, em `settings.json`, `url`/`httpUrl` para HTTP ou SSE; a opção
   `stdio` é adequada apenas para servidor local.
2. Com OAuth discovery, o CLI pode detectar `401`, descobrir endpoints,
   registrar cliente dinamicamente quando suportado, abrir o browser e trocar o
   authorization code por tokens. Dynamic registration não deve ser assumido:
   se o provider não suportar, CP-4 precisa autorizar um client ID.
3. O redirect padrão é local, em formato
   `http://localhost:<random-port>/oauth/callback`; `redirectUri` pode ser
   configurado. O computador precisa abrir browser e receber esse redirect;
   headless, SSH sem X11 e container sem browser são bloqueios conhecidos.
4. Scopes e audiences devem ser os mínimos do servidor. `clientSecret` é
   opcional para public clients, mas não deve ser criado ou armazenado nesta
   preflight. Refresh só existe se o provider emitir refresh token.
5. Validar com `/mcp auth`, `/mcp list`/`/mcp reload` e chamadas sintéticas
   apenas após autorização. Nenhum desses comandos foi executado aqui.

## Fluxo de import/export e limites

### Fluxo MCP proposto (não executado)

```text
ChatGPT ou Gemini CLI
  → UMCP capture/write (consent explícito, provenance e tenant)
  → UMCP export owner-scoped (artefato versionado/checksummed)
  → download/import explícito no outro cliente
  → UMCP ingest/recall com provenance da origem e do import
```

Esse fluxo é a alternativa de produto que preserva a semântica UMCP. Ele exige
um contrato de export/import e testes C03/C04; a existência de um ZIP nativo de
um provedor não prova que o outro provedor aceite o formato.

### Transferência nativa documentada

- **ChatGPT:** exporta um ZIP de dados elegíveis. A transferência entre contas
  pessoais consiste em carregar `conversations.json` (ou arquivos numerados)
  em nova conversa; é apenas referência, não restauração de chats separados.
- **Gemini Apps:** aceita ZIP de histórico/memória de outra plataforma e cria
  nova conversa para integrar o conteúdo à memória. Limites e elegibilidade
  estão na tabela; o processo não é uma conexão MCP nem uma reidratação do
  estado UMCP.
- **ChatGPT → Gemini:** a própria ajuda do Gemini documenta ChatGPT como
  origem de export e upload ZIP. Isso é um caminho suportado para referência
  de histórico, mas não cobre capture/recall/update/forget/revoke do UMCP.
- **Gemini → ChatGPT:** a documentação consultada não descreve um importador
  equivalente de ZIP no ChatGPT; o caminho seguro é exportação UMCP explícita,
  ou upload manual de conteúdo compatível numa conversa pessoal, sem chamar
  isso de migração.

## Checkpoint CP-4 e ações do owner

CP-4 precisa decidir, antes de qualquer implementação ou login:

- qual conta/workspace e plano ChatGPT serão usados;
- se a primeira superfície será ChatGPT web Developer Mode;
- se o fallback aceito é Gemini CLI, Gemini Spark ou um cliente documentado
  alternativo (o roadmap cita Claude API/cliente quando o preflight impedir o
  fluxo completo);
- OAuth issuer, redirect URI, client type, scopes, audience/resource,
  `offline_access`, refresh-token policy e retenção de tokens;
- região/elegibilidade do Gemini Apps e se os dados sintéticos podem ser
  carregados;
- critérios de abortar, revogar e apagar o tenant de teste.

Nenhuma dessas decisões foi inferida. Não foram solicitados tokens, e-mails,
credenciais, clientes OAuth, contas ou convites.

## Acceptance e estado atual

| Item W03 | Resultado | Evidência |
| --- | --- | --- |
| Capability matrix atual | **Pass — documental** | Fontes oficiais acima, consultadas em 2026-08-29 |
| Conta/client/redirect/scopes | **Pass — requisitos identificados; não configurado** | Seções de requisitos e CP-4 |
| Fluxo import/export | **Pass — limites e não-equivalências registradas** | Seção de transferência |
| Alternativa suportada | **Pass — Gemini CLI identificado** | Matriz e fontes Gemini CLI |
| MCP ChatGPT real | **Not-run / blocked by C02 + CP-4** | Sem login, app ou chamada |
| MCP Gemini real | **Not-run / blocked by CP-4** | Sem login, configuração ou chamada |
| C03 gate | **Open; não promover** | Dependência C02 e autorização externa ausentes |

## Handoff

- **Arquivos alterados:** somente este handoff.
- **Testes/configuração externa:** nenhum; tarefa read-only de capability
  preflight.
- **Proveniência:** base SHA e estado Git registrados no topo; fontes externas
  são links oficiais atuais, não evidência de execução UMCP.
- **Próximo passo:** fechar C01/C02 com SHA limpo; depois CP-4 decide a conta,
  plano, client/OAuth e superfície. Só então C03 pode implementar a recipe e
  executar report checksummed.
- **Limitação:** a worktree foi recebida com `HEAD detached`; o handoff foi
  commitado localmente nesse contexto, sem criar branch, fazer push ou alterar
  outra worktree. O manager deve reconciliar o commit conforme a regra de W03.
