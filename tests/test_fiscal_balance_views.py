"""The data views offered in the « Solde budgétaire » section and the one shown by default."""

import types
import unittest
from unittest.mock import patch

import dash

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from components import fiscal_balance  # noqa: E402
from constants import COMPOSITE_VIEW_COUNTRIES, VIEW_COMPOSITE, VIEW_OFFICIAL, VIEW_WEO  # noqa: E402
from pages import home  # noqa: E402
from tests.fiscal_balance_fixture import dgbf_file_rows  # noqa: E402

BASIC_INFO = {"currency_code": "XOF", "currency_name": "CFA franc BCEAO"}


def _find(component, component_id):
    if getattr(component, "id", None) == component_id:
        return component
    children = getattr(component, "children", None)
    if children is None:
        return None
    for child in children if isinstance(children, (list, tuple)) else [children]:
        found = _find(child, component_id)
        if found is not None:
            return found
    return None


class CompositeOfferTest(unittest.TestCase):
    def test_no_country_is_offered_the_composite_view(self):
        self.assertNotIn("Togo", COMPOSITE_VIEW_COUNTRIES)
        self.assertEqual(COMPOSITE_VIEW_COUNTRIES, frozenset())

    def test_default_view(self):
        self.assertEqual(fiscal_balance.default_view("Togo", official_available=True), VIEW_OFFICIAL)
        self.assertEqual(fiscal_balance.default_view("Togo", official_available=False), VIEW_WEO)
        self.assertEqual(fiscal_balance.default_view("Kenya", official_available=False), VIEW_WEO)


class ViewSelectorTest(unittest.TestCase):
    def test_static_selector_offers_no_composite(self):
        for lang in ("fr", "en"):
            with self.subTest(lang=lang):
                content = home.render_overview_content("overview-tab-time", lang)
                radio = _find(content, "revenue-expenditure-view")
                self.assertIsNotNone(radio)
                self.assertNotIn(VIEW_COMPOSITE, [o["value"] for o in radio.options])
                self.assertNotEqual(radio.value, VIEW_COMPOSITE)

    def _options(self, country, national_df):
        context = (national_df, None, None, BASIC_INFO)
        with patch.object(home, "_get_revenue_budget_context", return_value=context), \
                patch.object(home, "ctx", types.SimpleNamespace(triggered_id="country-select")):
            return home.update_revenue_expenditure_view_options(country, "fr", {"ready": True}, None)

    def test_togo_gets_three_views_with_the_official_report_selected(self):
        options, value = self._options("Togo", dgbf_file_rows())
        self.assertEqual(
            [(o["label"], o["value"]) for o in options],
            [("Rapport officiel", "official"), ("SFP", "gfs"), ("PEM", "weo")],
        )
        self.assertEqual(value, VIEW_OFFICIAL)

    def test_without_official_rows_weo_is_selected(self):
        options, value = self._options("Kenya", None)
        self.assertEqual([o["value"] for o in options], ["gfs", "weo"])
        self.assertEqual(value, VIEW_WEO)


class UnselectedViewTest(unittest.TestCase):
    """The figure and narrative callbacks draw Togo's default view before a view is selected."""

    def _call(self, render):
        context = (dgbf_file_rows(), None, None, BASIC_INFO)
        with patch.object(home, "_get_revenue_budget_context", return_value=context):
            return render({"ready": True}, {"ready": True}, "Togo", {"ready": True}, None, "fr")

    def test_narrative_reads_the_official_report(self):
        text = self._call(home.render_revenue_expenditure_narrative)
        self.assertTrue(text.startswith("Selon les chiffres de la DGBF, "), text)

    def test_figure_draws_the_official_report(self):
        fig = self._call(home.render_revenue_expenditure_combined)
        years = sorted({int(x) for tr in fig.data for x in tr.x})
        self.assertEqual(years, list(range(2019, 2026)))


if __name__ == "__main__":
    unittest.main()
