"""« Agriculture » page: BOOST agriculture spending next to FAOSTAT crops.

Fixtures use Togo's figures: executed and approved spending of the BOOST
sub-function Agriculture (billion XOF) and FAOSTAT maize and cassava.
"""
import unittest
from unittest.mock import patch

import pandas as pd

import server_store
from components import agriculture as ag
from components.sidebar_nav import nav_items
from components.source_metadata_popover import CHART_METADATA
from constants import END_YEAR
from queries import QueryService
from translations.en import TRANSLATIONS as EN
from translations.fr import TRANSLATIONS as FR
from translations.pt import TRANSLATIONS as PT

with patch("dash.register_page"):
    from pages import agriculture as page

NNBSP = " "


def spending_frame(extra_years=()):
    rows = [(2021, 24.3, 45.6, 24.3), (2022, 28.0, 51.1, 25.9), (2023, 49.8, 52.9, 43.7), (2024, 36.6, 54.0, 31.2)]
    rows += [(year, 30.0, 50.0, 25.0) for year in extra_years]
    return pd.DataFrame(
        [("Togo", y, e * 1e9, b * 1e9, r * 1e9) for y, e, b, r in rows],
        columns=["country_name", "year", "expenditure", "budget", "real_expenditure"],
    )


def crops_frame():
    maize = [(2021, 755187, 1230.2, 929020, "A"), (2022, 763336, 1253.8, 957047, "A"),
             (2023, 808000, 1253.7, 1013000, "X"), (2024, 804000, 1256.2, 1010000, "X")]
    cassava = [(2021, 302742, 3977.8, 1204249, "A"), (2024, 333367, 3800.8, 1267066.17, "I")]
    rows = [("Togo", y, 56, "Maize (corn)", a, yl, p, f) for y, a, yl, p, f in maize]
    rows += [("Togo", y, 125, "Cassava, fresh", a, yl, p, f) for y, a, yl, p, f in cassava]
    return pd.DataFrame(rows, columns=["country_name", "year", "item_code", "item", "area_harvested_ha",
                                       "yield_kg_ha", "production_t", "production_flag"])


class StoreTest(unittest.TestCase):
    def setUp(self):
        server_store.set("agriculture_spending", spending_frame(extra_years=[END_YEAR + 1]))
        server_store.set("fao_crop_production", crops_frame())

    def tearDown(self):
        server_store.clear()


class WiringTest(unittest.TestCase):
    def test_queries_read_the_two_tables(self):
        service = QueryService.__new__(QueryService)
        with patch.object(QueryService, "fetch_data", side_effect=lambda q: q):
            self.assertIn("fao_crop_production", service.get_fao_crop_production())
            spending = service.get_agriculture_spending()
        self.assertIn("expenditure_by_country_geo0_func_sub_year", spending)
        self.assertIn("func_sub = 'Agriculture'", spending)

    def test_store_keys(self):
        from data_mapping import function_data_mapping
        self.assertIn("fao_crop_production", function_data_mapping)
        self.assertIn("agriculture_spending", function_data_mapping)

    def test_sidebar_link_for_togo_only(self):
        self.assertIn(("nav.agriculture", "agriculture"), nav_items("Togo"))
        self.assertNotIn(("nav.agriculture", "agriculture"), nav_items("Kenya"))

    def test_info_buttons_name_their_source(self):
        self.assertEqual(CHART_METADATA["agriculture-crops"]["sources"][0]["key"], "fao_crop_production")
        self.assertEqual(CHART_METADATA["agriculture-spending"]["sources"][0]["key"], "boost")

    def test_keys_in_every_language(self):
        keys = {k for k in EN if k.startswith("agriculture.")} | {"nav.agriculture", "source_name.faostat"}
        self.assertEqual(keys, {k for k in FR if k.startswith("agriculture.")} | {"nav.agriculture", "source_name.faostat"} & FR.keys())
        self.assertEqual(keys, {k for k in PT if k.startswith("agriculture.")} | {"nav.agriculture", "source_name.faostat"} & PT.keys())


class DataTest(StoreTest):
    def test_years_stop_at_end_year(self):
        self.assertEqual(ag.load_spending("Togo")["year"].max(), 2024)

    def test_other_countries_have_no_page_data(self):
        self.assertIsNone(ag.load_spending("Kenya"))
        self.assertIsNone(ag.load_crops("Kenya"))

    def test_crops_largest_first_with_french_names(self):
        df = ag.load_crops("Togo")
        self.assertEqual(ag.crop_options(df), ["Cassava, fresh", "Maize (corn)"])
        self.assertEqual(ag.crop_label(df, "Maize (corn)", "fr"), "Maïs")


