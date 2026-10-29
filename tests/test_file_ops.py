"""Testes unitários para operações de arquivos do Menor.AI."""
from __future__ import annotations
import os
import unittest
from pathlib import Path

import file_ops


class FileOpsTests(unittest.TestCase):
    def test_read_existing_module(self):
        result = file_ops.ler_arquivo("assistant.py", max_chars=3000)
        self.assertTrue(result["ok"], f"Falha ao ler assistant.py: {result}")
        self.assertIn("SYSTEM_PROMPT", result["content"])

    def test_root_listing(self):
        result = file_ops.listar_arquivos(".", recursive=False)
        self.assertTrue(result["ok"])
        paths = [item["path"] for item in result["items"]]
        self.assertTrue(any("assistant.py" in p for p in paths))

    def test_sensitive_file_blocked(self):
        res = file_ops.ler_arquivo(".env")
        self.assertFalse(res["ok"])
        self.assertIn("bloqueada", res["error"].lower())

    def test_absolute_external_blocked(self):
        with self.assertRaises(file_ops.PathSecurityError):
            file_ops.resolve_project_path("C:/Windows/System32/drivers/etc/hosts")

    def test_traversal_blocked(self):
        with self.assertRaises(file_ops.PathSecurityError):
            file_ops.resolve_project_path("../../etc/passwd")

    def test_symlink_escape_blocked_when_supported(self):
        # Em Windows sem privilégios de admin, a criação de symlink pode falhar
        sandbox = file_ops.PROJECT_ROOT / "cerebro" / "_test_symlink"
        sandbox.mkdir(parents=True, exist_ok=True)
        link = sandbox / "symlink_test"
        try:
            os.symlink(file_ops.PROJECT_ROOT.parent, link)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable on this platform")
        try:
            with self.assertRaises(file_ops.PathSecurityError):
                file_ops.resolve_project_path(f"cerebro/_test_symlink/{link.name}/secret.txt")
        finally:
            if link.is_symlink() or link.exists():
                link.unlink(missing_ok=True)
            if sandbox.exists():
                import shutil
                shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
