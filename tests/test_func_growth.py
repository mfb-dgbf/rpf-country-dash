"""Budget growth by function (overview, « Croissance des budgets par fonction »)."""

import unittest
from unittest.mock import patch

import pandas as pd

from components import budget_increment_analysis as bia
from constants import END_YEAR as E


def _by_function(funcs, years, grow=1.1):
    """Each function's budget from ``funcs``: (first budget, foreign share)
    or (first budget, foreign share, yearly growth factor, else ``grow``)."""
    rows = []
    for func, spec in funcs.items():
        base, foreign_share = spec[:2]
        factor = spec[2] if len(spec) > 2 else grow
        for k, year in enumerate(years):
            budget = base * factor ** k
            rows.append({
                "country_name": "Togo", "year": year, "func": func,
                "budget": budget, "real_budget": budget,
                "domestic_funded_budget": budget * (1 - foreign_share),
                "real_domestic_funded_budget": budget * (1 - foreign_share),
            })
    return pd.DataFrame(rows)


def _render(frame, lang="en"):
    with patch.object(bia.server_store, "get", side_effect={"func_by_country_year": frame}.__getitem__):
        return bia.render_fig_and_narrative(True, "Togo", "domestic_funded_budget", lang)


class FuncGrowthFigureTest(unittest.TestCase):
    def test_source_note_starts_inside_the_figure(self):
        df = pd.DataFrame({
            "func": ["Health", "Health"], "year": [2022, 2023],
            "yoy_domestic_funded_budget": [10.0, 12.0],
        })
        fig = bia.create_func_growth_figure(df, "domestic_funded_budget", lang="fr")
        note = fig.layout.annotations[0]
        # Left of x = 0 (paper) the note runs past the figure's left margin and is cut.
        self.assertEqual(note.x, 0)
        self.assertEqual(note.xanchor, "left")



class AverageGrowthTest(unittest.TestCase):
    def test_five_years_grow_over_four_intervals(self):
        # 10 % a year from the first to the fifth year is four years of growth:
        # 1.1 ** 4. Spread over five, the rate read 7.9 %.
        frame = _by_function({"Health": (100.0, 0.2), "Education": (200.0, 0.1)}, range(E - 4, E + 1))
        _, narrative = _render(frame)
        text = "".join(narrative)
        self.assertIn("Over the past 5 years, the national budget has grown at an average rate of 10.0% per year", text)
        self.assertIn("10.0%", text)
        self.assertNotIn("7.9%", text)

    def test_a_single_year_has_no_growth_to_report(self):
        frame = _by_function({"Health": (100.0, 0.2), "Education": (200.0, 0.1)}, [E])
        fig, narrative = _render(frame)
        self.assertEqual(narrative, bia.t("error.data_unavailable", "en"))



class ZeroExternalFundingTest(unittest.TestCase):
    """A function without external funding is all domestic, in a country
    whose data split other functions' budgets."""

    def _frame(self):
        import data_mapping
        frame = _by_function(
            {"Health": (100.0, 0.5), "Education": (200.0, 0.1), "Defence": (300.0, 0.0, 1.0)},
            range(E - 4, E + 1),
        )
        return data_mapping._add_real_funding_split_columns(frame)

    def test_its_domestic_budget_is_its_budget(self):
        frame = self._frame()
        defence = frame[frame["func"] == "Defence"]
        self.assertTrue((defence["foreign_funded_budget"] == 0).all())
        self.assertTrue((defence["domestic_funded_budget"] == defence["budget"]).all())

    def test_growth_chart_shows_it_and_counts_it_in_the_overall_budget(self):
        frame = self._frame()
        fig, _ = _render(frame)
        traces = {trace.name: trace for trace in fig.data}
        self.assertIn(bia.translate_func("Defence", "en"), traces)
        # Health and Education grow 10 % a year, Defence not at all: with it,
        # the overall domestic budget grows (55 + 198 + 300) / (50 + 180 + 300).
        overall = traces[bia.t("label.overall_budget", "en")]
        second_year = list(overall.x).index(E - 3)
        self.assertAlmostEqual(overall.y[second_year], (553 / 530 - 1) * 100)

    def test_a_country_without_any_split_keeps_the_unknown_sentinel(self):
        import data_mapping
        frame = _by_function({"Health": (100.0, 0.0), "Education": (200.0, 0.0)}, range(E - 1, E + 1))
        frame = data_mapping._add_real_funding_split_columns(frame)
        self.assertTrue(frame["foreign_funded_budget"].isna().all())


if __name__ == "__main__":
    unittest.main()
