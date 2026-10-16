"""Every amount axis names its unit and every amount colour bar carries the
dashboard's suffixes.

In French an amount axis shows plain numbers with "milliards de XOF" in its
title (``scale_currency_axes``), not plotly's "200B" / "1,5T"; a map colour
bar reads "200 Md". Each test builds one chart from a small frame and checks
the axis or colour bar the amounts are drawn on.
"""

import unittest
from unittest.mock import patch

import dash
import pandas as pd

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from components import budget_funding_execution as bfe  # noqa: E402
from components import edu_health_across_space as space  # noqa: E402
from components import fiscal_balance  # noqa: E402
from pages import education, health, home  # noqa: E402

YEARS = [2021, 2022, 2023]
FR_SUFFIXES = (" k", " M", " Md")

GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"country": "Togo", "region": region},
            "geometry": {"type": "Polygon", "coordinates": [[[lon, 8], [lon + 1, 8], [lon + 1, 9], [lon, 8]]]},
        }
        for lon, region in ((0, "Kara"), (1, "Savanes"))
    ],
}


def _scaled(test, fig, title, unit, axis="y"):
    """``title`` names ``unit`` and the traces on ``axis`` are scaled to plain numbers."""
    test.assertIn(unit, title)
    traces = [tr for tr in fig.data if (tr[axis[0] + "axis"] or axis[0]) == axis and tr[axis[0]] is not None]
    test.assertTrue(traces)
    largest = max(max(abs(v) for v in tr[axis[0]] if v == v) for tr in traces)
    test.assertLess(largest, 1e4)


def _labels_amounts(test, axis):
    test.assertEqual(axis.tickmode, "array")
    labels = [label for label in axis.ticktext if label != "0"]
    test.assertTrue(labels)
    for label in labels:
        test.assertTrue(label.endswith(FR_SUFFIXES), label)


class OverviewAmountAxesTest(unittest.TestCase):
    def _national(self):
        return pd.DataFrame({
            "country_name": "Togo",
            "year": YEARS,
            "expenditure": [1.05e12, 1.33e12, 1.58e12],
            "decentralized_expenditure": [0.0, 0.0, 0.0],
            "real_expenditure": [1.05e12, 1.24e12, 1.38e12],
            "per_capita_expenditure": [130e3, 160e3, 190e3],
            "per_capita_real_expenditure": [130e3, 150e3, 170e3],
            "poverty_rate": [55.0, None, None],
        })

    def test_total_expenditure(self):
        fig = home.total_figure(self._national(), "francs CFA", "XOF", lang="fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliards de francs CFA")

    def test_per_capita_expenditure(self):
        fig = home.per_capita_figure(self._national(), "francs CFA", "XOF", lang="fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliers de francs CFA")

    def test_funding_source_total_budget_on_the_right_axis(self):
        df = pd.DataFrame({
            "year": YEARS,
            "budget": [1.1e12, 1.3e12, 1.6e12],
            "real_budget": [1.1e12, 1.2e12, 1.4e12],
            "domestic_funded_budget": [0.9e12, 1.0e12, 1.3e12],
            "foreign_funded_budget": [0.2e12, 0.3e12, 0.3e12],
            "real_domestic_funded_budget": [0.9e12, 0.9e12, 1.1e12],
            "real_foreign_funded_budget": [0.2e12, 0.3e12, 0.3e12],
        })
        df["domestic_share"] = df["domestic_funded_budget"] / df["budget"] * 100
        df["foreign_share"] = df["foreign_funded_budget"] / df["budget"] * 100
        fig = bfe.create_funding_source_figure(df, "XOF", lang="fr")
        _scaled(self, fig, fig.layout.yaxis2.title.text, "milliards de XOF", axis="y2")
        self.assertEqual(fig.layout.yaxis.ticksuffix, "%")

    def test_funding_source_without_split_on_the_left_axis(self):
        df = pd.DataFrame({
            "year": YEARS, "budget": [1.1e12, 1.3e12, 1.6e12], "real_budget": [1.1e12, 1.2e12, 1.4e12],
            "domestic_share": [None] * 3, "foreign_share": [None] * 3,
        })
        fig = bfe.create_funding_source_figure(df, "XOF", lang="fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliards de XOF")

    def test_fiscal_balance_lines_and_deficit_bars(self):
        national = pd.DataFrame({
            "year": YEARS,
            "revenue": [0.9e12, 1.0e12, 1.1e12],
            "expenditure": [1.2e12, 1.4e12, 1.5e12],
            "source": "Togo DGB Budget Execution Report",
        })
        fig = fiscal_balance.combined_figure(national, None, None, "XOF", "francs CFA",
                                             view_mode="official", lang="fr")
        note = " ".join(a.text for a in fig.layout.annotations)
        _scaled(self, fig, note, "milliards de francs CFA")
        _scaled(self, fig, note, "milliards de francs CFA", axis="y2")
        balance = [tr for tr in fig.data if tr.yaxis == "y2"]
        self.assertTrue(any(v < 0 for tr in balance for v in tr.y))

    def _regional(self):
        return pd.DataFrame({
            "country_name": "Togo", "year": 2023, "adm1_name": ["Kara", "Savanes"],
            "expenditure": [40e9, 90e9], "per_capita_expenditure": [30e3, 160e3],
            "expenditure_formatted": ["", ""], "per_capita_expenditure_formatted": ["", ""],
        })

    def test_regional_spending_map_colorbar(self):
        df = self._regional()
        fig = home.regional_spending_choropleth(GEOJSON, None, df, 40e9, 90e9, 8, 1, 5, "light", lang="fr")
        _labels_amounts(self, fig.layout.coloraxis.colorbar)

    def test_regional_per_capita_map_colorbar(self):
        df = self._regional()
        fig = home.regional_percapita_spending_choropleth(GEOJSON, None, df, 30e3, 160e3, 8, 1, 5, "light", lang="fr")
        _labels_amounts(self, fig.layout.coloraxis.colorbar)


