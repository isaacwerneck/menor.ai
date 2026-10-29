"""Supervisor de recuperação do Menor.AI.

INSTALAÇÃO: copie este arquivo para FORA da pasta do projeto, por exemplo:
Z:\menor.ai_guardian\supervisor.py
Depois rode: python Z:\menor.ai_guardian\supervisor.py --project Z:\menor.ai

O agente deve ficar confinado à raiz do projeto; não copie este supervisor para
uma pasta que o agente possa editar. Ele executa testes/sintaxe, mantém o último
checkpoint conhecido como bom e restaura os arquivos desse checkpoint após falha.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".menor_backups", ".lixeira", ".menor_runtime", "dist", "build"
}
EXCLUDED_NAMES = {".env"}  # preserva segredo local fora dos checkpoints
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def guardian_home(project: Path) -> Path:
    return project.parent / f".{project.name}_guardian"


def project_python(project: Path) -> str:
    """Prefere o Python do ambiente virtual do projeto quando existente."""
    candidates = [
        project / ".venv" / "Scripts" / "python.exe",
        project / "venv" / "Scripts" / "python.exe",
        project / ".venv" / "bin" / "python",
        project / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def iter_project_files(project: Path):
    for p in project.rglob("*"):
        try:
            rel = p.relative_to(project)
            if p.is_symlink() or any(part in EXCLUDED_DIRS for part in rel.parts):
                continue
            if not p.is_file() or p.name in EXCLUDED_NAMES or p.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            yield p, rel
        except OSError:
            continue


def create_snapshot(project: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path, rel in iter_project_files(project):
            zf.write(path, rel.as_posix())
    temp.replace(target)


def restore_snapshot(project: Path, snapshot: Path) -> int:
    """Restaura os arquivos contidos no checkpoint; não apaga dados novos."""
    count = 0
    with zipfile.ZipFile(snapshot, "r") as zf:
        for info in zf.infolist():
            rel = PurePosixPath(info.filename)
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise RuntimeError(f"Caminho inválido dentro do backup: {info.filename}")
            if any(part in EXCLUDED_DIRS for part in rel.parts) or rel.name in EXCLUDED_NAMES:
                continue
            dest = (project / Path(*rel.parts)).resolve()
            dest.relative_to(project.resolve())
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = dest.with_name(dest.name + ".menor_restore_tmp")
            with zf.open(info, "r") as src, temp.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            temp.replace(dest)
            count += 1
    return count


def validate_project(project: Path, timeout: int = 180) -> tuple[bool, str]:
    """Valida sintaxe de todo Python e executa unittest, se houver testes."""
    project = project.resolve()
    skip = EXCLUDED_DIRS
    py_files = []
    for p in project.rglob("*.py"):
        rel = p.relative_to(project)
        if any(part in skip for part in rel.parts) or p.is_symlink():
            continue
        py_files.append(p)
    if not py_files:
        return False, "Nenhum arquivo Python encontrado."
    python_exe = project_python(project)
    compile_cmd = [python_exe, "-m", "py_compile", *[str(p) for p in py_files]]
    compiled = subprocess.run(compile_cmd, cwd=project, capture_output=True, text=True, timeout=timeout)
    if compiled.returncode:
        return False, "Falha de sintaxe/compilação:\n" + (compiled.stderr or compiled.stdout)[-6000:]
    tests = project / "tests"
    if tests.is_dir():
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [python_exe, "-m", "unittest", "discover", "-s", str(tests), "-t", str(project), "-v"],
            cwd=project, env=env, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode:
            return False, "Testes falharam:\n" + (result.stdout + "\n" + result.stderr)[-10000:]
        return True, "Sintaxe válida e testes passaram.\n" + (result.stdout + result.stderr)[-4000:]
    return True, "Sintaxe Python válida; pasta tests/ não existe, portanto testes não foram executados."


def write_state(home: Path, data: dict) -> None:
    home.mkdir(parents=True, exist_ok=True)
    tmp = home / "state.json.tmp"
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(home / "state.json")


def supervise(project: Path, max_rollbacks: int = 1, check_only: bool = False, force_update_snapshot: bool = False) -> int:
    project = project.resolve()
    if not (project / "assistant.py").is_file():
        print(f"[Guardian] assistant.py não encontrado em {project}")
        return 2
    home = guardian_home(project)
    home.mkdir(parents=True, exist_ok=True)
    known_good = home / "known_good.zip"

    if check_only:
        ok, details = validate_project(project)
        print(f"[Guardian Check] {'Sucesso' if ok else 'Falha'}:\n{details}")
        return 0 if ok else 1

    if force_update_snapshot:
        ok, details = validate_project(project)
        if not ok:
            print(f"[Guardian] Não é possível atualizar checkpoint bom; validação falhou:\n{details}")
            return 1
        create_snapshot(project, known_good)
        print(f"[Guardian] Checkpoint conhecido como bom atualizado com sucesso: {known_good}")
        return 0

    rollback_count = 0

    while True:
        ok, details = validate_project(project)
        if not ok:
            print(f"[Guardian] Validação falhou antes da inicialização.\n{details}")
            if known_good.exists() and rollback_count < max_rollbacks:
                # Cria backup de quarentena do estado atual antes de sobrescrever com o rollback
                try:
                    quarantine = home / f"quarantine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    create_snapshot(project, quarantine)
                    print(f"[Guardian] Backup do estado atual salvo em quarentena: {quarantine.name}")
                except Exception:
                    pass
                n = restore_snapshot(project, known_good)
                rollback_count += 1
                print(f"[Guardian] BACKUP RESTAURADO ({n} arquivos). Reiniciando a versão conhecida como boa.")
                continue
            print("[Guardian] Sem backup válido disponível ou limite de restaurações atingido.")
            return 3

        if not known_good.exists():
            create_snapshot(project, known_good)
            print(f"[Guardian] Checkpoint inicial criado: {known_good}")

        write_state(home, {
            "project": str(project), "started_at": datetime.now().isoformat(timespec="seconds"),
            "known_good": str(known_good), "validation": details
        })
        print("[Guardian] Validação aprovada. Iniciando assistant.py...\n")
        try:
            proc = subprocess.run([project_python(project), str(project / "assistant.py")], cwd=project)
            code = proc.returncode
        except KeyboardInterrupt:
            print("\n[Guardian] Interrupção recebida; encerrando sem alterar backup.")
            return 130
        except Exception as exc:
            print(f"[Guardian] Não foi possível iniciar o Menor: {exc}")
            code = 1

        if code == 0:
            ok_after, details_after = validate_project(project)
            if ok_after:
                create_snapshot(project, known_good)
                write_state(home, {
                    "project": str(project), "last_clean_exit": datetime.now().isoformat(timespec="seconds"),
                    "known_good": str(known_good), "validation": details_after
                })
                print("[Guardian] Encerramento limpo; checkpoint conhecido como bom atualizado.")
                return 0
            print(f"[Guardian] O processo encerrou, mas a validação pós-execução falhou.\n{details_after}")

        if known_good.exists() and rollback_count < max_rollbacks:
            n = restore_snapshot(project, known_good)
            rollback_count += 1
            print(f"[Guardian] Falha detectada (código {code}). Backup restaurado ({n} arquivos). Reiniciando uma vez...")
            continue
        print(f"[Guardian] Processo terminou com código {code}; não será feito novo rollback automático.")
        return code or 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Supervisor de backup e recuperação do Menor.AI")
    parser.add_argument("--project", required=True, help="Caminho da pasta Menor.AI")
    parser.add_argument("--max-rollbacks", type=int, default=1)
    parser.add_argument("--check", action="store_true", help="Apenas valida testes e sintaxe sem iniciar o assistente")
    parser.add_argument("--update-snapshot", action="store_true", help="Valida e força a atualização do checkpoint conhecido como bom")
    args = parser.parse_args()
    return supervise(
        Path(args.project),
        max(0, min(args.max_rollbacks, 3)),
        check_only=args.check,
        force_update_snapshot=args.update_snapshot,
    )


if __name__ == "__main__":
    raise SystemExit(main())
