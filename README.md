# Menor.AI — versão integrada e reforçada

Esta versão substitui os fluxos de intenção frágeis por ferramentas reais de leitura/pesquisa/edição. Não existe uma promessa de segurança absoluta: o pacote aplica limites concretos e precisa ser testado no ambiente real antes de uso diário.

## O que mudou

- **Tool calling real** com OpenRouter ou Ollama, com limite de ciclos de ferramenta.
- **Fallback determinístico de inspeção**: pedidos como “olha os arquivos da sua arquitetura” fazem listagem e leitura dos módulos reais em vez de responder que não tem acesso.
- **Ferramentas locais**: listar, ler, pesquisar, escrever, criar pasta, mover para lixeira, pesquisar web e consultar/salvar memória.
- **Gatekeeper**: escrita, criação de pasta, memória persistente e remoção exigem digitar `SIM` no terminal.
- **Raiz confinada**: caminhos absolutos externos, traversal (`..`), links simbólicos para fora e arquivos sensíveis são bloqueados.
- **Backups por arquivo** antes de sobrescrever arquivos existentes em `.menor_backups/`; gravação atômica e validação AST para `.py` antes de substituir o original.
- **Supervisor externo de recuperação**: executa compilação/testes antes de iniciar; se a validação falhar ou o processo cair, restaura o último checkpoint conhecido como bom e tenta reiniciar uma vez. O checkpoint só é atualizado após encerramento limpo e nova validação.
- **Sem execução automática de código gerado** nem ferramenta genérica de shell.
- **MCP opcional somente leitura**, restrito a localhost; não oferece escrita, exclusão nem execução remota.
- **Voz conectada ao mesmo `respond()`** em vez de gerar resposta simulada.
- **Histórico e SQLite** com caminho estável relativo ao arquivo do projeto.
- Testes de segurança básicos incluídos.

## Instalação (Windows / PowerShell)

1. Faça backup de `Z:\menor.ai`.
2. Extraia o pacote em uma pasta temporária e revise os arquivos.
3. Copie os arquivos do pacote para `Z:\menor.ai`, sem substituir seu `.env` existente. O pacote não inclui chave API.
4. No PowerShell, dentro da pasta do projeto, instale o supervisor fora da raiz editável pelo agente:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\instalar_guardian.ps1
```

Isso cria `Z:\.menor.ai_guardian\supervisor.py` (ajustado automaticamente ao nome/local da pasta) e o launcher `iniciar_menor_com_guardian.bat`. Use esse launcher, não `python assistant.py`, para ter recuperação automática.
5. No terminal:

```powershell
cd Z:\menor.ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

6. Se usar OpenRouter, copie `.env.example` para `.env` e preencha `OPENROUTER_API_KEY`. Se preferir Ollama, instale/inicie o Ollama e baixe o modelo configurado:

```powershell
ollama pull qwen2.5-coder:3b
```

7. Teste sintaxe e testes:

```powershell
python -m py_compile assistant.py file_ops.py middleware.py state_manager.py mcp_server.py voice_assistant.py tui_dashboard.py
python -m unittest discover -s tests -v
```

8. Inicie:

```powershell
iniciar_menor_com_guardian.bat
```

## Exemplos

- `tu consegue olhar os arquivos da sua arquitetura?` — lista e lê módulos principais.
- `leia file_ops.py` — lê o arquivo real.
- `procure onde o projeto salva checkpoints` — o modelo pode usar `search_files`.
- `/arquivos` — lista arquivos.
- `/ler assistant.py` — leitura direta.
- `/buscar checkpoint` — pesquisa local.
- `edite README.md para ...` — deve usar `write_file`; o terminal pedirá confirmação digitando `SIM`.

## MCP opcional

Por padrão, o servidor não inicia com o assistente. Se precisar dele, defina `MENOR_MCP_TOKEN` no `.env` e execute `python mcp_server.py`. O servidor escuta somente em `127.0.0.1` e oferece apenas leitura/listagem/pesquisa. Configure o cliente MCP para enviar `Authorization: Bearer <token>` se ele suportar cabeçalhos personalizados. Não encaminhe essa porta para a internet.

## Voz e dashboard

- `python voice_assistant.py` — depende de `pyttsx3` e `SpeechRecognition`; o reconhecimento pode recorrer a serviço externo se `recognize_whisper` não estiver disponível.
- `python tui_dashboard.py` — interface Rich opcional; usa o mesmo agente.

## Limitações importantes

- Nenhum prompt ou filtro torna um agente “100% blindado”. O supervisor externo protege contra erros detectáveis por sintaxe/testes e crashes; não detecta toda falha lógica. Mantenha backups externos adicionais.
- Modelos gratuitos podem não suportar ou respeitar tool calling de modo consistente. Para pedidos explícitos de leitura de arquivos, o fallback determinístico cobre os casos comuns.
- Não há ferramenta de execução arbitrária de comandos. Isso é intencional. O supervisor é instalado fora da raiz do agente para que o agente não possa alterar o próprio mecanismo de recuperação usando suas ferramentas normais.
- A inspeção automática inclui trechos limitados para caber em contextos pequenos; use `read_file` para arquivos específicos ou peça análises em etapas. Arquivos secretos como `.env` e chaves privadas permanecem bloqueados para leitura pelo modelo; arquivos binários podem ser preservados em checkpoints, mas não editados semanticamente pelas ferramentas de texto.
- O rollback restaura os arquivos que existem no checkpoint; ele não apaga automaticamente arquivos novos criados depois do checkpoint, para evitar perda acidental de dados. Ele não inventa uma correção de código: reverte para a versão conhecida como boa e reinicia.
- Testes locais não substituem execução na sua máquina e validação de dependências/API.
