"""Operações de arquivos confinadas ao diretório do projeto Menor.AI."""
from __future__ import annotations
import difflib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import backup_manager

PROJECT_ROOT = Path(__file__).resolve().parent
BRAIN_DIR = PROJECT_ROOT / "cerebro"
MAX_READ_BYTES = 250_000
TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".conf", ".properties", ".csv", ".tsv", ".html", ".htm", ".css", ".scss",
    ".sass", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte",
    ".sql", ".ps1", ".bat", ".cmd", ".sh", ".bash", ".zsh", ".xml", ".xsd",
    ".xsl", ".svg", ".graphql", ".gql", ".go", ".rs", ".java", ".kt", ".kts",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".php", ".rb", ".pl", ".lua",
    ".r", ".R", ".swift", ".dart", ".dockerfile", ".makefile", ".log", ".env.example"
}
SENSITIVE_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
TEXT_FILENAMES = {
    "dockerfile", "makefile", "procfile", "license", ".gitignore",
    ".dockerignore", ".editorconfig", ".prettierrc", ".eslintrc",
    ".gitattributes", ".npmrc.example"
}
CORE_PROTECTED_FILES = {
    "assistant.py", "file_ops.py", "middleware.py", "mcp_server.py",
    "state_manager.py", "backup_manager.py", "guardian_supervisor.py",
    "voice_assistant.py", "tui_dashboard.py", "agents.yaml"
}


class PathSecurityError(PermissionError):
    pass


def safe_rel_path(p: Path | None, root: Path | None = None) -> str | None:
    """Converte caminho para formato relativo POSIX de forma segura, sem falhar caso esteja fora ou em outro drive."""
    if p is None:
        return None
    base = root or PROJECT_ROOT
    try:
        return p.resolve().relative_to(base.resolve()).as_posix()
    except Exception:
        return p.as_posix()


