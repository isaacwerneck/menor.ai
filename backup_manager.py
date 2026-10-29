"""Backups de arquivos individuais e checkpoints do projeto Menor.AI.

O supervisor externo é a autoridade de recuperação; este módulo oferece apenas
utilitários locais para backups por arquivo e validação antes da gravação.
"""
from __future__ import annotations
import ast
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".menor_backups"


def get_backup_dir(target_path: Path | None = None) -> Path:
    """Retorna o diretório de backups, respeitando file_ops.PROJECT_ROOT se disponível."""
    try:
        import file_ops
        return file_ops.PROJECT_ROOT / ".menor_backups"
    except Exception:
        if target_path and target_path.parent.exists():
            return target_path.parent / ".menor_backups"
        return BACKUP_DIR


def backup_file(path: Path, backup_dir: Path | None = None) -> Path | None:
    """Cria backup de um arquivo existente antes de alterá-lo."""
    if not path.exists() or not path.is_file():
        return None
    dest_dir = backup_dir or get_backup_dir(path)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = dest_dir / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, target)
    return target


def validate_python(path: Path, content: str) -> None:
    """Recusa conteúdo Python com erro de sintaxe antes de tocar no arquivo."""
    if path.suffix.lower() == ".py":
        ast.parse(content, filename=str(path))
