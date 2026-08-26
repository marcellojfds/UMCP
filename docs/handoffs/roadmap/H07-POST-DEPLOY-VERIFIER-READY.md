# H07 — verificador pós-deploy pronto

Este handoff adiciona `scripts/verify-mcp-post-deploy.sh`, um verificador
somente de leitura para uso futuro por Antigravity. Ele não foi executado
contra serviço algum nesta tarefa.

## Chamada obrigatória

Após o deploy, Antigravity deve fornecer explicitamente o endpoint, a allowlist
de host, o digest imutável esperado e o SHA de origem esperado:

```sh
scripts/verify-mcp-post-deploy.sh \
  --endpoint 'https://mcp-staging.example/mcp' \
  --allowed-host 'mcp-staging.example' \
  --expected-image-digest 'sha256:REDACTED_HEX_DIGEST' \
  --expected-source-sha '0123456789abcdef0123456789abcdef01234567'
```

O host deve ser explicitamente allowlisted e a resposta deve expor exatamente
os headers `X-UMCP-Image-Digest` e `X-UMCP-Image-Source-SHA`, com os valores
esperados. A ferramenta usa `curl` já instalado, exige TLS e `/mcp` exato,
desativa redirects (`--max-redirs 0`) e retorna código diferente de zero em
qualquer falha. Não passe segredos ou dados reais na linha de comando.

## Uso pela auditoria H07

Registrar a chamada redigida, timestamp, commit verificado, host allowlisted,
status de saída e a linha `PASS` (ou a mensagem `FAIL`) no pacote de evidências.
Um `PASS` prova somente HTTPS sem redirect observado, path exato e igualdade
dos dois valores de provenance fornecidos; não prova disponibilidade contínua,
autorização, segurança do conteúdo, validade do attestation ou que o header não
foi forjado pelo serviço. A auditoria deve conferir digest/SHA contra a fonte
de verdade independente do pipeline e tratar ausência de evidência como falha.

## Validação local

Sem rede, executar:

```sh
scripts/test-verify-mcp-post-deploy.sh
```

O teste injeta um `curl` sintético que apenas grava headers locais e também
confirma a recusa de HTTP. Ele não contata rede, GCP, autenticação ou secrets.

Limitações honestas: o script não faz deploy, não resolve identidade da
imagem, não valida certificados além do comportamento do `curl`, não detecta
mudanças posteriores à consulta e não substitui auditoria de logs ou
attestation.
