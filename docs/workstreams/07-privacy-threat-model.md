# W07 — Privacy e threat model

## Objetivo

Tornar as garantias e limitações de privacidade verificáveis, orientar decisões caras de reverter e impedir claims enganosos. A frente entrega requisitos mínimos desde o Gate A e pesquisa uma arquitetura client-side para eventual hosting no MVP 4.

## Contexto mínimo

Memórias podem conter decisões, relações, preferências, projetos e ideias sensíveis. A ambição é que o operador não precise ler seu conteúdo, mas embeddings também podem vazar informação. No MVP local não haverá promessa de E2EE; transparência é obrigatória.

Leia W00, W01–W06, W09, W11 e W12.

## Escopo

### Dentro

- data inventory e classification;
- threat actors, assets, trust boundaries e abuse cases;
- requisitos de minimização, retention, deletion, secrets e tenant isolation;
- política de uso de provedores de LLM/embedding;
- requisitos de logging/telemetry/redaction;
- análise de vazamento de embeddings e metadados;
- desenho e protótipo de client-side encryption/key management;
- security/privacy tests e linguagem de claims.

### Fora

- implementação geral do banco, owned por W03;
- cliente criptográfico de produção, owned por W09 após ADR;
- operação de backups, owned por W11;
- compliance certification, pentest formal ou promessa regulatória no MVP;
- criptografia pesquisável própria sem revisão especializada;
- auth completo de serviço hospedado, que será uma frente futura derivada deste threat model.

## Assets e adversários mínimos

Assets:

- conteúdo e histórico de versões;
- provenance/evidence;
- embeddings e relações;
- owner/space identifiers e padrões de acesso;
- chaves/tokens de provedores;
- backups, logs, traces, eval artifacts e exports.

Adversários/cenários:

- operador de hosting curioso ou comprometido;
- atacante com dump do banco ou backup;
- tenant tentando acessar outro tenant;
- provedor de modelo/embedding observando payloads;
- conteúdo malicioso tentando prompt injection no writer/reranker;
- logs/traces exportados a terceiro;
- dispositivo cliente ou chave do usuário comprometida;
- inferência de conteúdo a partir de embedding/metadados.

## Decisões já tomadas

- O alpha local/self-hosted declara conteúdo e embeddings legíveis pelo operador da instância.
- Nenhum claim de E2EE ou zero knowledge antes do Gate F.
- Owner isolation, export, forget, minimal plaintext metadata e no-content logging são requisitos do MVP 0.
- Secrets nunca entram em código, fixture, log ou error payload.
- Telemetria de conteúdo é opt-in e desabilitada por default.
- Forget remove conteúdo online imediatamente; limitações de backup são documentadas e testadas por política de retenção.
- Chaves client-side, quando existirem, não ficam disponíveis ao servidor em plaintext.
- Embeddings são classificados como dados sensíveis, mesmo quando o conteúdo estiver cifrado.

## Decisões abertas

- modelo exato de autenticação/tenant identity para hosted;
- provider e localidade de embedding: cliente, servidor ou provedor escolhido pelo usuário;
- envelope encryption, algoritmo e biblioteca auditada;
- recovery/rotation de chaves e experiência multi-device;
- metadados que precisam permanecer pesquisáveis em plaintext;
- busca sobre conteúdo cifrado e trade-off de leakage;
- retention de tombstones, logs e backups;
- threat model para sharing, se essa feature for priorizada futuramente.

Nenhuma dessas decisões deve ser resolvida inventando criptografia. O executor compara alternativas maduras, prototipa e pede review.

## Dependências

- W02: forget, provenance e owner model.
- W03/W06: dados persistidos e vetores.
- W09: capacidades do cliente e export.
- W11: logs, backups, deploy e incident response.

W01–W06 recebem requisitos mínimos desta frente no Gate A. W12 depende da matriz de claims.

## Entregáveis

### Gate A/MVP 0

- `docs/privacy.md` com data inventory e garantias atuais;
- threat model versionado, preferencialmente com STRIDE/LINDDUN ou método equivalente;
- data flow diagram e trust boundaries;
- retention/deletion matrix;
- provider data-handling policy;
- redaction e safe-error requirements;
- privacy/security test checklist;
- claim matrix: “garantido”, “mitigado”, “não protegido”, “futuro”.

### MVP 4

- ADR comparando ao menos duas arquiteturas viáveis;
- protótipo de client-side encryption e key rotation/recovery;
- experimento de embedding location/leakage e impacto em retrieval;
- atualização do threat model e protocolo de migração;
- revisão independente antes do Gate F.

## Etapas

1. Inventariar dados em repouso, trânsito, logs, providers, exports e backups.
2. Desenhar data flows local e hosted futuro.
3. Priorizar ameaças por impacto/probabilidade e definir controles MVP.
4. Converter controles em acceptance tests para W02/W03/W04/W11.
5. Revisar docs/claims do alpha.
6. Após Gate B, prototipar alternativas client-side com dados sintéticos.
7. Medir leakage, latência, operabilidade e efeito em retrieval antes do ADR final.

## Critérios de aceite verificáveis

- Cada asset aparece em um data flow e em uma retention rule.
- Testes cross-owner cobrem read, search, update, forget, relations e error responses.
- Busca automatizada em logs/traces de teste não encontra conteúdo-canário nem secrets.
- Forget online e export/delete são demonstrados no cenário E2E.
- Documentação afirma explicitamente que embeddings podem vazar informação.
- Provider policy esclarece quais dados saem da instância e sob qual configuração.
- Gate F inclui perda/rotação de chave, restore de backup, dispositivo novo e revogação.
- Toda claim pública mapeia para controle e teste; o restante está marcado como limitação.

## Testes e revisões

- canary secrets/content em logs, traces, exceptions e CI artifacts;
- cross-owner/ID enumeration;
- backup/restore/delete retention test;
- ciphertext tampering e wrong-key behavior no protótipo;
- key rotation e migration interruption;
- prompt injection em conteúdo enviado a writer/reranker;
- análise experimental de nearest-neighbor/membership inference em embeddings sintéticos;
- revisão por alguém que não implementou o protótipo.

## Riscos e mitigação

- **Privacy washing:** claim matrix ligada a testes e revisão W12.
- **Embedding tratado como anônimo:** classificação sensível e documentação explícita.
- **Chave perdida destrói memória:** recovery UX definida antes de produção, com trade-offs claros.
- **Servidor ainda vê metadata:** minimização e data flow, sem promessa absoluta.
- **Backups violam forget imediato:** janela de retenção publicada e restore com deletion ledger não sensível.
- **Crypto custom:** usar primitives/bibliotecas estabelecidas e revisão independente.

## Handoff

No Gate A, entregar requisitos concretos e claim matrix a todas as frentes. No MVP 4, entregar ADR e protocolo implementável a W03/W06/W09/W11. W12 só publica afirmações listadas como verificadas.

## Perfil sugerido do executor

P4, com experiência em threat modeling, applied cryptography, multi-tenant isolation e privacy engineering. Revisão independente P4 é obrigatória antes do Gate F.
