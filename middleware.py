"""Middleware leve: pesquisa web opcional e checkpoints, sem executar comandos."""
from __future__ import annotations
import state_manager
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


def pesquisar_web(query: str, max_resultados: int = 5) -> str:
    if DDGS is None:
        return "Pesquisa web indisponível: instale a dependência 'ddgs'."
    query = (query or "").strip()[:500]
    if not query:
        return "Consulta de pesquisa vazia."
    try:
        rows = list(DDGS().text(query, max_results=max(1, min(max_resultados, 8))))
        if not rows:
            return "Nenhum resultado encontrado."
        return "\n".join(f"- {r.get('title','Sem título')} — {r.get('body','')} (Fonte: {r.get('href','')})" for r in rows)
    except Exception as exc:
        return f"Pesquisa web falhou: {type(exc).__name__}: {exc}"


class MiddlewareManager:
    def __init__(self, session_id: str = "menor_session"):
        self.session_id = session_id

    def pre_execute(self, user_input: str, agent_spec: dict | None = None):
        return user_input, None, False

    def post_execute(self, user_input: str, response_text: str, agent_name: str = "menor_main", context: dict | None = None) -> bool:
        return state_manager.salvar_checkpoint(self.session_id, user_input, response_text, agent_name, context)
