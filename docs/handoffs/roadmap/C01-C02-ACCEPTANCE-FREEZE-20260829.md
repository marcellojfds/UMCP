# W02 — congelamento de aceitação C01/C02 — 2026-08-29

## Estado e escopo congelados

- **Lane:** W02 / Terra 1; **base SHA:**
  `a9e7b5deefeb0f43799e95a09a263bea5a5757d6`.
- **Único path alterado por W02:** este handoff. W02 não altera runtime,
  scripts, reports ou o checklist.
- **Dependência satisfeita:** H07 é `M02 STAGING READY`, não production-ready.
- **Estado de C01/C02:** aberto. Os artefatos de 2026-08-29 são evidência
  `historical`: registram C01 14/14, C02 15/15 e contenção 0/0/0, mas seu
  `audit_source_sha` aponta para uma árvore ainda não commitada. Eles não
  podem fechar o gate nem ser reutilizados como evidência `current`.

Este documento é o contrato de aceitação para W01 antes da nova rodada. Uma
implementação que não conseguir produzir cada evidência abaixo permanece
aberta; não é permitido enfraquecer este contrato durante a execução para
acomodar o resultado.

## 1. Proveniência obrigatória

Cada JSON C01, C02 e Containment, bem como o respectivo Markdown, deve levar
os mesmos valores para os seguintes campos:

| Campo | Regra congelada |
| --- | --- |
| `report_id` e `timestamp_utc` | Identificam a mesma rodada e instante UTC rastreável; os três artefatos referenciam o mesmo ciclo de auditoria. |
| `base_url` | Endpoint HTTPS de staging realmente exercitado; a rota MCP é exatamente `/mcp`. |
| `audit_source_sha` | SHA completo de commit Git (40 hex) do código que entrou na imagem de auditoria. Deve ser igual ao SHA resolvido no checkout limpo usado para o build e ao valor passado ao job; não pode ser `unknown`, abreviado, tag ou SHA de árvore com diff. |
| `audit_image_digest` | Digest imutável completo `sha256:<64 hex>` da imagem que executou `python -m omp.sdk.audit_entrypoint`. A imagem deve ter sido construída a partir do checkout limpo do `audit_source_sha`; referência por tag, inclusive `latest`, não é prova suficiente. |
| `server_source_sha` | SHA completo separado que identifica a fonte do servidor de staging. Não deve ser inferido a partir do SHA de auditoria. |
| `server_digest` | Digest imutável completo da imagem do servidor que atendia a rodada. |
| `server_revision` | Revisão ativa que serviu a rodada; deve corresponder ao `server_digest` observado. |
| `sdk_version`, `agent_version`, `protocol_version` e `scopes` | Presentes quando aplicáveis e coerentes entre C01/C02; scopes mínimos exatos: `memory:read`, `memory:write`, `memory:delete`. |

Além dos campos do report, a evidência da execução deve preservar, sem
segredos, o comando de preflight que confirma: checkout no commit informado,
`git status --porcelain` vazio antes do build, resolução do digest da imagem e
o módulo/entrypoint executado. A fonte de auditoria, o digest da sua imagem e
o SHA/digest/revision do servidor são quatro identidades distintas. Nenhuma
delas pode ser substituída pela outra.

## 2. Probes positivos — C01 (14/14)

O report C01 só pode dizer `Supported` e `PASS` quando cada identificador
abaixo possui resultado da rodada, em serviço staging real e com payloads
sintéticos. Cada linha inclui asserções que não podem ser omitidas.

| ID | Probe positivo e asserção mínima |
| --- | --- |
| `protected_resource_discovery` | Discovery do protected resource responde 200 e anuncia recurso HTTPS `/mcp`. |
| `authorization_server_discovery` | Discovery do authorization server responde 200 e retorna endpoints HTTPS coerentes com o resource anunciado. |
| `oauth_pkce_s256` | Fluxo authorization-code com PKCE `S256` válido associa verifier/challenge e chega ao token endpoint. |
| `token_exchange` | Troca de código válida responde 200, com Bearer e somente os scopes autorizados; o token em si nunca é reportado. |
| `mcp_initialize` | Sessão autenticada inicializa o endpoint exato `/mcp` com sucesso. |
| `mcp_tools_list` | A sessão inicializada lista as ferramentas necessárias à jornada de memória. |
| `memory_write_synthetic` | Grava um único dado sintético, produz identificador sintético e não usa dado de usuário. |
| `memory_search_synthetic` | A busca autorizada recupera o registro sintético da própria tenant. |
| `memory_update_synthetic` | Atualiza o mesmo registro e demonstra transição de versão observável. |
| `memory_forget_synthetic` | Executa forget no registro da rodada e recebe confirmação de lifecycle. |
| `token_refresh_rotation` | Refresh válido emite a nova credencial de forma rotacionada. |
| `token_revocation` | Revogação válida é aceita pelo servidor e invalida a credencial-alvo. |
| `forged_authority_rejection` | A tentativa de fornecer `owner_id` ou `tenant_id` forjado é rejeitada tanto pelo cliente quanto pelo servidor, sem mutação. |
| `zero_leakage_redaction` | A coleta de evidência permanece redigida nos sinks definidos na seção 6. |

