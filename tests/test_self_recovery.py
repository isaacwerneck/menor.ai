"""Testes para recuperação e backups do Menor.AI."""
from __future__ import annotations
import shutil
import tempfile
import unittest
from pathlib import Path

import file_ops
import backup_manager
import guardian_supervisor


class SelfRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_root = file_ops.PROJECT_ROOT
        file_ops.PROJECT_ROOT = Path(self.temp_dir)
        self.sample = Path(self.temp_dir) / "module.py"
        self.sample.write_text("VALUE = 1\n", encoding="utf-8")

    def tearDown(self):
        file_ops.PROJECT_ROOT = self.orig_root
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_good_write_creates_per_file_backup(self):
        result = file_ops.salvar_arquivo("module.py", "VALUE = 2\n")
        self.assertTrue(result["ok"], f"Salvar falhou: {result}")
        self.assertTrue(result["backup_created"])
        self.assertIsNotNone(result["backup_path"])
        self.assertEqual(self.sample.read_text(encoding="utf-8"), "VALUE = 2\n")

    def test_invalid_python_write_preserves_original(self):
        original = self.sample.read_text(encoding="utf-8")
        result = file_ops.salvar_arquivo("module.py", "def syntax_error(:\n", backup=True)
        self.assertFalse(result["ok"])
        self.assertIn("Python inválido", result["error"])
        self.assertEqual(self.sample.read_text(encoding="utf-8"), original)

    def test_guardian_restores_known_good_snapshot(self):
        proj_dir = Path(self.temp_dir) / "subproject"
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "assistant.py").write_text("print('hello')", encoding="utf-8")
        snapshot = Path(self.temp_dir) / "snapshot.zip"
        guardian_supervisor.create_snapshot(proj_dir, snapshot)
        self.assertTrue(snapshot.exists())
        # Modifica arquivo
        (proj_dir / "assistant.py").write_text("corrompido", encoding="utf-8")
        restored = guardian_supervisor.restore_snapshot(proj_dir, snapshot)
        self.assertGreater(restored, 0)
        self.assertEqual((proj_dir / "assistant.py").read_text(encoding="utf-8"), "print('hello')")


if __name__ == "__main__":
    unittest.main()
