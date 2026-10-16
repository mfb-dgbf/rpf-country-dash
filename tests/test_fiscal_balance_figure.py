"""The fiscal balance chart (overview, « Solde budgétaire »)."""

import unittest

import pandas as pd

from components.fiscal_balance import _clean_rev_exp, combined_figure
from tests.fiscal_balance_fixture import DGBF_EXPENDITURE, DGBF_REVENUE, DGBF_YEARS, dgbf_file_rows


def _composite():
    national = pd.DataFrame({
        "year": [2023, 2024],
        "revenue": [1.0e12, 1.1e12],
        "expenditure": [1.3e12, 1.45e12],
        "source": "Togo DGB Budget Execution Report",
    })
    weo = pd.DataFrame({
        "year": [2025, 2026, 2027],
        "revenue": [1.2e12, 1.3e12, 1.4e12],
        "expenditure": [1.5e12, 1.8e12, 2.1e12],
        "is_forecast": [False, True, True],
    })
    return combined_figure(national, None, weo, "XOF", "francs CFA", view_mode="composite", lang="fr")


class ForecastLabelTest(unittest.TestCase):
    def test_lines_stay_below_the_forecast_label(self):
        fig = _composite()
        label = next(a for a in fig.layout.annotations if a.text == "prévision")
        self.assertEqual((label.yref, label.yanchor), ("paper", "top"))
        low, high = fig.layout.yaxis.range
        top_line = 2100.0  # 2.1e12 XOF, drawn in milliards
        # The label hangs from the top of the upper panel; the lines leave it
        # the top sixth of the panel.
        self.assertGreaterEqual(high - top_line, (high - low) / 6)

    def test_no_band_no_headroom(self):
        national = pd.DataFrame({
            "year": [2023, 2024], "revenue": [1.0e12, 1.1e12], "expenditure": [1.3e12, 1.45e12],
            "source": "Togo DGB Budget Execution Report",
        })
        fig = combined_figure(national, None, None, "XOF", "francs CFA", view_mode="official", lang="fr")
        self.assertIsNone(fig.layout.yaxis.range)


class TaxExpenditureTest(unittest.TestCase):
    def test_a_year_without_tax_expenditure_keeps_every_year_as_published(self):
        d = _clean_rev_exp(dgbf_file_rows())
        self.assertEqual(d["year"].tolist(), DGBF_YEARS)
        self.assertEqual(d["revenue"].tolist(), DGBF_REVENUE)
        self.assertEqual(d["expenditure"].tolist(), DGBF_EXPENDITURE)
        self.assertEqual(
            d["balance"].tolist(),
            [r - e for r, e in zip(DGBF_REVENUE, DGBF_EXPENDITURE)],
        )

    def test_tax_expenditure_on_every_year_is_subtracted_from_both_sides(self):
        rows = dgbf_file_rows().iloc[:4]
        d = _clean_rev_exp(rows)
        tax = [84.15e9, 76.06e9, 135.80e9, 160.34e9]
        self.assertEqual(d["year"].tolist(), DGBF_YEARS[:4])
        self.assertEqual(d["revenue"].tolist(), [r - x for r, x in zip(DGBF_REVENUE, tax)])
        self.assertEqual(d["expenditure"].tolist(), [e - x for e, x in zip(DGBF_EXPENDITURE, tax)])
        self.assertEqual(
            d["balance"].tolist(),
            [(r - x) - (e - x) for r, e, x in zip(DGBF_REVENUE, DGBF_EXPENDITURE, tax)],
        )

    def test_official_view_draws_2019_to_2025(self):
        fig = combined_figure(dgbf_file_rows(), None, None, "XOF", "francs CFA", view_mode="official", lang="fr")
        revenue = next(tr for tr in fig.data if tr.name == "Recettes")
        self.assertEqual(list(revenue.x), DGBF_YEARS)
        # Drawn in milliards: scale_currency_axes divides the amounts by 10**9.
        self.assertEqual([round(v, 2) for v in revenue.y], [round(v / 1e9, 2) for v in DGBF_REVENUE])


class DefaultViewTest(unittest.TestCase):
    """Without a selected view the figure draws the country's default view."""

    def _weo(self):
        return pd.DataFrame({
            "year": [2024, 2025, 2026],
            "revenue": [1.2e12, 1.3e12, 1.4e12],
            "expenditure": [1.5e12, 1.8e12, 2.1e12],
            "is_forecast": [False, True, True],
        })

    def test_togo_with_official_rows_draws_the_official_report_only(self):
        fig = combined_figure(dgbf_file_rows(), None, self._weo(), "XOF", "francs CFA",
                              view_mode=None, lang="fr", country="Togo")
        years = sorted({int(x) for tr in fig.data for x in tr.x})
        self.assertEqual(years, DGBF_YEARS)
        self.assertNotIn("prévision", [a.text for a in fig.layout.annotations])

    def test_without_official_rows_draws_weo(self):
        fig = combined_figure(None, None, self._weo(), "XOF", "francs CFA",
                              view_mode=None, lang="fr", country="Togo")
        years = sorted({int(x) for tr in fig.data for x in tr.x})
        self.assertEqual(years, [2024, 2025, 2026])


if __name__ == "__main__":
    unittest.main()
