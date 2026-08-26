# H07 — preflight da auditoria pronto

`scripts/preflight-h07-audit.sh` valida somente argumentos explícitos fornecidos
por Antigravity após o deploy. Ele não faz DNS, rede, GCP, autenticação, deploy
ou leitura de secrets.

O preflight exige URL HTTPS exata terminada em `/mcp`, projeto e região iguais
às respectivas allowlists, service/revision, digest de imagem, source SHA,
referências não-secretas para identidade e conexão sintéticas autorizadas e
`--mode read-only`. Recusa endpoint HTTP ou path diferente, campos ausentes,
escopo divergente, provenance malformado e entradas contendo padrões de
segredo/token. Valores não devem ser substituídos por secrets reais.

Exemplo redigido:

```sh
scripts/preflight-h07-audit.sh \
  --endpoint 'https://REDACTED_HOST/mcp' \
  --project 'REDACTED_PROJECT' --allowed-project 'REDACTED_PROJECT' \
  --region 'REDACTED_REGION' --allowed-region 'REDACTED_REGION' \
  --service 'mcp' --revision 'REDACTED_REVISION' \
  --image-digest 'sha256:REDACTED_HEX' \
  --source-sha '0123456789abcdef0123456789abcdef01234567' \
  --identity-ref 'identity-synthetic' --connection-ref 'connection-synthetic' \
  --mode read-only
```

Validação offline: `scripts/test-preflight-h07-audit.sh`. O teste apenas chama
o script localmente e cobre HTTPS/path, projeto, modo e token-like input.
