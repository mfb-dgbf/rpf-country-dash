"""Two different splits of spending, each with its own labels.

The time charts split spending by who executes it: the central government or
subnational governments (decentralized_expenditure). The donut and the
sub-function treemap split it by where it goes: allocated to a region or not
(geo0). The bars on the time charts are nominal amounts.
"""

import unittest

import dash
import pandas as pd

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from components import edu_health_across_space as space  # noqa: E402
from pages import education, health, home  # noqa: E402

YEARS = [2021, 2022]


def _sector():
    return pd.DataFrame({
        "country_name": "Togo", "year": YEARS,
        "expenditure": [150e9, 160e9], "central_expenditure": [150e9, 160e9],
        "decentralized_expenditure": [0.0, 0.0], "real_expenditure": [150e9, 150e9],
    })


def _bars(fig):
    return [trace for trace in fig.data if trace.type == "bar"]


class TimeChartLevelsTest(unittest.TestCase):
    def _figures(self, lang):
        national = pd.DataFrame({
            "country_name": "Togo", "year": YEARS, "expenditure": [1.0e12, 1.2e12],
            "decentralized_expenditure": [0.0, 0.0], "real_expenditure": [1.0e12, 1.1e12],
        })
        return {
            "overview": home.total_figure(national, "francs CFA", "XOF", lang=lang),
            "education": education.total_edu_figure(_sector(), "XOF", lang=lang),
            "health": health.total_health_figure(_sector(), "XOF", lang=lang),
        }

    def test_bars_name_the_level_of_government(self):
        expected = {
            "fr": ["Administration centrale", "Collectivités territoriales"],
            "en": ["Central government", "Subnational governments"],
            "pt": ["Governo central", "Governos subnacionais"],
        }
        for lang, names in expected.items():
            for chart, fig in self._figures(lang).items():
                with self.subTest(lang=lang, chart=chart):
                    self.assertEqual([bar.name for bar in _bars(fig)], names)

    def test_top_margin_holds_the_title_above_a_two_row_legend(self):
        # On a half-width chart « Collectivités territoriales », « Administration
        # centrale » and « Ajusté à l'inflation » take two legend rows.
        for chart, fig in self._figures("fr").items():
            with self.subTest(chart=chart):
                self.assertGreaterEqual(fig.layout.margin.t, 140)

    def test_bar_hovers_name_the_level_and_are_not_called_real(self):
        for chart, fig in self._figures("fr").items():
            with self.subTest(chart=chart):
                central, subnational = _bars(fig)
                self.assertIn("Dépenses de l'administration centrale", central.hovertemplate)
                self.assertIn("Dépenses des collectivités territoriales", subnational.hovertemplate)
                for bar in (central, subnational):
                    self.assertNotIn("réelles", bar.hovertemplate)


class GeographicSplitTest(unittest.TestCase):
    def _data(self):
        return pd.DataFrame({
            "func_sub": ["Primary education", "Primary education", "Tertiary education"],
            "geo0": ["Central", "Regional", "Regional"],
            "expenditure": [6e9, 87e9, 25e9],
            "real_expenditure": [6e9, 80e9, 23e9],
        })

    def test_donut_slices_say_whether_spending_is_allocated_to_a_region(self):
        fig = space._central_vs_regional_fig(self._data(), "Education", "XOF", lang="fr")
        self.assertEqual(list(fig.data[0].labels), ["Non allouées géographiquement", "Allouées géographiquement"])
        self.assertIn("%{label}", fig.data[0].hovertemplate)
        fig = space._central_vs_regional_fig(self._data(), "Education", "XOF", lang="en")
        self.assertEqual(list(fig.data[0].labels), ["Not geographically allocated", "Geographically allocated"])

    def test_donut_shares_share_one_precision(self):
        # Plotly's default writes 3 significant digits: 6,63 % beside 93,4 %.
        fig = space._central_vs_regional_fig(self._data(), "Education", "XOF", lang="fr")
        self.assertEqual(fig.data[0].texttemplate, "%{percent:.1%}")

    def test_treemap_boxes_use_the_same_labels(self):
        fig = space._sub_func_fig(self._data(), "Education", "XOF", lang="fr")
        children = [label for label, parent in zip(fig.data[0].labels, fig.data[0].parents) if parent]
        self.assertTrue(children)
        for label in children:
            self.assertTrue(label.startswith(("Allouées géographiquement", "Non allouées géographiquement")), label)


if __name__ == "__main__":
    unittest.main()
