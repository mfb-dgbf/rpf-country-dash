"""SHOW_NARRATIVE_INTERPRETATION gates the "This might suggest…" sentences."""

import importlib
import os
import unittest
from unittest.mock import patch

import constants
from components import budget_increment_analysis
from translations import t

DATA = {"Overall budget": 14.3, "highest": ("Social protection", 49.8), "lowest": ("Economic affairs", 4.1)}
DATA_OUTPACED = {"Overall budget": 14.3, "highest": ("Social protection", 2.0), "lowest": ("Economic affairs", 10.0)}


def _narrative(data):
    return budget_increment_analysis.format_budget_increment_narrative(
        data, foreign_funding_isnull=False, exp_type="budget", num_years=5, lang="en"
    )[0]


class NarrativeInterpretationTest(unittest.TestCase):
    def _reload(self):
        importlib.reload(constants)
        importlib.reload(budget_increment_analysis)

    def test_interpretation_translated_in_every_language(self):
        for key in ("narrative.high_expanded_interpretation", "narrative.low_outpacing_interpretation"):
            for lang in ("en", "fr", "pt"):
                with self.subTest(key=key, lang=lang):
                    self.assertNotEqual(t(key, lang, high="X"), key)  # no fallback to the key

    def test_hidden_by_default_on_this_branch(self):
        env = dict(os.environ)
        env.pop("SHOW_NARRATIVE_INTERPRETATION", None)
        try:
            with patch.dict(os.environ, env, clear=True):
                self._reload()
                for data in (DATA, DATA_OUTPACED):
                    narrative = _narrative(data)
                    self.assertNotIn("suggest", narrative)
                    self.assertIn("category", narrative)  # the factual clause stays
        finally:
            self._reload()

    def test_shown_when_enabled(self):
        try:
            with patch.dict(os.environ, {"SHOW_NARRATIVE_INTERPRETATION": "true"}):
                self._reload()
                self.assertIn("This might suggest a policy shift", _narrative(DATA))
                self.assertIn("This suggests a greater focus", _narrative(DATA_OUTPACED))
        finally:
            self._reload()


if __name__ == "__main__":
    unittest.main()
