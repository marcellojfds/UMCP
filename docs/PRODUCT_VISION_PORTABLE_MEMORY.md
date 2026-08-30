---
title: UMCP Portable Memory — Product Vision
status: vision-reference
confidence: confirmed
implementation_status: partially-implemented
applies_to_branch: terra-alpha-recovery
updated: 2026-08-21
workstreams:
  - product
  - memory-model
  - mcp
  - multitenancy
  - web
  - privacy
---

> **Vision, not current status.** Verified behavior and active priorities live
> in [`CURRENT_STATE.md`](CURRENT_STATE.md) and [`roadmap.md`](roadmap.md).

# UMCP Portable Memory — visão de produto de longo prazo

## 1. North star

O UMCP é a camada de memória pessoal que acompanha o usuário entre modelos,
chats e agentes.

> **Your memory should outlive the model.**

Uma pessoa pode registrar um aprendizado em uma conversa no ChatGPT, retomá-lo
no Claude, relacioná-lo a um problema discutido no Gemini e consultá-lo em um
agente próprio. A memória pertence ao usuário, não ao cliente de IA que originou
a conversa.

O UMCP não é apenas um banco vetorial e não deve ser apresentado como um dump de
histórico. Ele transforma trechos consentidos de conversas em memórias
estruturadas, conceitos, relações, decisões, objetivos e notas mentais que o
usuário consegue inspecionar, corrigir, fixar, exportar e apagar.

## 2. A promessa em uma frase

> Conecte seus assistentes a um único vault de memória, controlado por você.

## 3. Verdade de protocolo

Conectar um MCP não concede ao servidor acesso automático a todas as mensagens
de um chat. Um servidor MCP recebe somente chamadas de ferramenta e os
argumentos que o cliente decide enviar.

Consequências:

- em agentes próprios, o runtime pode integrar captura e recall ao ciclo de
  mensagens de forma determinística;
- em ChatGPT, Claude, Gemini e outros clientes, o comportamento depende das
  ferramentas, instruções, permissões e capacidades daquela superfície;
- a alegação pública correta é “memórias registradas por conversas conectadas ao
  UMCP ficam disponíveis aos outros clientes autorizados”;
- “todas as conversas são sincronizadas automaticamente” permanece proibido sem
  um mecanismo comprovado de ingestão naquela superfície;
- full transcript não é necessário para produzir valor e não deve ser o padrão.

## 4. Jornada principal

```text
usuário adiciona UMCP ao cliente de IA
                ↓
cliente inicia autorização em /oauth/authorize
                ↓
UMCP apresenta login e consentimento
                ↓
usuário entra com Google ou magic link
                ↓
token vincula conexão + usuário + tenant + scopes
                ↓
cliente pode recordar ou propor memórias conforme a política
                ↓
memórias estruturadas entram no vault isolado do tenant
                ↓
outro cliente autorizado consulta o mesmo vault
                ↓
dashboard explica o que foi lembrado, de onde veio e por que foi usado
```

### 4.1 Superfícies distintas

- `/`: landing pública;
- `/oauth/authorize`: login e consentimento da conexão;
- `/login`: entrada direta na plataforma;
- `/dashboard`: visão geral do vault;
- `/memories`: inventário e busca;
- `/memory-inbox`: candidatos aguardando revisão;
- `/concepts`: conceitos e relações;
- `/notes`: notas mentais importantes;
- `/activity`: captura, recall, alteração e revogação;
- `/connections`: clientes e agentes autorizados;
- `/settings/security`: sessões, export, retenção e deleção.

“Continuar com Google” é um método de identidade. Magic link por e-mail deve ser
mantido como alternativa para não limitar o produto a contas Gmail.

## 5. Unidade de valor: memória estruturada

Uma memória não é sinônimo de mensagem. Ela é um objeto revisável com:

- conteúdo normalizado;
- tipo;
- importância;
- confiança;
- estado;
- espaço;
- provenance;
- cliente e sessão de origem quando disponíveis;
- instante de captura;
- conceitos e relações;
- política de compartilhamento contextual;
- versão;
- profile de embedding;
- identificadores de consentimento e idempotência.

### 5.1 Tipos

- `fact`;
- `preference`;
- `decision`;
- `goal`;
- `lesson`;
- `insight`;
- `concept`;
- `hypothesis`;
- `relationship`;
- `open_question`;
- `project_context`;
- `mental_note`.

### 5.2 Estados

- `candidate`: sugerida, ainda não confirmada;
- `confirmed`: aceita como memória ativa;
- `pinned`: destacada pelo usuário;
- `contradicted`: há evidência incompatível;
- `superseded`: substituída por versão ou decisão posterior;
- `stale`: pode estar desatualizada;
- `archived`: preservada, mas fora do recall padrão;
- `forgotten`: resultado de deleção, nunca conteúdo persistido.

