# Plano Diretor de Arquitetura e Roadmap de Desenvolvimento: Menor.AI

Este documento estabelece o **Plano Diretor de Arquitetura e Roadmap de Execução Incremental** para o assistente pessoal **Menor.AI**. O objetivo fundamental do projeto é construir um agente autônomo, altamente contextualizado, persistente e capaz de realizar ações reais no sistema operacional, rodando 100% localmente em hardware de entrada — especificamente em uma GPU **NVIDIA GeForce GTX 1650 (4GB VRAM)**.

---

## 1. Arquitetura do Sistema e Limites de Hardware

A engenharia do **Menor.AI** foi projetada sob a premissa de eficiência máxima por token e controle rigoroso da memória de vídeo (VRAM). Em placas de 4GB, a alocação de memória pelo runtime do Ollama precisa ser estritamente orçamentada para evitar que o modelo seja empurrado para a memória RAM do sistema através de *shared memory*, o que degradaria drasticamente a velocidade de inferência.

```
USUÁRIO / TERMINAL
       │
       ▼
MOTOR DE DECISÃO RÁPIDO (LAYA)
  • Classificação em ~30ms (Categorias: preferências, projetos, etc)
  • Avaliação de salvamento (deve_salvar > 0.75)
       │
       ├───────────────────────────────────────┐
       ▼ (Se deve salvar)                      ▼ (Recall de contexto)
PERSISTÊNCIA LOCAL / CÉREBRO (.MD)      RECURSO DE MEMÓRIA (ORIMNEMOS SQL)
  • cerebro/preferencias/usuario.md       • CLI/MCP Bridge (npx ori-memory)
  • cerebro/projetos/                     • Busca semântica e contextual
  • cerebro/memorias/diario.md                 │
  • cerebro/conhecimentos/                     │
       │                                       │
       └───────────────────┬───────────────────┘
                           ▼
        SLIDING WINDOW CONTEXT MANAGER (FASE 3)
          • Preserva System Prompt (Posição 0)
          • Poda histórico (MAX_HISTORICO = 6)
                           │
                           ▼
               INFERÊNCIA LOCAL (OLLAMA)
          • Modelo: Qwen 2.5-Coder (3B Parâmetros)
          • VRAM Alocada: ~2.2 GB / 4.0 GB (GTX 1650)
```

### Componentes Principais da Pilha Tecnológica:
1. **Modelo Primário de Linguagem**: `qwen2.5-coder:3b` rodando via Ollama. Modelo de 3 bilhões de parâmetros otimizado para instrução, raciocínio lógico, geração e manipulação de código.
2. **Motor de Roteamento e Decisão**: `Laya` (`pip install laya`). Modelo não-autoregressivo de classificação única em ~30ms que toma decisões de fluxo sem gastar geração do LLM e sem alucinações.
3. **Gerenciador de Memória Relacional/Vetorial**: `OriMnemos` (`npm install -g ori-memory`). Banco local-first que permite gravar (`remember`) e consultar (`recall`) memórias via ponte CLI/MCP.
4. **Cérebro de Arquivos Locais**: Estrutura de diretórios em Markdown (`cerebro/`) organizada em `preferencias/`, `projetos/`, `memorias/` e `conhecimentos/`.

---

## 2. Status Atual da Execução (Fases 1 a 5)

Abaixo encontra-se o registro consolidado das etapas já projetadas, validadas e implementadas no arquivo principal `assistant.py`.

### Tabela de Progresso Atual
* **[CONCLUÍDO]** **Fase 1: Infraestrutura & Inferência Local**
  * Execução do Ollama com modelo `qwen2.5-coder:3b` integrado via Python SDK.
  * Respostas em tempo real via *streaming* (`stream=True`) no terminal.
  * Garantia de inferência 100% local rodando na placa GTX 1650.
* **[CONCLUÍDO]** **Fase 2: Identidade & System Prompt Personalizado**
  * Definição da personalidade **Menor** (assistente moderno, objetivo e prestativo em PT-BR).
  * Injeção de instruções fundamentais no System Prompt para manter tom de resposta natural.
* **[CONCLUÍDO]** **Fase 3: Gerenciamento Dinâmico de Contexto (Janela Deslizante)**
  * Implementação da função `podar_historico()` com limite fixo (`MAX_HISTORICO = 6`).
  * Preservação incondicional do System Prompt na posição inicial (`historico[0]`).
  * Proteção do KV Cache para impedir travamentos de VRAM por acúmulo de contexto.
* **[CONCLUÍDO]** **Fase 4: Memória Persistente e Estrutura `cerebro/`**
  * Criação automática da estrutura de diretórios em `cerebro/`: `preferencias/`, `projetos/`, `memorias/` e `conhecimentos/`.
  * Carregamento automático do arquivo `preferencias/usuario.md` no arranque do script.
  * Módulo de consolidação diária: ao digitar `sair`, o Menor gera um resumo automático da sessão e grava em `cerebro/memorias/diario.md` com data e hora.
