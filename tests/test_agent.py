"""Testes para intenções e contratos do assistente Menor.AI."""
from __future__ import annotations
import unittest
import assistant


class AgentIntentTests(unittest.TestCase):
    def test_generic_architecture_request_reads_real_files(self):
        msg = assistant.build_system_message()
        self.assertIn("role", msg)
        self.assertEqual(msg["role"], "system")
        self.assertIn("assistant.py", msg["content"])
        self.assertIn("file_ops.py", msg["content"])
        self.assertIn("inspeção real", msg["content"])

    def test_specific_file_request_reads_real_file(self):
        msg = assistant.build_system_message()
        self.assertIn("Para pedidos sobre um arquivo específico, leia-o", msg["content"])


if __name__ == "__main__":
    unittest.main()