def resolve_project_path(raw_path: str, *, allow_root: bool = False) -> Path:
    """Resolve path and reject traversal/symlinks escaping the project root."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("Informe um caminho relativo válido.")
    raw = raw_path.strip().replace("\\", "/")
    candidate = Path(raw)
    root_text = str(PROJECT_ROOT).replace("\\", "/").rstrip("/")
    if raw == root_text:
        target = PROJECT_ROOT
    elif raw.startswith(root_text + "/"):
        target = PROJECT_ROOT / raw[len(root_text) + 1:]
    elif candidate.is_absolute() or re.match(r"^[A-Za-z]:", raw):
        raise PathSecurityError("Caminhos absolutos externos não são permitidos; use caminho relativo ao projeto.")
    else:
        target = PROJECT_ROOT / raw
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        raise PathSecurityError("Acesso bloqueado: o caminho sai da pasta autorizada do projeto.")
    if not allow_root and resolved == PROJECT_ROOT:
        raise PathSecurityError("A operação não pode ser executada na raiz inteira do projeto.")
    probe = resolved
    while probe != PROJECT_ROOT:
        if probe.exists() and probe.is_symlink():
            try:
                probe.resolve().relative_to(PROJECT_ROOT)
            except ValueError:
                raise PathSecurityError("Acesso bloqueado: link simbólico aponta para fora do projeto.")
        probe = probe.parent
    return resolved


def _is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    return (
        name in SENSITIVE_NAMES
        or (name.startswith(".env") and name != ".env.example")
        or name.endswith((".pem", ".key", ".p12", ".pfx", ".secret"))
    )


def gerar_diff_preview(caminho: str, novo_conteudo: str, *, append: bool = False, max_chars: int = 2000) -> str:
    """Gera um unified diff limpo se o arquivo já existir, ou mostra o conteúdo novo se for criação."""
    try:
        path = resolve_project_path(caminho)
        if not path.exists() or not path.is_file():
            header = f"[NOVO ARQUIVO: {path.relative_to(PROJECT_ROOT).as_posix()}]\n"
            body = novo_conteudo[:max_chars]
            if len(novo_conteudo) > max_chars:
                body += "\n... [prévia truncada]"
            return header + body
        atual = path.read_text(encoding="utf-8", errors="replace")
        final = (atual + novo_conteudo) if append else novo_conteudo
        if atual == final:
            return "[Sem alterações em relação ao arquivo atual]"
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        diff_lines = list(difflib.unified_diff(
            atual.splitlines(keepends=True),
            final.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            n=3,
        ))
        diff_text = "".join(diff_lines)
        if len(diff_text) > max_chars:
            return diff_text[:max_chars] + "\n... [diff truncado]"
        return diff_text
    except Exception:
        return novo_conteudo[:max_chars]


def listar_arquivos(caminho: str = ".", recursive: bool = True, max_items: int = 200) -> dict:
    folder = resolve_project_path(caminho, allow_root=True)
    if not folder.exists() or not folder.is_dir():
        return {"ok": False, "error": f"Pasta não encontrada: {caminho}"}
    items = []
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    ignored = {
        ".git", ".venv", "venv", "__pycache__", "node_modules", ".idea",
        ".pytest_cache", ".menor_backups", ".lixeira", ".menor_runtime"
    }
    for p in iterator:
        try:
            rel = p.relative_to(PROJECT_ROOT)
            if any(part in ignored for part in rel.parts) or _is_sensitive(p):
                continue
            if p.is_symlink():
                continue
            items.append({"path": rel.as_posix(), "type": "dir" if p.is_dir() else "file"})
            if len(items) >= max(1, min(max_items, 1000)):
                break
        except (OSError, ValueError):
            continue
    return {"ok": True, "root": str(PROJECT_ROOT), "items": items, "truncated": len(items) >= max_items}


def ler_arquivo(caminho: str, max_chars: int = 30000) -> dict:
    path = resolve_project_path(caminho)
    if _is_sensitive(path):
        return {"ok": False, "error": "Leitura de arquivo potencialmente secreto bloqueada."}
    if not path.is_file():
        return {"ok": False, "error": f"Arquivo não encontrado: {caminho}"}
    if path.stat().st_size > MAX_READ_BYTES:
        return {"ok": False, "error": f"Arquivo grande demais ({path.stat().st_size} bytes). Limite: {MAX_READ_BYTES}."}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"ok": False, "error": "Arquivo não parece ser texto UTF-8; leitura bloqueada."}
    max_chars = max(100, min(int(max_chars), 50000))
    return {
        "ok": True,
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
        "characters": len(text),
    }


def pesquisar_arquivos(query: str, caminho: str = ".", max_results: int = 30) -> dict:
    if not query or len(query) > 300:
        return {"ok": False, "error": "A pesquisa deve ter entre 1 e 300 caracteres."}
    root = resolve_project_path(caminho, allow_root=True)
    if not root.is_dir():
        return {"ok": False, "error": "Pasta não encontrada."}
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", ".menor_backups", ".lixeira"}
    found, needle = [], query.casefold()
    for p in root.rglob("*"):
        if (
            not p.is_file()
            or p.is_symlink()
            or (p.suffix.lower() not in TEXT_EXTENSIONS and p.name.lower() not in TEXT_FILENAMES)
            or _is_sensitive(p)
        ):
            continue
        try:
            rel = p.relative_to(PROJECT_ROOT)
            if any(part in ignored for part in rel.parts) or p.stat().st_size > MAX_READ_BYTES:
                continue
            for number, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if needle in line.casefold():
                    found.append({"path": rel.as_posix(), "line": number, "text": line[:300]})
                    if len(found) >= max(1, min(max_results, 100)):
                        return {"ok": True, "results": found, "truncated": True}
        except (OSError, ValueError):
            continue
    return {"ok": True, "results": found, "truncated": False}


def salvar_arquivo(caminho: str, conteudo: str, *, append: bool = False, backup: bool = True) -> dict:
    """Salva texto atomicamente; usa backup_manager para validar Python e criar backup antes da troca."""
    path = resolve_project_path(caminho)
    if _is_sensitive(path):
        return {"ok": False, "error": "Escrita em arquivo potencialmente secreto bloqueada."}
    if not isinstance(conteudo, str) or len(conteudo.encode("utf-8")) > 1_000_000:
        return {"ok": False, "error": "Conteúdo inválido ou maior que 1 MB."}
    if (
        path.suffix.lower() not in TEXT_EXTENSIONS
        and path.name.lower() not in TEXT_FILENAMES
        and path.name.lower() != ".env.example"
    ):
        return {"ok": False, "error": f"Formato não textual ou extensão não autorizada para escrita: {path.suffix or path.name}"}
    if path.exists() and path.is_dir():
        return {"ok": False, "error": "O destino é uma pasta."}
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        old_content = path.read_text(encoding="utf-8") if path.exists() else ""
        final_content = (old_content + conteudo) if append else conteudo
        try:
            backup_manager.validate_python(path, final_content)
        except SyntaxError as exc:
            return {
                "ok": False,
                "error": f"Alteração recusada: Python inválido ({exc.msg}, linha {exc.lineno}). O arquivo original foi preservado.",
            }

        backup_path = backup_manager.backup_file(path, backup_dir=PROJECT_ROOT / ".menor_backups") if (path.exists() and backup) else None

        temp_path = path.with_name(path.name + ".menor_write_tmp")
        with temp_path.open("w", encoding="utf-8", newline="") as f:
            f.write(final_content)
            f.flush()
            os.fsync(f.fileno())
        temp_path.replace(path)
        return {
            "ok": True,
            "path": safe_rel_path(path, PROJECT_ROOT),
            "bytes_written": len(final_content.encode("utf-8")),
            "backup_created": backup_path is not None,
            "backup_path": safe_rel_path(backup_path, PROJECT_ROOT),
            "validated_python": path.suffix.lower() == ".py",
        }
    except (OSError, UnicodeDecodeError) as e:
        return {"ok": False, "error": f"Falha ao salvar: {e}"}


def editar_trecho_arquivo(
    caminho: str,
    trecho_antigo: str,
    trecho_novo: str,
    *,
    substituir_todos: bool = False,
    backup: bool = True,
) -> dict:
    """Edição cirúrgica (search & replace) que evita que modelos menores precisem reescrever o arquivo inteiro."""
    path = resolve_project_path(caminho)
    if _is_sensitive(path):
        return {"ok": False, "error": "Edição em arquivo potencialmente secreto bloqueada."}
    if not path.is_file():
        return {"ok": False, "error": f"Arquivo não encontrado para edição: {caminho}"}
    if not trecho_antigo:
        return {"ok": False, "error": "O parâmetro 'old_text' não pode ser vazio."}
    try:
        atual = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"ok": False, "error": "Arquivo não é texto UTF-8 válido."}

    ocorrencias = atual.count(trecho_antigo)
    if ocorrencias == 0:
        return {
            "ok": False,
            "error": "Trecho original ('old_text') não encontrado exatamente no arquivo. Use read_file para conferir linhas exatas.",
        }
    if ocorrencias > 1 and not substituir_todos:
        return {
            "ok": False,
            "error": f"O trecho aparece {ocorrencias} vezes no arquivo. Inclua mais linhas de contexto em 'old_text' ou defina replace_all=True.",
        }

    novo_conteudo = atual.replace(trecho_antigo, trecho_novo) if substituir_todos else atual.replace(trecho_antigo, trecho_novo, 1)
    res = salvar_arquivo(caminho, novo_conteudo, append=False, backup=backup)
    if res.get("ok"):
        res["replacements"] = ocorrencias if substituir_todos else 1
    return res


def criar_pasta(caminho: str) -> dict:
    path = resolve_project_path(caminho)
    path.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": path.relative_to(PROJECT_ROOT).as_posix()}


def mover_para_lixeira(caminho: str) -> dict:
    path = resolve_project_path(caminho)
    if not path.exists():
        return {"ok": False, "error": "O item não existe."}
    if (
        path.name in CORE_PROTECTED_FILES
        or path == BRAIN_DIR
        or path.name in {".menor_backups", "tools", "tests"}
    ):
        return {"ok": False, "error": "Exclusão desses módulos/pastas centrais está bloqueada; mova manualmente após backup."}
    # Impede apagar uma pasta pai que contenha módulos centrais ou cerebro
    if path.is_dir():
        for child in path.rglob("*"):
            if child.name in CORE_PROTECTED_FILES or child == BRAIN_DIR:
                return {"ok": False, "error": "A pasta contém arquivos centrais protegidos e não pode ser movida para a lixeira."}
    trash = PROJECT_ROOT / "cerebro" / ".lixeira"
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / f"{path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    shutil.move(str(path), str(target))
    return {
        "ok": True,
        "original": path.relative_to(PROJECT_ROOT).as_posix(),
        "trash_path": target.relative_to(PROJECT_ROOT).as_posix(),
    }


def gerar_nota_obsidian(titulo: str, categoria: str, subpasta: str | None, conteudo_bruto: str) -> str:
    title = titulo.replace("_", " ").replace('"', "'").strip().title()
    tags = [categoria] + ([subpasta] if subpasta else [])
    tags_yaml = "\n".join("  - " + re.sub(r"[^\w/-]", "", tag) for tag in tags)
    return (
        f'---\ntitle: "{title}"\ndate: "{datetime.now():%Y-%m-%d %H:%M}"\n'
        f'category: "{categoria}"\ntags:\n{tags_yaml}\nauthor: "Menor.AI"\n---\n\n'
        f"# {title}\n\n{conteudo_bruto.strip()}\n"
    )


def criar_arquivo(caminho: str, conteudo: str = ""):
    result = salvar_arquivo(caminho, conteudo, backup=True)
    return result.get("ok", False), result.get("path", result.get("error", "Erro"))


def ler_arquivo_legacy(caminho: str):
    result = ler_arquivo(caminho)
    return result.get("ok", False), result.get("content", result.get("error", "Erro"))