### 5.3 Espaços

Cada vault pode conter espaços:

- Global;
- Pessoal;
- MBA;
- Trabalho;
- projetos específicos;
- espaços customizados.

Cada espaço define se suas memórias podem participar de recall global, somente
de recall explícito ou nunca fora daquele contexto. Uma memória pessoal não
entra implicitamente em um workspace corporativo.

## 6. Pipeline de captura

```text
trecho explicitamente enviado pelo cliente
                  ↓
validação de consentimento e categorias proibidas
                  ↓
extração de candidatos
                  ↓
deduplicação, conflito e classificação
                  ↓
manual: aguarda comando
assistido: entra na Memory Inbox
automático: confirma dentro da política
                  ↓
embedding e relações
                  ↓
vault + provenance + audit metadata
```

### 6.1 Modos de captura

1. `disabled`: a conexão não registra memórias.
2. `manual`: somente comandos explícitos como “lembre disso”.
3. `assisted`: o UMCP propõe e o usuário confirma; padrão recomendado.
4. `automatic`: confirma candidatos permitidos e os deixa revisáveis.

As políticas existem por usuário, espaço e conexão. “Não memorize esta
conversa” precisa sobrepor qualquer configuração automática.

### 6.2 Categorias proibidas por padrão

- senhas, tokens, chaves e códigos de autenticação;
- dados de pagamento completos;
- segredos de terceiros;
- dados médicos ou jurídicos sem escolha explícita;
- conteúdo cuja origem não autoriza retenção;
- instruções de prompt apresentadas como se fossem fatos;
- payloads que scanners classificarem como credenciais.

## 7. Pipeline de recall

Recall deve procurar relevância sem despejar todo o perfil do usuário no
contexto.

```text
pergunta atual
    ↓
tenant + usuário + conexão + scopes
    ↓
espaços permitidos
    ↓
busca semântica + filtros + relações
    ↓
relevância + importância + confiança + atualidade
    ↓
política cross-space
    ↓
memórias mínimas com provenance e reason_retrieved
```

O resultado deve explicar, em linguagem curta:

- o que foi recuperado;
- de qual espaço veio;
- qual cliente o registrou;
- quando foi registrado;
- por que foi considerado relevante;
- se é fato confirmado, hipótese ou memória contradita.

Memória é dado não confiável. O cliente nunca deve tratar conteúdo recuperado
como instrução de sistema.

## 8. Exemplo canônico cross-assistant

### Captura

No ChatGPT, o usuário diz:

> No meu projeto do MBA, concluí que incentivos mal desenhados levam equipes a
> otimizar a métrica e não o resultado.

O cliente propõe ao UMCP:

```text
type: lesson
space: MBA
concepts: incentivos, métricas, comportamento organizacional
importance: high
source_client: chatgpt
state: candidate
```

O usuário confirma ou sua política assistida mantém o candidato na Inbox.

### Recall

No Claude, o mesmo usuário pergunta por que a equipe aumentou tickets encerrados
enquanto a satisfação caiu.

O UMCP relaciona `tickets encerrados → métricas → incentivos` e retorna a lição
do MBA com provenance. Claude pode então apresentar a conexão como memória do
usuário, não como conhecimento inventado.

### Isolamento

- Claude usa a mesma identidade/tenant e recebe a memória;
- um usuário de outro tenant recebe zero memórias;
- revogar o token do ChatGPT impede novas capturas por aquela conexão;
- a revogação não impede o Claude de usar o vault ainda autorizado;
- apagar a memória remove conteúdo, versões, relações e vetor online e cria a
  evidência operacional necessária para impedir ressurreição após restore.

## 9. Memory Atlas

O dashboard não é apenas administração. Ele é a representação navegável da
memória do usuário.

### 9.1 Key Concepts

Lista conceitos recorrentes com:

- resumo;
- número de memórias;
- espaços;
- evolução temporal;
- conceitos relacionados;
- evidências de origem;
- conflitos e perguntas abertas;
- data de última consolidação.

Um conceito é derivado e versionado. Seu resumo nunca substitui as memórias e
provenance que o sustentam.

### 9.2 Mental Notes

Bloco de notas mental composto por:

- memórias `pinned`;
- decisões importantes;
- ideias que merecem retorno;
- objetivos ativos;
- perguntas abertas;
- conexões cross-space relevantes;
- notas criadas diretamente pelo usuário.

Ações: confirmar, editar, pin/unpin, relacionar, mover de espaço, arquivar,
resolver e esquecer.

### 9.3 Memory Inbox

Fila transparente de candidatos:

```text
“Você parece preferir relatórios curtos.”
[Confirmar] [Editar] [Descartar] [Nunca registrar esta categoria]
```

Cada candidato precisa mostrar origem, razão da sugestão e política que o
produziu.

### 9.4 Memory Map