O resumo deve ser exatamente `supported_count=14`,
`total_capabilities=14`, `unverified_count=0`; qualquer capacidade adicional
permanece `Experimental` ou `Unverified` e não é promovida por esta rodada.

## 3. Jornada positiva — C02 (15/15)

O agente Python controlado deve executar a jornada inteira no mesmo ciclo e
reportar exatamente os 15 IDs abaixo. `PASS` exige a asserção indicada, não
apenas uma resposta HTTP bem-sucedida.

| ID | Asserção mínima |
| --- | --- |
| `1_discovery` | Descobre protected resource e authorization server HTTPS vinculados ao `/mcp` exercitado. |
| `2_oauth_pkce_login` | PKCE S256 autorizado obtém Bearer/refresh efêmeros com os três scopes congelados. |
| `3_mcp_initialize` | Inicializa uma sessão MCP autenticada no `/mcp` exato. |
| `4_mcp_tools_list` | Lista as ferramentas exigidas para write, recall, update e forget. |
| `5_synthetic_write` | Cria uma memória exclusivamente sintética na tenant A. |
| `6_recall_search` | Encontra a memória A pela busca autorizada da tenant A. |
| `7_update` | Atualiza a memória A e confirma avanço de versão. |
| `8_forget` | Aplica forget à memória A e confirma seu estado apagado. |
| `9_tombstone_non_resurrection` | Nova leitura/busca não ressuscita a memória esquecida. |
| `10_provenance_preservation` | A proveniência sintética esperada permanece vinculada ao registro durante a jornada, sem vazar payload sensível. |
| `11_refresh_rotation` | Refresh válido gira a credencial e invalida o refresh anterior. |
| `12_token_revocation` | Revoga a credencial-alvo no servidor. |
| `13_unauthorized_after_revoke` | Chamada MCP com a credencial revogada recebe 401 e não produz mutação. |
| `14_forged_authority_rejection` | Forjar `owner_id` ou `tenant_id` falha client-side e server-side, sem mutação. |
| `15_tenant_isolation` | Token da tenant B não lê, atualiza, esquece nem obtém conteúdo ou metadados da memória A; a evidência demonstra leakage zero. |

O resumo deve ser exatamente `passed_steps=15`, `failed_steps=0` e
`total_steps=15`. IDs fora da lista não compensam falha, ausência ou
`Unverified` de qualquer um dos 15.

## 4. Probes negativos obrigatórios

Os negativos abaixo devem ser executados e ficar associados ao ID C01/C02
correspondente; não são um adendo documental nem podem ser satisfeitos por
resultado histórico H07.

| Negativo | Resultado fail-closed exigido | IDs que o registram |
| --- | --- | --- |
| Sem credencial Bearer em `/mcp` | 401; nenhuma ferramenta, service ou mutação é invocada. | `mcp_initialize`, `3_mcp_initialize` |
| Verifier PKCE incorreto, código expirado/reutilizado ou redirect não vinculado | Rejeição OAuth segura (`400`/`invalid_grant` ou equivalente), sem token emitido. | `oauth_pkce_s256`, `token_exchange`, `2_oauth_pkce_login` |
| Refresh pré-rotação | Rejeitado após a rotação; não emite novo par. | `token_refresh_rotation`, `11_refresh_rotation` |
| Access token revogado | MCP retorna 401 após a revogação, sem mutação. | `token_revocation`, `13_unauthorized_after_revoke` |
| `owner_id`/`tenant_id` forjado | Rejeição no SDK e no servidor; nenhum dado ou mutação atravessa a borda. | `forged_authority_rejection`, `14_forged_authority_rejection` |
| Token da tenant B contra dado da tenant A | Ausência de conteúdo e metadados de A; tentativas de leitura e mutação falham. | `15_tenant_isolation` |
| Após forget | O tombstone bloqueia recuperação/ressurreição do registro A. | `9_tombstone_non_resurrection` |

