# Master Blueprint de Arquitetura & Roadmap de Desenvolvimento: Menor.AI (v2.0)

Este documento estabelece o **Plano Diretor de Arquitetura, Engenharia de Prompt e Execução de Segunda Geração** para o assistente pessoal autônomo **Menor.AI**. 

O objetivo do sistema é atuar como um **Agente Autônomo com Auto-Evolução (Self-Evolving Agent)**, intuitivo, proativo, contextualizado e capaz de executar ações reais no sistema operacional Windows, operando 100% localmente em hardware de entrada — especificamente em uma GPU **NVIDIA GeForce GTX 1650 (4GB VRAM)**.

---

## 1. Arquitetura de Duas Velocidades & Limites de Hardware

A engenharia do **Menor.AI** divide a inteligência em três camadas fundamentais para eliminar a alucinação de ações, evitar estouro de memória de vídeo (VRAM) e garantir tempos de resposta abaixo de 50ms para decisões lógicas:

```
                               ┌─────────────────────────────────────────┐
                               │           ENTRADA DO USUÁRIO            │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │     DECOMPOSITOR DE MULTI-INTENÇÕES     │
                               │     • Separa frases em N sub-tarefas    │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  SISTEMA 1: ROTEADOR LAYA ENGINE (~30ms) │
                               │  • Predict não-autoregressivo          │
                               │  • JSON Schema Estrito                  │
                               │  • Captura Passiva de Ideias            │
                               └────────────────────┬────────────────────┘
                                                    │
                   ┌────────────────────────────────┴────────────────────────────────┐
                   ▼                                                                 ▼
┌──────────────────────────────────────┐                         ┌──────────────────────────────────────┐
│  HARNESS PYTHON & GATEKEEPER DE SO   │                         │    BUSCA DE MEMÓRIA (ORIMNEMOS)      │
│  • CRUD Físico (Criar/Editar/Mover)  │                         │    • Recall de fatos passados        │
│  • Lixeira de Segurança (.lixeira/)  │                         │    • Busca Semântica + Obsidian Vault│
│  • Context Hooks (Regras da Pasta)   │                         └──────────────────┬───────────────────┘
└──────────────────┬───────────────────┘                                            │
                   │                                                                │
                   └────────────────────────────────┬───────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │    INJEÇÃO DE CONTEXTO & COMPRESSÃO    │
                               │    • System Prompt + Regras (Max 300t)  │
                               │    • Resumo Cumulativo (Sliding Window) │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │ SISTEMA 2: INFERÊNCIA LOCAL (OLLAMA 3B) │
                               │ • Qwen 2.5-Coder 3B (100% GPU / GTX1650)│
                               │ • num_gpu=99 | num_ctx=2048             │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │    MODO REFLEXÃO (AUTO-EVOLUÇÃO)        │
                               │ • Análise Semanal de Padrões            │
                               │ • Promoção de Preferências (usuario.md) │
                               │ • Auto-Correção (auto_melhoria.md)     │
                               └─────────────────────────────────────────┘
```

---

## 2. As 5 Engrenagens Tecnológicas do Sistema

### 2.1. Sistema 1: Decisão Rápida e Sem Alucinação (Laya Engine)
* **Tempo de Resposta**: ~30ms via predição *single forward pass* em CPUs/GPUs.
* **Função**: Substitui completamente o uso de expressões regulares (Regex) em Python.
* **Propriedades**: Não gera texto caractere por caractere; portanto, tem **0% de alucinação** e consome 0 tokens do LLM.
* **Confidence Gating**: Se a confiança da classificação for menor que `0.75` (75%), o sistema bloqueia execuções automáticas e abre uma interface de confirmação interativa.

### 2.2. Sistema 2: Raciocínio & Resposta (Qwen 2.5-Coder 3B via Ollama)
* **Modelo**: `qwen2.5-coder:3b` rodando via Ollama com quantização Q4_K_M (~1.9 GB VRAM).
* **Configuração de Performance GPU**:
  ```python
  OLLAMA_OPTIONS = {
      "num_gpu": 99,    # Offload de 100% das camadas na GTX 1650 (evita uso da RAM)
      "num_ctx": 2048,  # Orçamento de contexto otimizado para economizar VRAM
      "temperature": 0.7
  }
  ```
* **Papel**: Focado exclusivamente em conversação, explicação técnica, síntese e geração de código. Proibido de fingir ações em disco.

### 2.3. Harness Python, Conectividade MCP & Interface TUI/Rich
* **MCP Stateless (Model Context Protocol)**: Conexão padronizada de ferramentas via JSON-RPC/Headers sem estado.
* **Menu Interativo Rich/Textual**: Quando houver ambiguidade ou baixa confiança no roteamento, o terminal exibe um menu visual formatado com opções numeradas de múltipla escolha e um campo de texto para caminho livre.

### 2.4. Cérebro de Conhecimento, Obsidian Vault & OriMnemos
* **Obsidian Vault (`cerebro/`)**: Estrutura em Markdown organizada em `conhecimentos/`, `projetos/`, `preferencias/` e `memorias/`.
* **Sincronização de Metadados**: Notas geradas com **YAML Frontmatter** e **WikiLinks bidirecionais** (`[[Design]]`, `[[Conceito]]`).
* **OriMnemos**: Banco relacional/vetorial local-first acessado via CLI (`npx ori-memory`).

