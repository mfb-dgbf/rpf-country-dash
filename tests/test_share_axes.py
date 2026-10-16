"""Axes that plot shares of a total from 0 to 100 print the percent sign."""

import unittest

import dash
import pandas as pd

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from components.func_operational_vs_capital_spending import _generate_econ_figure  # noqa: E402
from pages import home  # noqa: E402


class ShareAxesTest(unittest.TestCase):
    def test_functional_breakdown(self):
        df = pd.DataFrame({
            "year": [2021, 2021], "func": ["Health", "Education"], "percentage": [40.0, 60.0],
            "expenditure_formatted": ["", ""],
        })
        fig = home.functional_figure(df, lang="fr")
        self.assertEqual(fig.layout.yaxis.ticksuffix, "%")

    def test_economic_breakdown(self):
        df = pd.DataFrame({
            "year": [2021, 2021], "econ": ["Wage bill", "Goods and services"],
            "percentage": [40.0, 60.0], "expenditure": [4e9, 6e9],
        })
        fig = home.economic_figure(df, "XOF", lang="fr")
        self.assertEqual(fig.layout.yaxis.ticksuffix, "%")

    def test_sector_economic_composition(self):
        df = pd.DataFrame({
            "year": [2021, 2022], "Wage bill": [60.0, 62.0],
            "Non-wage recurrent": [30.0, 28.0], "Capital expenditures": [10.0, 10.0],
        })
        fig = _generate_econ_figure(df, "Education", lang="fr")
        # Plotly leaves ticksuffix off ticks placed with tickvals; the labels carry it.
        self.assertEqual(list(fig.layout.yaxis.ticktext), ["20%", "40%", "60%", "80%", "100%"])


if __name__ == "__main__":
    unittest.main()
