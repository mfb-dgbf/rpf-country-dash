"""HIDDEN_CHARTS removes a chart's whole section; education-outcome is hidden here."""

import importlib
import os
import unittest
from unittest.mock import patch

import dash

import constants

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education  # noqa: E402


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

    def test_education_outcome_is_hidden_on_this_branch(self):
        self.assertIn("education-outcome", constants.HIDDEN_CHARTS)


class EducationOutcomeSectionTest(unittest.TestCase):
    OUTCOME_IDS = {"education-outcome", "education-outcome-measure", "education-outcome-narrative"}

    def _reload(self):
        importlib.reload(constants)
        importlib.reload(education)

    def _time_tab_ids(self):
        return component_ids(education.render_education_content("edu-tab-time", "en"))

    def test_section_follows_the_setting(self):
        try:
            with patch.dict(os.environ, {"HIDDEN_CHARTS": "education-outcome"}):
                self._reload()
                self.assertFalse(self.OUTCOME_IDS & self._time_tab_ids())
            with patch.dict(os.environ, {"HIDDEN_CHARTS": ""}):
                self._reload()
                ids = self._time_tab_ids()
                self.assertTrue(self.OUTCOME_IDS <= ids)
                # the rest of the tab is untouched either way
                self.assertIn("education-total", ids)
        finally:
            self._reload()


if __name__ == "__main__":
    unittest.main()