Uma visão de grafo ajuda a visualizar conceitos e relações, mas não substitui a
lista acessível. O usuário deve navegar por teclado e obter a mesma informação
em uma representação textual.

### 9.5 Activity e “Why recalled?”

Timeline sem conteúdo sensível em logs operacionais, mas com recibos seguros no
produto:

- memória proposta;
- confirmada;
- recuperada;
- alterada;
- contradita;
- exportada;
- esquecida;
- conexão criada ou revogada.

“Why recalled?” explica sinais públicos e determinísticos; não revela
chain-of-thought.

## 10. Identidade e tenancy

```text
User
 ├── Personal workspace/tenant
 │    ├── Personal vault
 │    ├── Spaces
 │    └── Connections
 └── Team workspaces futuros
      └── memória explicitamente compartilhada
```

Invariantes:

- identidade vem do token verificado;
- `owner_id` enviado pelo cliente nunca concede acesso em Cloud;
- cada query e job possui tenant context fail-closed;
- RLS e constraints reforçam o isolamento;
- conteúdo usa envelope encryption por tenant no design server-decryptable;
- conexões têm scopes e consentimentos próprios;
- o vault pessoal não é automaticamente visível ao empregador ou workspace;
- account linking entre clientes precisa resolver a mesma identidade canônica.

## 11. Superfície de protocolo desejada

Os quatro tools v0 continuam compatíveis. A evolução pode adicionar:

- `memory.capture`;
- `memory.search`/`memory.recall` com filtros por espaço;
- `memory.review_candidates`;
- `memory.confirm`;
- `memory.pin`;
- `memory.list_concepts`;
- `memory.get_concept`;
- `memory.list_mental_notes`;
- `memory.explain_recall`;
- `memory.get_source` com autorização explícita.

Novos tools precisam de versionamento, schemas estritos, scopes, annotations,
idempotência e conformance tests. A quantidade de tools deve ser mantida pequena
quando operações puderem ser compostas com segurança.

## 12. Princípios do produto

1. **Portabilidade:** trocar de modelo não apaga a memória.
2. **Controle:** o usuário pode inspecionar, corrigir e esquecer.
3. **Provenance:** toda memória relevante explica sua origem.
4. **Consentimento:** captura e recall respeitam política por conexão e espaço.
5. **Minimização:** guardar a memória útil, não a conversa inteira por padrão.
6. **Isolamento:** cross-client dentro do tenant; nunca cross-tenant.
7. **Honestidade:** compatibilidade e criptografia só são anunciadas após gates.
8. **Reversibilidade:** consolidação não destrói as evidências originais.
9. **Calma:** recall deve ajudar sem inserir fatos irrelevantes em todo assunto.
10. **Open core:** self-hosting e contratos auditáveis são parte da confiança.

## 13. Métricas de produto

### Ativação

- conta criada;
- primeira conexão autorizada;
- primeira memória confirmada;
- segundo cliente conectado;
- primeiro recall cross-client bem-sucedido.

### Valor

- percentual de recalls considerados úteis;
- tempo até primeiro recall cross-client;
- candidatos confirmados, editados e descartados;
- conceitos consultados;
- notas pinned revisitadas;
- redução de repetição de contexto percebida pelo usuário.

### Guardrails

- recall irrelevante/intrusivo;
- memória incorreta confirmada automaticamente;
- cross-tenant leakage: tolerância zero;
- captura de categoria proibida;
- memória sem provenance;
- deleção não efetivada;
- tokens revogados ainda aceitos;
- conteúdo sensível em logs;
- reclamações de surpresa: “não sabia que isso seria lembrado”.

## 14. Não objetivos do v1

- gravar todas as conversas;
- substituir o histórico nativo dos clientes;
- prometer suporte idêntico em todas as superfícies;
- agir como sistema de vigilância do usuário;
- E2EE ou zero knowledge sem arquitetura própria;
- compartilhar memória pessoal com equipes por inferência;
- diagnosticar personalidade, saúde ou intenção;
- transformar toda mensagem em memória;
- usar dados do usuário para treinar modelos sem escolha explícita.

## 15. Definition of Done da visão

A visão está materializada quando uma pessoa consegue:

1. entrar com Google ou e-mail;
2. conectar dois clientes suportados ao mesmo vault;
3. registrar uma lição no primeiro cliente;
4. recuperá-la semanticamente no segundo cliente;
5. ver origem e motivo do recall;
6. impedir acesso por outro tenant;
7. revogar apenas uma conexão;
8. revisar candidatos na Memory Inbox;
9. navegar por Key Concepts e Mental Notes;
10. corrigir, fixar, mover, exportar e esquecer;
11. restaurar um backup sem ressuscitar conteúdo esquecido;
12. compreender exatamente o que é e não é capturado.

Até esses comportamentos estarem testados, a visão permanece aceita como
produto, mas sua implementação continua parcial.
