"""The note beside the execution-rate/deviation toggle: both views, same data."""

import unittest

import dash

from components.budget_funding_execution import execution_metric_note
from translations import t

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education, health, home  # noqa: E402


def _texts(component):
    """Every string in a Dash component tree."""
    texts = []
    stack = [component]
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            texts.append(node)
        elif isinstance(node, (list, tuple)):
            stack.extend(node)
        elif node is not None and not isinstance(node, (int, float)):
            stack.append(getattr(node, "children", None))
    return texts


class ExecutionNoteTest(unittest.TestCase):
    def test_translated_in_every_language(self):
        notes = {lang: t("note.execution_deviation", lang) for lang in ("en", "fr", "pt")}
        self.assertEqual(len(set(notes.values())), 3)
        for lang, note in notes.items():
            with self.subTest(lang=lang):
                self.assertNotEqual(note, "note.execution_deviation")  # no fallback to the key

    def test_note_sits_beside_each_toggle(self):
        note = t("note.execution_deviation", "en")
        for page, render, tab in (
            ("home", home.render_overview_content, "overview-tab-time"),
            ("education", education.render_education_content, "edu-tab-time"),
            ("health", health.render_health_content, "health-tab-time"),
        ):
            with self.subTest(page=page):
                self.assertIn(note, _texts(render(tab, "en")))


if __name__ == "__main__":
    unittest.main()
