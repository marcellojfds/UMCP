# Fluxo de Captura e Recuperação Proativa de Pensamentos (UMCP)

**Status:** Implementado no servidor FastMCP do UMCP e pronto para uso nos clientes.

Este guia estabelece como configurar o **Claude**, o **ChatGPT** e o **Gemini** para operarem como um **Segundo Cérebro contínuo**, eliminando a necessidade de comandos manuais burocráticos como *"guarde isso no cofre"* ou *"procure no UMCP por X"*.

---

## 1. Como o Fluxo Funciona

Em vez de tratar a memória como um arquivo estático acionado apenas por comandos manuais, o assistente adota um **ciclo contínuo de pensamento**:

```text
[Usuário inicia novo tópico de domínio (ex: Marketing, Relacionamentos, Decisão X)]
                            │
                            ▼
    1. RECALL CONTEXTUAL SILENCIOSO
    O assistente dispara `memory.search(query=tópico, min_relevance=0.45)` em background.
       ├─ Se encontrar memórias: incorpora naturalmente na introdução da resposta.
       └─ Se não encontrar: responde diretamente sem citar a ferramenta.
                            │
                            ▼
    [Desenvolvimento do diálogo e reflexão conjunta]
                            │
                            ▼
    2. CAPTURA FLUIDA DE CONCLUSÕES
    Ao atingir uma síntese, decisão estratégica, princípio ou modelo mental maduro:
    O assistente dispara `memory.capture(content, type, space, reason)` automaticamente.
                            │
                            ▼
    3. CONFIRMAÇÃO NÃO-INVASIVA
    O assistente finaliza a resposta com um rodapé elegante:
    `[🧠 Diretriz registrada no cofre: "<resumo curto>" em #espaço]`
```

---

## 2. Configurações por Cliente

### 2.1 Claude (Claude Desktop, Claude Projects ou Claude Code)

#### Opção A: No Claude Desktop (`claude_desktop_config.json`) ou Claude Code
Certifique-se de que o servidor MCP está registrado apontando para o endpoint do UMCP Cloud:

```json
{
  "mcpServers": {
    "umcp": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-fetch",
        "https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp"
      ]
    }
  }
}
```
*(Ou conectando diretamente via OAuth no Claude Code: `claude mcp add --transport http umcp https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp`)*.

#### Opção B: Nas "Project Instructions" do Claude ou no `CLAUDE.md`
Cole o bloco de instruções comportamentais da Seção 3 abaixo.

---

### 2.2 ChatGPT (Custom Instructions ou Custom GPT)

1. Acesse **Configurações → Instruções Personalizadas (Custom Instructions)** ou edite as instruções do seu **Custom GPT**.
2. No campo *"Como você gostaria que o ChatGPT respondesse?"*, cole o bloco da Seção 3.
3. Se estiver usando Connected Apps / MCP Actions, garanta que a ferramenta `memory.capture` e `memory.search` estejam autorizadas.

---

### 2.3 Gemini (Gemini Spark ou Gems)

1. No **Gemini Settings → Personal Intelligence → Connected Apps**, certifique-se de que o **Umcp Cloud** está conectado e autorizado via OAuth.
2. Ao criar um **Gem** dedicado ou nas instruções de sistema, inclua o bloco da Seção 3.

---

## 3. Protocolo de Sistema para Colar nos Assistentes

Copie e cole o texto abaixo nas instruções de sistema (System Prompt / Custom Instructions) do seu assistente:

```markdown
### SECOND BRAIN PROTOCOL (UMCP CONTINUOUS MEMORY)

Você tem acesso ao cofre pessoal de memória de longo prazo do usuário através do UMCP.
Você deve agir como um parceiro de pensamento com memória contínua e proativa:

1. RECUPERAÇÃO PROATIVA (RECALL CONTEXTUAL):
- Ao iniciar uma nova conversa ou quando o usuário trouxer um tema com profundidade conceitual
  (por exemplo: estratégias de marketing, princípios de relacionamentos, decisões de carreira,
  regras de arquitetura de software, preferências pessoais):
  Execute `memory.search` silenciosamente com o tema ou termos-chave antes de formular sua resposta.
- Se houver memórias relevantes recuperadas: conecte o passado ao presente de forma fluida
  (ex: "Considerando o princípio que definimos anteriormente sobre X...", "Seguindo a diretriz de marketing que já adotamos...").
- Se a busca vier vazia: responda normalmente sem menções técnicas.

2. CAPTURA PROATIVA (PENSAMENTO FLUIDO):
- Durante a conversa, quando um raciocínio amadurecer e vocês chegarem a uma conclusão
  significativa, uma decisão estratégica, uma lição aprendida ou um novo modelo mental:
  Execute `memory.capture` imediatamente, sem esperar que o usuário diga "salve isso":
  * content: Uma declaração atômica, auto-suficiente e clara do aprendizado.
  * type: O tipo exato ('insight', 'decision', 'lesson', 'preference', 'concept', 'goal').
  * space: A categoria temática (ex: 'marketing', 'relacionamentos', 'negocios', 'pessoal').
  * reason: Breve contexto do porquê essa conclusão é relevante no longo prazo.
  * source_model: O seu modelo (ex: 'claude', 'chatgpt', 'gemini').
- No final da sua resposta, adicione uma nota sutil:
  `[🧠 Conclusão salva no cofre: "<resumo curto>" em #espaço]`

3. FILTRO DE RUÍDO (GUARDRAILS):
- NÃO memorize dados efêmeros, rascunhos provisórios, conversas triviais ou tarefas descartáveis.
- NUNCA capture credenciais, senhas, chaves de API ou segredos.
- Mantenha o cofre limpo e de alto sinal.
```

---

## 4. Tipos e Espaços Recomendados

Para manter o cofre do UMCP organizado no portal (`/portal/`):

| Tipo (`type`) | Quando o modelo deve usar | Exemplo de conteúdo |
| :--- | :--- | :--- |
| `decision` | Decisões fechadas e acordadas | *"No marketing do produto X, decidimos focar 100% em conteúdo técnico no LinkedIn antes de testar tráfego pago."* |
| `insight` | Conclusões conceituais ou modelos mentais | *"Em relacionamentos profissionais, a clareza de expectativas reduz conflitos mais rápido do que acordos verbais vagos."* |
| `lesson` | Lições práticas pós-experiência | *"Campanhas focadas apenas em aquisição sem onboarding estruturado geram churn prematuro."* |
| `preference` | Preferências de trabalho, estilo ou vida | *"Prefiro comunicação assíncrona detalhada a reuniões de alinhamento recorrentes."* |
| `goal` | Metas e objetivos de médio/longo prazo | *"Alcançar os primeiros 100 usuários ativos do produto até o final do trimestre."* |

---

## 5. Verificação do Fluxo

1. **Teste de Captura Fluida:**
   - No chat do Claude/ChatGPT/Gemini, debata um dilema (ex: *"Estou pensando em como posicionar meu novo serviço de consultoria..."*).
   - Ao chegarem a uma definição clara, observe o assistente registrar a conclusão via `memory.capture` e sinalizar no rodapé.
   - Acesse o portal do UMCP (`https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/`) e veja a nova memória com tags, tipo e espaço atribuídos.

2. **Teste de Recuperação Proativa:**
   - Em uma nova conversa ou em outro assistente conectado, inicie uma pergunta relacionada ao tema (ex: *"Como devo estruturar a proposta comercial da consultoria?"*).
   - Observe o modelo consultar o UMCP em background e responder já considerando a premissa de posicionamento capturada anteriormente.