### 2.5. Diário Estruturado & Modo Reflexão (Self-Evolving Agent)
* **Estrutura por Data**: `cerebro/memorias/diario/YYYY-MM-DD/topico.md`.
* **Modo Reflexão (Meta-Aprendizado)**:
  1. *Análise de Preferências*: Promove regras ao `usuario.md` somente se observadas em $\ge 3$ sessões do diário ou solicitadas explicitamente.
  2. *Refinamento de Tom*: Ajusta as diretrizes do System Prompt para eliminar respostas robóticas.
  3. *Auto-Correção*: Registra aprendizados de falhas operacionais em `auto_melhoria.md`.

---

## 3. Matriz de Módulos & Lista de Verificação de Implementação

### [CONCLUÍDO] Módulo 1: Performance & Offload de GPU (100% VRAM)
- [x] Configuração de `num_gpu=99` e `num_ctx=2048` na API do Ollama.
- [x] Eliminação do vazamento de memória para a RAM do sistema.
- [x] Validação via `ollama ps` e `nvidia-smi` com 100% de offload na GTX 1650.

### [CONCLUÍDO] Módulo 2: Formatação Obsidian Vault & WikiLinks
- [x] Injeção de cabeçalho YAML Frontmatter (`title`, `date`, `category`, `tags`, `author`).
- [x] Auto-formatting de WikiLinks bidirecionais em conceitos chave.

### [PENDENTE] Módulo 3: Decompositor de Múltiplas Intenções (Multi-Intent Loop)
- [ ] Implementar algoritmo de separação de frases compostas em $N$ sub-tarefas.
- [ ] Loop de execução sequencial: Ação em disco -> Notificação real no SO -> Processamento conversacional no Qwen.

### [PENDENTE] Módulo 4: Harness CRUD, Lixeira de Segurança & Gatekeeper
- [ ] Implementar funções físicas em `file_ops.py`: `criar_pasta`, `salvar_arquivo`, `renomear_item`, `editar_arquivo`, `deletar_item`.
- [ ] **Gatekeeper Destrutivo (Human-in-the-Loop)**: Exigir confirmação explícita no terminal ("Posso deletar a pasta X e os arquivos Y, Z?") para ações de exclusão ou alteração de nomes.
- [ ] **Lixeira Reciclável**: Mover itens apagados para `cerebro/.lixeira/YYYY-MM-DD/` em vez de executar `os.remove()` definitivo.

### [PENDENTE] Módulo 5: Context Hooks & Teto Rígido de Regras (300 Tokens)
- [ ] Injeção automática das regras de `cerebro/conhecimentos/<tema>/regras.md` no `SYSTEM_PROMPT`.
- [ ] **Teto Rígido de Tokens**: Limitar o contexto injetado a no máximo 300 tokens (~20 linhas) para não sobrecarregar a VRAM da placa.

### [PENDENTE] Módulo 6: Captura Passiva de Ideias via Laya Router
- [ ] Mapear intenção `compartilhar_ideia` no Laya em ~30ms.
- [ ] Gravação automática em `cerebro/projetos/` e sincronização no OriMnemos sem necessidade de comando explícito do usuário.

### [PENDENTE] Módulo 7: Diário Estruturado por Data & Modo Reflexão
- [ ] Organização do diário de bordo na hierarquia `cerebro/memorias/diario/YYYY-MM-DD/topico.md`.
- [ ] Ciclo offline do Modo Reflexão ao encerrar a sessão:
  - Atualização de `usuario.md` baseada em regra de consenso ($\ge 3$ ocorrências).
  - Escrita do log de auto-melhoria em `auto_melhoria.md`.

### [PENDENTE] Módulo 8: Interface Interativa TUI/Rich
- [ ] Implementação de menus interativos com `rich`/`textual` no terminal para amostragem de opções de múltipla escolha e entrada livre de caminhos quando a confiança for < 75%.

### [PENDENTE] Módulo 9: Aprendizado Autônomo na Web via MCP (Web Research)
- [ ] Conexão do client MCP com ferramenta de busca web leve (DuckDuckGo/Tavily).
- [ ] Fluxo autônomo de estudo de fóruns, wikis e documentações com resumo condensado salvo em `cerebro/conhecimentos/`.

---

## 4. Matriz de Blindagens de Engenharia & Casos de Teste

| Ponto Cego Identificado | Risco Operacional | Solução de Engenharia Injetada |
| :--- | :--- | :--- |
| **Comandos Compostos** | Ignorar partes da frase do usuário. | Pipeline de Decomposição Sequencial (Multi-Intent Loop). |
| **Regras de Pasta Longas** | Estouro de VRAM e vazamento para RAM. | Teto Rígido de 300 tokens no Context Hook. |
| **Exclusão Acidental** | Perda permanente de dados do cérebro. | Lixeira de Segurança (`.lixeira/`) + Confirmation Gatekeeper. |
| **Drift de Personalidade** | Atualizar preferências por frases de um único dia. | Regra de Consenso Multi-Sessão ($\ge 3$ ocorrências) no Modo Reflexão. |
| **Ambuidade de Entrada** | Criar pastas ou arquivos com caminhos errados. | Confidence Gating (< 75%) com Menu Interativo Rich TUI. |

---

*Este blueprint representa a especificação completa, unificada e sem omissões de todas as discussões de arquitetura do Menor.AI.*