class FigureTest(StoreTest):
    def test_spending_axis_in_milliards(self):
        fig = ag.spending_figure(ag.load_spending("Togo"), "fr")
        self.assertEqual([trace.name for trace in fig.data], ["Budget approuvé", "Dépense exécutée", "Ajusté à l'inflation"])
        self.assertEqual(fig.layout.yaxis.title.text, "milliards de XOF")
        self.assertEqual(list(fig.data[1].y), [24.3, 28.0, 49.8, 36.6])

    def test_crop_figure_has_production_and_yield_axes(self):
        fig = ag.crop_figure(ag.load_crops("Togo"), "Maize (corn)", "fr")
        self.assertEqual(fig.layout.title.text, "Maïs : production et rendement")
        self.assertEqual(fig.layout.yaxis.title.text, "Production (tonnes)")
        self.assertEqual(fig.layout.yaxis2.title.text, "Rendement (kg/ha)")

    def test_crop_figure_shows_the_agriculture_budget_on_a_third_axis(self):
        fig = ag.crop_figure(ag.load_crops("Togo"), "Maize (corn)", "fr", spending=ag.load_spending("Togo"))
        budget = [trace for trace in fig.data if trace.name in ("Budget approuvé", "Dépense exécutée")]
        self.assertEqual([trace.yaxis for trace in budget], ["y3", "y3"])
        self.assertEqual(fig.layout.yaxis3.title.text, "Budget d'agriculture<br>(milliards de XOF)")
        self.assertEqual(fig.layout.title.text, "Maïs : production, rendement et budget d'agriculture")
        yield_color = next(trace.line.color for trace in fig.data if trace.name == "Rendement")
        self.assertNotIn(yield_color, [trace.line.color for trace in budget])
        self.assertEqual(list(budget[0].y), [45.6, 51.1, 52.9, 54.0])

    def test_crop_figure_without_spending_keeps_two_axes(self):
        fig = ag.crop_figure(ag.load_crops("Togo"), "Maize (corn)", "fr")
        self.assertEqual(len(fig.data), 2)

    def test_render_crop_starts_at_first_year_with_expenditure(self):
        crops = ag.load_crops("Togo")
        earlier = crops[crops["item"] == "Maize (corn)"].iloc[[0]].copy()
        earlier["year"] = 2020
        crops = pd.concat([crops, earlier], ignore_index=True)
        spending = ag.load_spending("Togo")
        spending.loc[spending["year"] < 2023, "expenditure"] = pd.NA

        figure, _ = ag.render_crop(crops, "Maize (corn)", "fr", spending)

        production = next(trace for trace in figure.data if trace.name == "Production")
        self.assertEqual(list(production.x), [2023, 2024])

    def test_missing_data_reads_unavailable(self):
        fig, text = ag.render_spending(None, "fr")
        self.assertEqual(text, "Données non disponibles pour cette période.")


class NarrativeTest(StoreTest):
    def test_spending_sentence(self):
        text = ag.spending_narrative(ag.load_spending("Togo"), "fr")
        self.assertIn("de 24,3 Md en 2021 à 36,6 Md en 2024, avec un maximum de 49,8 Md en 2023", text)
        self.assertIn("68,1 % du budget approuvé", text)

    def test_crop_sentence_sets_spending_and_production_side_by_side(self):
        text = ag.crop_narrative(ag.load_crops("Togo"), "Maize (corn)", "fr", spending=ag.load_spending("Togo"))
        self.assertIn("De 2021 à 2024, la dépense d'agriculture exécutée est passée de 24,3 Md à 36,6 Md (+50,6 %) "
                      f"et la production de cette culture de 929{NNBSP}020 à 1{NNBSP}010{NNBSP}000 tonnes (+8,7 %).", text)

    def test_crop_sentence_names_the_fao_flag(self):
        text = ag.crop_narrative(ag.load_crops("Togo"), "Maize (corn)", "fr")
        self.assertIn(f"Maïs : 929{NNBSP}020 tonnes en 2021 et 1{NNBSP}010{NNBSP}000 tonnes en 2024 (+8,7 %)", text)
        self.assertTrue(text.endswith("Le chiffre de 2024 est repris d'une autre organisation (FAOSTAT)."), text)


class PageTest(StoreTest):
    def test_store_says_what_is_ready(self):
        self.assertEqual(page.fetch_agriculture_data("Togo"), {"country": "Togo", "spending": True, "crops": True})
        self.assertEqual(page.fetch_agriculture_data("Kenya"), {"country": "Kenya", "spending": False, "crops": False})

    def test_crop_dropdown_defaults_to_maize(self):
        options, value = page.update_crop_options({"country": "Togo", "crops": True}, "Togo", "fr", None)
        self.assertEqual(value, "Maize (corn)")
        self.assertEqual([o["label"] for o in options], ["Manioc", "Maïs"])

    def test_no_crops_for_other_countries(self):
        self.assertEqual(page.update_crop_options({"country": "Kenya", "crops": False}, "Kenya", "fr", None), ([], None))


if __name__ == "__main__":
    unittest.main()
