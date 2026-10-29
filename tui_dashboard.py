"""Interface Rich opcional ligada ao agente real; exibe Diff colorido no Gatekeeper."""
from pathlib import Path
from assistant import respond, build_system_message, hydrate_history_from_db, CORE_FILES, confirmation
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.markdown import Markdown
    from rich.syntax import Syntax
except ImportError:
    Console = Panel = Prompt = Markdown = Syntax = None


def make_rich_confirm(console: "Console"):
    def _rich_confirm(action: str, target: str, preview: str = "") -> bool:
        header = f"[bold yellow]Ação:[/bold yellow] {action}\n[bold yellow]Destino:[/bold yellow] {target}"
        console.print(Panel(header, title="[bold red]Gatekeeper — Confirmação Necessária[/bold red]", border_style="red"))
        if preview:
            snippet = preview[:2000] + ("\n... [prévia truncada]" if len(preview) > 2000 else "")
            lexer = "diff" if (snippet.startswith("--- ") or snippet.startswith("@@")) else "python"
            if Syntax:
                console.print(Syntax(snippet, lexer, theme="monokai", line_numbers=False, word_wrap=True))
            else:
                console.print(snippet)
        try:
            ans = Prompt.ask("Confirmar? Digite [bold green]SIM[/bold green] para autorizar", default="NAO").strip()
            if ans != "SIM":
                return False
            if Path(target).name in CORE_FILES:
                core_ans = Prompt.ask(
                    "[bold red]Arquivo central da arquitetura![/bold red] Digite [bold red]ALTERAR CORE[/bold red] para confirmar",
                    default="NAO"
                ).strip()
                return core_ans == "ALTERAR CORE"
            return True
        except (EOFError, KeyboardInterrupt):
            return False
    return _rich_confirm


def main():
    history = [build_system_message()]
    if not Console:
        print("Instale rich com: pip install rich. Abrindo fallback simples.")
        while True:
            try:
                q = input("Você: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.casefold() in {"sair", "exit", "quit"}:
                break
            if not q:
                continue
            print("Menor:", respond(q, history, confirm_fn=confirmation))
        return

    console = Console()
    confirm_cb = make_rich_confirm(console)
    console.print(Panel("Menor.AI — painel conectado ao agente real (/retomar, /limpar, sair)", title="Menor.AI", border_style="cyan"))
    while True:
        try:
            q = Prompt.ask("[bold cyan]Você[/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.casefold() in {"sair", "exit", "quit"}:
            break
        if not q:
            continue
        if q == "/retomar":
            n = hydrate_history_from_db(history, limit=4)
            console.print(f"[dim][Sessão] {n} turno(s) restaurado(s) do SQLite.[/dim]")
            continue
        if q == "/limpar":
            history[:] = [build_system_message()]
            console.print("[dim][Sessão] Histórico reiniciado.[/dim]")
            continue
        answer = respond(q, history, confirm_fn=confirm_cb)
        console.print(Panel(Markdown(answer), title="Menor", border_style="green"))


if __name__ == "__main__":
    main()