Respostas negativas não podem carregar token, código, cookie, e-mail, payload
de memória, query sensível nem detalhes internos de banco. Uma resposta
diferente da rejeição segura esperada é `FAIL`, mesmo se a jornada positiva
tiver passado.

## 5. Checksums e integridade física

Para cada um dos três JSONs (C01, C02 e Containment), o algoritmo canônico é
fixado como:

```text
payload_sem_checksum = remover somente a chave de primeiro nível "checksum"
bytes = UTF-8(json.dumps(payload_sem_checksum, sort_keys=True,
                         separators=(",", ":")))
checksum = "sha256:" + SHA-256(bytes).hexdigest()
```

- O JSON deve conter o `checksum` calculado acima; nenhum outro campo é
  excluído do payload canônico.
- O checksum físico é `sha256:` + SHA-256 dos bytes exatos do arquivo JSON em
  disco, incluindo a serialização e newline finais que existirem.
- Cada Markdown deve apontar para o JSON correspondente e conter literalmente
  os dois valores calculados: checksum canônico e checksum físico.
- Antes de aceitar, o verificador versionado deve executar com êxito em um
  checkout limpo usando somente a biblioteca padrão, sem importar `omp` e sem
  instalar dependências do pacote. Ele deve verificar os três pares JSON/MD,
  o algoritmo canônico, hashes físicos e marcadores Markdown.
- Falta de arquivo/campo/marcador, JSON inválido, digest malformado ou qualquer
  divergência faz o verificador retornar não zero e mantém C01/C02 abertos.

## 6. Contenção e redaction

Depois que o `finally` da auditoria concluir e antes de os reports serem
aceitos, a mesma rodada deve medir explicitamente:

```text
active_tokens=0
active_codes=0
active_test_tenants=0
```

Os três campos devem existir, ser inteiros e ser zero. Campo ausente,
não-numérico, não consultado ou contagem diferente de zero é falha; um mapa de
contagens vazio não equivale a contenção aprovada. A consulta deve cobrir os
tokens, códigos e tenants de teste criados pelo runner, e a jornada deve usar
somente tenants, IDs, textos e atores sintéticos efêmeros.

Não pode aparecer valor de token, refresh token, authorization code, PKCE
verifier, state, cookie, cabeçalho `Authorization`, e-mail, URL de conexão,
valor de segredo, chave, payload de memória ou dado de usuário em stdout,
stderr, argumentos de processo, logs do job, JSONs, Markdown ou metadados de
erro. Podem ser reportados somente nomes de campos, estados, contagens,
identificadores sintéticos não sensíveis e hashes/digests permitidos. Antes da
aceitação, W01 deve escanear todos esses sinks da rodada; qualquer ocorrência
ou impossibilidade de inspecionar um sink torna `zero_leakage_redaction` e a
rodada inteiros `FAIL`.

## 7. Decisão fail-closed

Somente depois de uma única rodada com proveniência coerente, C01 14/14, C02
15/15, todos os negativos acima, checksums válidos, contenção 0/0/0 e redaction
sem achados, W01 pode propor marcar C01/C02 como `current` e atualizar o
checklist. A proposta ainda requer a reconciliação do manager.

Qualquer uma das condições abaixo resulta em `NO-GO / gate open`, sem marcar
checklist e sem promover claims:

- build sem checkout limpo, `audit_source_sha` divergente, abreviado ou não
  comprovado pelo digest da imagem;
- imagem/revisão identificada por tag mutável, SHA/digest/revision ausente ou
  discrepante entre C01, C02 e Containment;
- total diferente de 14/14 ou 15/15, resultado `FAIL`, `Unverified`,
  `Experimental`, omitido ou não executado;
- positivo sem o negativo correspondente, status HTTP/efeito diferente do
  especificado ou qualquer mutação em rejeição;
- checksum, hash físico, marcador Markdown ou verificador stdlib-only falho;
- contenção diferente de 0/0/0, limpeza não demonstrada, dado não sintético ou
  redaction não demonstrada;
- indisponibilidade de staging, credencial, permissão ou outro checkpoint.

Em `NO-GO`, os artefatos podem registrar a falha de forma redigida e
classificada como `current`/`environment-blocked` conforme a execução, mas não
podem ser usados para declarar C01/C02 entregues. Não autoriza C03, produção,
usuários externos, push, PR, tag ou release.

## Handoff para W01 e reconciliação

W01 deve manter este contrato intacto, executar somente a nova rodada limpa e
entregar SHA local, árvore limpa, comandos atuais, reports regenerados e
evidência de cada regra acima. A decisão de C01/C02 continua sendo do manager
após reconciliar SHA, worktree, proveniência, reports, checksums e contenção.
