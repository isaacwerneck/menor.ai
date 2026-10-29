# Menor.AI — correções de segurança e inspeção local

Arquivos incluídos:
- `mcp_server.py`: limita CORS, valida JSON/Content-Length, captura erros e restringe criação de pastas MCP a cerebro/. Ainda não tem autenticação; use somente em loopback confiável.
- `state_manager.py`: fixa o banco SQLite à raiz do projeto.
- `tui_dashboard.py`: remove métricas de GPU fictícias quando `nvidia-smi` falha.
- `agents.yaml`: cópia original; a configuração ainda não é carregada pelo `assistant.py` atual.
- `assistant.py`: reconhece pedidos genéricos de inspeção, injeta conteúdo real lido pelo Python, trata conteúdo de arquivos como dados não confiáveis, usa caminhos relativos à raiz do projeto e não executa ferramentas recém-geradas automaticamente.
- `file_ops.py`: corrige validação de caminhos, adiciona listagem/inspeção de arquitetura, impede sobrescrita por padrão e implementa as funções que `mcp_server.py` já tentava chamar.
- `middleware.py`: melhora o filtro de pedidos destrutivos de execução e limita resultados de pesquisa.
- `voice_assistant.py`: deixa explícito que o motor de voz ainda não chama o LLM principal em vez de fingir que processou o pedido.

## Como instalar
1. Faça backup dos arquivos atuais do projeto `Z:\menor.ai`.
2. Copie os quatro arquivos desta pasta para a raiz do projeto, substituindo os antigos somente depois de revisar o diff.
3. Execute `python -m py_compile assistant.py file_ops.py middleware.py voice_assistant.py`.
4. Inicie com `python assistant.py`.
5. Teste: `analisa os arquivos da sua arquitetura`.

## Notas importantes
- O código não foi executado no seu computador Windows; a validação foi feita por compilação sintática no ambiente de trabalho desta resposta.
- A ferramenta de leitura só inspeciona arquivos de texto permitidos dentro da raiz do projeto e evita `.env`, credenciais, ambientes virtuais, caches e dependências.
- As alterações destrutivas e gravações de arquivos existentes devem ser confirmadas. A geração de ferramentas valida a sintaxe antes de salvar, pede confirmação e não executa automaticamente código recém-gerado.
- Isto não é uma sandbox completa. Não exponha a porta MCP à rede pública; revise `mcp_server.py` separadamente antes de usá-lo com aplicações externas.


**Limite da revisão:** o servidor MCP continua sem autenticação de cliente. Apesar de estar vinculado a `127.0.0.1` e ter CORS limitado, use-o apenas em ambiente local confiável e não o exponha à rede. A configuração `agents.yaml` permanece sem integração com o loop principal.
