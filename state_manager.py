"""Checkpoint SQLite com caminho estável relativo ao código do projeto."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "cerebro" / "estado.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
          timestamp TEXT NOT NULL, user_input TEXT NOT NULL,
          assistant_response TEXT NOT NULL, agent_name TEXT NOT NULL, context_json TEXT)""")


def salvar_checkpoint(session_id: str, user_input: str, assistant_response: str, agent_name: str = "menor_main", context: dict | None = None) -> bool:
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO checkpoints(session_id,timestamp,user_input,assistant_response,agent_name,context_json) VALUES(?,?,?,?,?,?)",
                (
                    session_id,
                    datetime.now().isoformat(timespec="seconds"),
                    user_input,
                    assistant_response,
                    agent_name,
                    json.dumps(context or {}, ensure_ascii=False),
                ),
            )
        return True
    except Exception as exc:
        print(f"[Checkpoint] Não foi possível salvar: {exc}")
        return False


def obter_ultimo_checkpoint(session_id: str = "menor_session") -> dict | None:
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT id,timestamp,user_input,assistant_response,agent_name,context_json FROM checkpoints WHERE session_id=? ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "timestamp": row[1],
            "user_input": row[2],
            "assistant_response": row[3],
            "agent_name": row[4],
            "context": json.loads(row[5] or "{}"),
        }
    except Exception:
        return None


def listar_checkpoints_recentes(session_id: str = "menor_session", limit: int = 4) -> list[dict]:
    """Retorna os últimos turnos salvos no SQLite em ordem cronológica para retomar contexto entre sessões."""
    try:
        init_db()
        limit = max(1, min(int(limit), 20))
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id,timestamp,user_input,assistant_response,agent_name,context_json "
                "FROM checkpoints WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        items = [
            {
                "id": r[0],
                "timestamp": r[1],
                "user_input": r[2],
                "assistant_response": r[3],
                "agent_name": r[4],
                "context": json.loads(r[5] or "{}"),
            }
            for r in rows
        ]
        items.reverse()
        return items
    except Exception:
        return []