* **[CONCLUÍDO]** **Fase 5: Decisão Não-Autoregressiva e Ponte OriMnemos**
  * Integração do **Laya** para rotear mensagens em ~30ms e definir onde salvar cada fato.
  * Ponte com **OriMnemos** (`ori_remember` e `ori_recall`) executada via CLI `npx ori-memory`.
  * Inicialização defensiva do Laya com aquecimento (*warmup*) para evitar travamento na primeira interação.

---

## 3. Módulo A: Execução Real no Sistema de Arquivos (File System Tooling)

Como identificado no diagnóstico da conversa (arquivo `aaaaaa.txt`), o modelo de linguagem isolado tenta simular a criação de pastas desenhando árvores de texto no chat. Este módulo adicionará capacidades reais de escrita no sistema operacional Windows via Python.

> **Objetivo do Módulo A**: Permitir que o Menor crie pastas, arquivos `.md`, salve trechos de código e manipule arquivos de verdade na máquina do usuário, fornecendo retorno transparente no terminal confirmando a criação física com o caminho exato do arquivo.

### Checklist de Implementação - Módulo A
* **[CONCLUIDO]** **A.1 - Criar Módulo Native Tooling (`tools/file_ops.py`)**
  * Desenvolver funções Python para `criar_pasta(caminho)`, `criar_arquivo(caminho, conteudo)`, `listar_diretorio(caminho)` e `ler_arquivo(caminho)`.
  * Adicionar validações de segurança para impedir a sobrescrita acidental de arquivos do sistema.
* **[CONCLUIDO]** **A.2 - Integrar Laya para Detecção de Intenção de Arquivo**
  * Adicionar pergunta ao roteador Laya: `"O usuário solicitou explicitamente a criação de um arquivo ou pasta no computador?"`.
  * Mapear o nome da pasta e o tipo de conteúdo desejado caso a probabilidade seja superior a `0.80`.
* **[CONCLUIDO]** **A.3 - Implementar Loop de Retorno do Sistema**
  * Quando o Python executar a criação do arquivo no Windows, injetar uma mensagem de sistema no contexto do Menor confirmando o sucesso da operação.
  * Ajustar o System Prompt para proibir o Menor de fingir que criou um arquivo antes da confirmação do script Python.

---

## 4. Módulo B: Gestão Avançada de VRAM e Compactação de Contexto

Para manter o tempo de resposta do Menor extremamente rápido no hardware de 4GB VRAM, este módulo implementará técnicas avançadas de gerenciamento e compressão de memória de curto prazo.

> **Objetivo do Módulo B**: Reduzir a carga de tokens enviada ao Ollama em até 60% e garantir que conversas longas não percam o fio da meada através de resumos cumulativos.

### Checklist de Implementação - Módulo B
* **[PENDENTE]** **B.1 - Poda Semântica de Histórico via Laya (Semantic Pruning)**
  * Antes de enviar o histórico para o Ollama, passar as mensagens pelo Laya para filtrar saudações redundantes ("opa", "blz", "valeu") e confirmações curtas.
  * Manter na janela deslizante apenas frases que contêm conceitos, dúvidas ou dados técnicos.
* **[PENDENTE]** **B.2 - Resumo Hierárquico Cumulativo**
  * Quando a janela de mensagens atingir o limite (`MAX_HISTORICO`), em vez de descartar as mensagens antigas, condensá-las em um bloco mantido no topo do histórico: `[RESUMO DAS MENSAGENS ANTERIORES]`.
  * Atualizar esse resumo de forma incremental a cada 5 trocas de mensagens.
* **[PENDENTE]** **B.3 - Otimização de Parâmetros do Ollama (`num_ctx` e Quantização)**
  * Ajustar dinamicamente o parâmetro `num_ctx` da API do Ollama dependendo da tarefa (ex: 2048 tokens para bate-papo, 4096 tokens para código).
  * Testar e ativar a quantização de KV Cache no Ollama (`OLLAMA_KV_CACHE_TYPE=q8_0`) para economizar VRAM.

---

## 5. Módulo C: Cérebro Avançado, Obsidian Vault & OriMnemos Híbrido

O cérebro do Menor precisa evoluir de uma estrutura passiva de arquivos para um ecossistema ativo de conhecimento, perfeitamente sincronizado com ferramentas do usuário.

> **Objetivo do Módulo C**: Conectar a pasta `cerebro/` diretamente ao **Obsidian** para visualização do mapa mental em tempo real e implementar mecanismos de desduplicação e busca híbrida no banco do OriMnemos.

### Checklist de Implementação - Módulo C
* **[PENDENTE]** **C.1 - Integração Nativa com Obsidian Vault**
  * Configurar a pasta `cerebro/` para seguir a estrutura padrão de notas do Obsidian com links internos (`[[Conceito]]`).
  * Adicionar cabeçalhos YAML (frontmatter) automáticos nas notas salvas pelo Menor com tags (`#design`, `#ui`, `#hardware`).
