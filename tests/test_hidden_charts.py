"""HIDDEN_CHARTS removes a chart's whole section; the education and health
outcome charts are hidden on this branch."""

import importlib
import os
import unittest
from unittest.mock import patch

import dash

import constants

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education, health  # noqa: E402


def component_ids(component):
    """Every string id in a Dash component tree."""
    ids = set()
    stack = [component]
    while stack:
        node = stack.pop()
        if node is None or isinstance(node, (str, int, float)):
            continue
        if isinstance(node, (list, tuple)):
            stack.extend(node)
            continue
        if isinstance(getattr(node, "id", None), str):
            ids.add(node.id)
        stack.append(getattr(node, "children", None))
    return ids


class HiddenChartsSettingTest(unittest.TestCase):
    def test_unset_gives_default(self):
        env = dict(os.environ)
        env.pop("HIDDEN_CHARTS", None)
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                constants.hidden_charts_setting({"education-outcome"}),
                frozenset({"education-outcome"}),
            )

    def test_empty_hides_nothing(self):
        with patch.dict(os.environ, {"HIDDEN_CHARTS": ""}):
            self.assertEqual(constants.hidden_charts_setting({"education-outcome"}), frozenset())

    def test_comma_separated_ids_are_read(self):
        with patch.dict(os.environ, {"HIDDEN_CHARTS": " education-outcome , health-outcome "}):
            self.assertEqual(
                constants.hidden_charts_setting(set()),
                frozenset({"education-outcome", "health-outcome"}),
            )

    def test_outcome_charts_are_hidden_on_this_branch(self):
        self.assertIn("education-outcome", constants.HIDDEN_CHARTS)
        self.assertIn("health-outcome", constants.HIDDEN_CHARTS)


class OutcomeSectionTest(unittest.TestCase):
    PAGES = (
        (education, "render_education_content", "edu-tab-time", "education"),
        (health, "render_health_content", "health-tab-time", "health"),
    )

    def _reload(self):
        importlib.reload(constants)
        for module, _, _, _ in self.PAGES:
            importlib.reload(module)

    def test_section_follows_the_setting(self):
        try:
            with patch.dict(os.environ, {"HIDDEN_CHARTS": "education-outcome,health-outcome"}):
                self._reload()
                for module, render, tab, chart in self.PAGES:
                    with self.subTest(page=chart, hidden=True):
                        ids = component_ids(getattr(module, render)(tab, "en"))
                        self.assertFalse({f"{chart}-outcome", f"{chart}-outcome-narrative"} & ids)
            with patch.dict(os.environ, {"HIDDEN_CHARTS": ""}):
                self._reload()
                for module, render, tab, chart in self.PAGES:
                    with self.subTest(page=chart, hidden=False):
                        ids = component_ids(getattr(module, render)(tab, "en"))
                        self.assertIn(f"{chart}-outcome", ids)
                        self.assertIn(f"{chart}-outcome-narrative", ids)
                        # the rest of the tab is untouched either way
                        self.assertIn(f"{chart}-total", ids)
        finally:
            self._reload()


if __name__ == "__main__":
    unittest.main()
