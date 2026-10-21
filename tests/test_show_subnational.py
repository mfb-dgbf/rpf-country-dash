"""SHOW_SUBNATIONAL removes the across-space (subnational) tab when false."""

import importlib
import os
import unittest
from unittest.mock import patch

import dash

import constants

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education, health, home  # noqa: E402


class BoolSettingTest(unittest.TestCase):
    def test_unset_or_empty_gives_default(self):
        for raw in (None, "", "  "):
            env = dict(os.environ)
            env.pop("SHOW_SUBNATIONAL", None)
            if raw is not None:
                env["SHOW_SUBNATIONAL"] = raw
            with self.subTest(raw=raw), patch.dict(os.environ, env, clear=True):
                self.assertTrue(constants.bool_setting("SHOW_SUBNATIONAL", True))
                self.assertFalse(constants.bool_setting("SHOW_SUBNATIONAL", False))

    def test_true_and_false_spellings(self):
        for raw, expected in (
            ("true", True), ("1", True), ("YES", True), ("on", True),
            ("false", False), ("0", False), ("No", False), (" OFF ", False),
        ):
            with self.subTest(raw=raw), patch.dict(os.environ, {"SHOW_SUBNATIONAL": raw}):
                self.assertEqual(constants.bool_setting("SHOW_SUBNATIONAL", True), expected)

    def test_invalid_value_stops_with_the_variable_name(self):
        with patch.dict(os.environ, {"SHOW_SUBNATIONAL": "maybe"}):
            with self.assertRaisesRegex(ValueError, "SHOW_SUBNATIONAL must be true or false"):
                constants.bool_setting("SHOW_SUBNATIONAL", True)


class AcrossSpaceTabTest(unittest.TestCase):
    PAGES = (
        (home, "update_overview_tab_labels", "overview-tab-space"),
        (education, "update_edu_tab_labels", "edu-tab-space"),
        (health, "update_health_tab_labels", "health-tab-space"),
    )

    def _tab_ids(self, module, callback_name):
        return [tab.tab_id for tab in getattr(module, callback_name)("en")]

    def _reload(self):
        importlib.reload(constants)
        for module, _, _ in self.PAGES:
            importlib.reload(module)

    def test_tab_shown_by_default_and_removed_when_disabled(self):
        try:
            with patch.dict(os.environ, {"SHOW_SUBNATIONAL": ""}):
                self._reload()
                for module, callback_name, tab_id in self.PAGES:
                    with self.subTest(page=module.__name__, shown=True):
                        self.assertIn(tab_id, self._tab_ids(module, callback_name))
            with patch.dict(os.environ, {"SHOW_SUBNATIONAL": "false"}):
                self._reload()
                for module, callback_name, tab_id in self.PAGES:
                    with self.subTest(page=module.__name__, shown=False):
                        tab_ids = self._tab_ids(module, callback_name)
                        self.assertNotIn(tab_id, tab_ids)
                        self.assertEqual(len(tab_ids), 1)  # the over-time tab stays
        finally:
            self._reload()


if __name__ == "__main__":
    unittest.main()
