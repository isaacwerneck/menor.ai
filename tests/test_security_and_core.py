"""Suíte de testes automatizados de segurança, integridade e contratos para o Guardian Supervisor."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

import file_ops
import assistant
import state_manager
import guardian_supervisor


class TestFileOpsSecurity(unittest.TestCase):
    def setUp(self):
        self.sandbox_dir = file_ops.PROJECT_ROOT / "cerebro" / "_test_sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.sample_py = self.sandbox_dir / "sample_mod.py"
        self.sample_py.write_text("def soma(a, b):\n    return a + b\n", encoding="utf-8")

    def tearDown(self):
        if self.sandbox_dir.exists():
            import shutil
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)

    def test_block_path_traversal(self):
        with self.assertRaises(file_ops.PathSecurityError):
            file_ops.resolve_project_path("../../etc/passwd")
        with self.assertRaises(file_ops.PathSecurityError):
            file_ops.resolve_project_path("../fora_do_projeto.txt")

    def test_block_absolute_external_paths(self):
        with self.assertRaises(file_ops.PathSecurityError):
            file_ops.resolve_project_path("C:/Windows/System32/drivers/etc/hosts")
        with self.assertRaises(file_ops.PathSecurityError):
            file_ops.resolve_project_path("/etc/shadow")

    def test_block_sensitive_files(self):
        res_read = file_ops.ler_arquivo(".env")
        self.assertFalse(res_read["ok"])
        res_write = file_ops.salvar_arquivo(".env.production", "SECRET=123")
        self.assertFalse(res_write["ok"])
        res_key = file_ops.salvar_arquivo("minha_chave.pem", "PRIVATE KEY")
        self.assertFalse(res_key["ok"])

    def test_reject_invalid_python_syntax_preserving_original(self):
        rel_path = self.sample_py.relative_to(file_ops.PROJECT_ROOT).as_posix()
        original = self.sample_py.read_text(encoding="utf-8")
        res = file_ops.salvar_arquivo(rel_path, "def quebrado(a, b\n    return a", backup=False)
        self.assertFalse(res["ok"])
        self.assertIn("Python inválido", res["error"])
        self.assertEqual(self.sample_py.read_text(encoding="utf-8"), original)

    def test_patch_file_surgical_edit(self):
        rel_path = self.sample_py.relative_to(file_ops.PROJECT_ROOT).as_posix()
        res = file_ops.editar_trecho_arquivo(
            rel_path,
            "return a + b",
            "return (a + b) * 2",
            backup=False,
        )
        self.assertTrue(res["ok"])
        self.assertIn("return (a + b) * 2", self.sample_py.read_text(encoding="utf-8"))

    def test_protect_core_files_from_trash(self):
        for core_file in ("assistant.py", "file_ops.py", "agents.yaml"):
            res = file_ops.mover_para_lixeira(core_file)
            self.assertFalse(res["ok"])


class TestAssistantContracts(unittest.TestCase):
    def test_call_name_args_handles_malformed_json(self):
        fake_call = {
            "id": "call_abc123",
            "function": {
                "name": "write_file",
                "arguments": '{"path": "teste.py", "content": "incompleto...',
            },
        }
        name, args, call_id = assistant._call_name_args(fake_call)
        self.assertEqual(name, "write_file")
        self.assertEqual(call_id, "call_abc123")
        self.assertIn("__json_error__", args)

        out = json.loads(assistant.execute_tool(name, args, confirm_fn=lambda *a: False))
        self.assertFalse(out["ok"])
        self.assertIn("JSON de argumentos malformado", out["error"])

    def test_trim_history_always_starts_with_user(self):
        history = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]},
            {"role": "tool", "tool_call_id": "1", "name": "list_files", "content": "{}"},
            {"role": "assistant", "content": "a1"},
        ]
        # Adiciona mensagens extras para forçar o corte
        for i in range(assistant.MAX_HISTORY_MESSAGES):
            history.append({"role": "tool" if i == 0 else "user", "content": f"msg_{i}"})
        assistant._trim_history(history)
        self.assertEqual(history[0]["role"], "system")
        self.assertEqual(history[1]["role"], "user")

    def test_checkpoint_roundtrip(self):
        ok = state_manager.salvar_checkpoint("test_unit_session", "oi", "olá", "menor_main", {"test": True})
        self.assertTrue(ok)
        last = state_manager.obter_ultimo_checkpoint("test_unit_session")
        self.assertIsNotNone(last)
        self.assertEqual(last["user_input"], "oi")
        recent = state_manager.listar_checkpoints_recentes("test_unit_session", limit=2)
        self.assertGreaterEqual(len(recent), 1)


if __name__ == "__main__":
    unittest.main()