def _sector_public(prefix):
    return pd.DataFrame({
        "country_name": "Togo",
        "year": YEARS,
        "expenditure": [150e9, 160e9, 210e9],
        "central_expenditure": [150e9, 160e9, 210e9],
        "decentralized_expenditure": [0.0, 0.0, 0.0],
        "real_expenditure": [150e9, 150e9, 190e9],
        "per_capita_real_expenditure": [18e3, 17e3, 22e3],
        "expenditure_decentralization": [0.0, 0.0, 0.0],
    })


class SectorAmountAxesTest(unittest.TestCase):
    def test_education_total(self):
        fig = education.total_edu_figure(_sector_public("edu"), "XOF", lang="fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliards de XOF")

    def test_health_total(self):
        fig = health.total_health_figure(_sector_public("health"), "XOF", lang="fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliards de XOF")

    def test_education_outcome_spending_axis(self):
        store = {
            "hd_index": pd.DataFrame({"country_name": "Togo", "year": [2019, 2020], "adm1_name": "Total",
                                      "attendance_6to17yo": [0.8, 0.82]}),
            "learning_poverty": pd.DataFrame({"country_name": "Togo", "year": [2019], "learning_poverty_rate": [80.0]}),
            "edu_public_expenditure": _sector_public("edu"),
            "basic_country_info": {"Togo": {"currency_code": "XOF"}},
        }
        with patch.object(education.server_store, "get", side_effect=store.__getitem__):
            fig, _, _ = education.render_education_outcome(["d"], ["d"], "Togo", {"Togo": {}}, "fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliers de XOF")
        self.assertEqual(fig.layout.yaxis2.tickformat, ".0%")

    def test_health_outcome_spending_axis(self):
        store = {
            "uhc_index": pd.DataFrame({"country_name": "Togo", "year": [2019, 2021],
                                       "universal_health_coverage_index": [42.0, 44.0]}),
            "health_public_expenditure": _sector_public("health"),
            "basic_country_info": {"Togo": {"currency_code": "XOF"}},
        }
        with patch.object(health.server_store, "get", side_effect=store.__getitem__):
            fig, _, _ = health.render_health_outcome(["d"], ["d"], "Togo", {"Togo": {}}, "fr")
        _scaled(self, fig, fig.layout.yaxis.title.text, "milliers de XOF")

    def test_sector_expenditure_map_colorbar(self):
        geo = pd.DataFrame({
            "country_name": "Togo", "year": 2023, "func": "Health", "adm1_name": ["Kara", "Savanes"],
            "expenditure": [4e9, 9e9], "per_capita_expenditure": [2_300.0, 5_800.0],
            "outcome_index": [None, None],
        })
        store = {
            "basic_country_info": {"Togo": {"currency_code": "XOF", "display_lat": 8, "display_lon": 1, "zoom": 5}},
            "geo1_func_expenditure": geo,
            "subnat_boundaries": GEOJSON,
            "disputed_boundaries": {},
        }
        with patch.object(space.server_store, "get", side_effect=store.__getitem__), \
                patch.object(space.server_store, "lookup", side_effect=lambda key, default=None: store.get(key, default)):
            fig = space.update_func_expenditure_map(
                ["d"], ["d"], "Togo", 2023, "per_capita_expenditure", ["d"], "Health", "light", lang="fr")
        _labels_amounts(self, fig.layout.coloraxis.colorbar)


if __name__ == "__main__":
    unittest.main()