* **[PENDENTE]** **C.2 - Atualização e Resolução de Contradições no OriMnemos**
  * Criar rotina em Python que verifica se um novo fato contradiz uma memória antiga (ex: alteração de GPU ou apelido).
  * Implementar o comando de atualização/substituição de registros no OriMnemos para evitar memórias obsoletas.
* **[PENDENTE]** **C.3 - Busca Híbrida (Lexical BM25 + Semantic Vector Search)**
  * Combinar a busca semântica do OriMnemos com busca por palavra-chave exata para nomes de funções, arquivos e termos técnicos específicos.

---

## 6. Módulo D: Protocolo MCP (Model Context Protocol) & Conectividade

O Model Context Protocol (MCP) é a especificação moderna para conectar assistentes de IA a ferramentas, bancos de dados e ambientes de desenvolvimento de forma padronizada e sem estado.

> **Objetivo do Módulo D**: Adequar o Menor à especificação MCP stateless sobre HTTP/JSON-RPC e permitir que o Menor atue como cliente e servidor MCP para interagir com extensões do VS Code.

### Checklist de Implementação - D
* **[PENDENTE]** **D.1 - Configuração da Ponte MCP no OriMnemos**
  * Executar e validar o servidor MCP nativo do OriMnemos (`npx ori-memory serve --mcp`).
  * Conectar o script Python ao servidor MCP via protocolo JSON-RPC.
* **[PENDENTE]** **D.2 - Módulo Cliente MCP em Python (`mcp_client.py`)**
  * Implementar cliente HTTP/Headers stateless compatível com o novo padrão Cloudflare/Anthropic MCP.
  * Permitir que o Menor descubra e execute ferramentas MCP expostas localmente no sistema.

---

## 7. Módulo E: Interface Visual TUI & Interatividade por Voz

Substituir o terminal de texto simples por uma interface rica e moderna no terminal, preparando o assistente para interação multimodal por voz rodando 100% localmente.

> **Objetivo do Módulo E**: Criar um painel visual no terminal com dados de VRAM, status do Laya, OriMnemos e histórico, além de adicionar escuta e fala por voz sem dependência de APIs pagas.

### Checklist de Implementação - Módulo E
* **[PENDENTE]** **E.1 - Interface Terminal Rica com `rich` / `textual`**
  * Desenvolver interface gráfica de terminal (TUI) exibindo:
    * Painel de resposta do Menor em Markdown formatado.
    * Barra lateral com status do Laya (categoria decidida e probabilidade).
    * Indicador de memórias carregadas do OriMnemos.
    * Monitor de uso de memória VRAM em tempo real.
* **[PENDENTE]** **E.2 - Transcrição de Voz Local via OpenAI Whisper (`whisper-tiny`)**
  * Integrar o modelo `whisper-tiny` em C++/Python para capturar áudio do microfone e converter em texto localmente em menos de 500ms.
* **[PENDENTE]** **E.3 - Síntese de Voz (TTS) Local em Português via Piper TTS**
  * Configurar o motor Piper TTS com voz natural em PT-BR para falar as respostas do Menor no alto-falante sem latência.

---

## 8. Matriz de Priorização e Plano de Execução Incremental

Para garantir que o desenvolvimento ocorra de forma organizada e sem quebrar as funcionalidades já existentes no `assistant.py`, a execução seguirá a ordem de prioridades definida abaixo:

| Ordem | Módulo | Funcionalidade Chave | Impacto Principal |
| :---: | :---: | :--- | :--- |
| **1º** | **Módulo A** | Ações reais no File System (`tools/file_ops.py`) | Elimina alucinações sobre criar pastas/arquivos |
| **2º** | **Módulo B** | Poda semântica de contexto e resumo cumulativo | Mantém a GPU GTX 1650 rápida em sessões longas |
| **3º** | **Módulo C** | Formatação Obsidian + Destaque Frontmatter | Transforma o `cerebro/` em um cofre visual navegável |
| **4º** | **Módulo E1** | Interface TUI no terminal (`rich`) | Melhora drasticamente a experiência do usuário |
| **5º** | **Módulo D** | Cliente/Servidor MCP Stateless | Conecta o Menor a IDEs e ferramentas externas |
| **6º** | **Módulo E2/E3**| Entrada e Saída por Voz (Whisper + Piper) | Transforma o Menor em assistente de voz completo |

---

## 9. Guia de Manutenção e Atualização do Documento

Este documento é vivo e deve ser mantido como referência de verdade do projeto **Menor.AI**. À medida que cada subitem for implementado no arquivo `assistant.py` ou em seus módulos auxiliares, a marcação do checklist neste arquivo deverá ser atualizada conforme o padrão:

* `* **[PENDENTE]**` -> Item ainda não iniciado.
* `* **[/] EM ANDAMENTO**` -> Item em fase de desenvolvimento ou testes.
* `* **[CONCLUÍDO]**` -> Item implementado, testado e validado em código real.
