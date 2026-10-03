import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from ai_smart_context.config import read_gemini_config
from ai_smart_context import ProviderError


class ConfigTests(unittest.TestCase):
    def read_fixture(self, contents):
        with patch("ai_smart_context.config.Path.is_file", return_value=True), patch("ai_smart_context.config.Path.stat", return_value=SimpleNamespace(st_size=200)), patch("ai_smart_context.config.Path.read_text", return_value=contents):
            return read_gemini_config("test-config.env")

    def test_file_and_quotes(self):
        with patch.dict(os.environ, {}, clear=True):
            before = dict(os.environ)
            result = self.read_fixture('# local\nGEMINI_API_KEY="test-only"\nGEMINI_MODEL=test-model\n')
            self.assertEqual(result["GEMINI_API_KEY"], "test-only")
            self.assertEqual(result["GEMINI_MODEL"], "test-model")
            self.assertEqual(dict(os.environ), before)

    def test_environment_priority(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "env-model"}, clear=True):
            self.assertEqual(self.read_fixture("GEMINI_MODEL=file-model\n")["GEMINI_MODEL"], "env-model")

    def test_no_secret_in_errors(self):
        for line in ("secret-test-only", "UNSUPPORTED=secret-test-only", 'GEMINI_API_KEY="secret-test-only'):
            with self.subTest(case=line.split("=")[0]):
                with self.assertRaises(ProviderError) as error:
                    self.read_fixture(line)
                self.assertNotIn("secret-test-only", str(error.exception))

    def test_missing_file(self):
        with patch("ai_smart_context.config.Path.is_file", return_value=False), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(read_gemini_config("missing.env")["GEMINI_API_KEY"], "")
