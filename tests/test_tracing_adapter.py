from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import langfuse

from app import tracing


class TracingAdapterTests(unittest.TestCase):
    def test_adapter_uses_the_installed_langfuse_v3_api(self) -> None:
        self.assertEqual(tracing.observe.__module__, langfuse.observe.__module__)
        client = tracing.get_langfuse_client()
        self.assertTrue(callable(client.update_current_trace))
        self.assertTrue(callable(client.update_current_generation))

    def test_tracing_is_disabled_without_both_keys(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(tracing.tracing_enabled())

        with patch.dict(os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-only"}, clear=True):
            self.assertFalse(tracing.tracing_enabled())

    def test_score_and_flush_safe_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Must not raise exceptions
            tracing.score_trace("heuristic_quality", 0.85)
            tracing.flush_tracing()

    def test_dummy_client_supports_extended_sdk_methods(self) -> None:
        dummy = tracing._DummyClient()
        self.assertIsNone(dummy.update_current_trace())
        self.assertIsNone(dummy.update_current_generation())
        self.assertIsNone(dummy.update_current_span())
        self.assertIsNone(dummy.score(name="test", value=1.0))
        self.assertIsNone(dummy.create_score(name="test", value=1.0))
        self.assertIsNone(dummy.flush())
        self.assertIsNone(dummy.get_prompt("test"))



if __name__ == "__main__":
    unittest.main()
