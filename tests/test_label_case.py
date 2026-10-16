"""Sector names inside French and Portuguese titles are lowercase; legend
entries start with a capital."""

import unittest
from unittest.mock import patch

import dash
import pandas as pd

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education  # noqa: E402
from tests.test_amount_axes_charts import _sector_public  # noqa: E402
from tests.test_subnational_outcomes import E, _health_exact_year, _rows, _store, space  # noqa: E402


class SectorNameCaseTest(unittest.TestCase):
    def _map_title(self, func, lang):
        geo = _rows(func, [E - 1], lambda y: (0.6, y))
        get, lookup = _store(geo)
        with get, lookup:
            fig = space.update_func_expenditure_map(
                ["d"], ["d"], "Togo", E - 1, "per_capita_expenditure", ["d"], func, "light", lang=lang)
        return fig.layout.title.text

    def test_spending_map_titles(self):
        self.assertEqual(self._map_title("Education", "fr"), "Dépenses infranationales de l'éducation")
        self.assertEqual(self._map_title("Health", "fr"), "Dépenses infranationales de la santé")
        self.assertEqual(self._map_title("Health", "pt"), "Despesa subnacional da saúde")
        self.assertEqual(self._map_title("Education", "en"), "Subnational Education Spending")

    def test_ranking_header(self):
        for lang, header in (("fr", "Dépenses par habitant en santé"), ("pt", "Despesa per capita na saúde"),
                             ("en", "Per Capita Expenditure in Health")):
            with self.subTest(lang=lang):
                get, lookup = _store(_health_exact_year())
                with get, lookup:
                    fig, _ = space.render_func_subnat_rank(["d"], "Togo", E - 1, "Health", "XOF", lang=lang)
                self.assertIn(f"<b>{header}</b>", fig.layout.annotations[0].text)


class OutcomeLegendCaseTest(unittest.TestCase):
    def test_education_outcome_legend_entries_start_with_a_capital(self):
        store = {
            "hd_index": pd.DataFrame({"country_name": "Togo", "year": [2019, 2020], "adm1_name": "Total",
                                      "attendance_6to17yo": [0.8, 0.82]}),
            "learning_poverty": pd.DataFrame({"country_name": "Togo", "year": [2019], "learning_poverty_rate": [80.0]}),
            "edu_public_expenditure": _sector_public("edu"),
            "basic_country_info": {"Togo": {"currency_code": "XOF"}},
        }
        for lang in ("fr", "en", "pt"):
            with self.subTest(lang=lang):
                with patch.object(education.server_store, "get", side_effect=store.__getitem__):
                    fig, _, _ = education.render_education_outcome(["d"], ["d"], "Togo", {"Togo": {}}, lang)
                for trace in fig.data:
                    # "6-17yo attendance rate" starts with its age range.
                    self.assertTrue(trace.name[0].isupper() or trace.name[0].isdigit(), trace.name)


if __name__ == "__main__":
    unittest.main()
