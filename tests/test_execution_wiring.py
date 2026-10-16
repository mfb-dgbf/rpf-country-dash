"""How the execution page is wired: its query, store key, sidebar link,
translations and the declared openpyxl dependency."""
import pathlib
import unittest
from unittest.mock import patch

import pandas as pd

import data_mapping
from components.sidebar_nav import nav_items
from constants import EXECUTION_VIEW_COUNTRIES
from queries import QueryService
from translations.en import TRANSLATIONS as EN
from translations.fr import TRANSLATIONS as FR
from translations.pt import TRANSLATIONS as PT
from tests.execution_detail_fixture import YEAR as DETAIL_YEAR, detail_frame
from tests.execution_fixture import execution_frame

ROOT = pathlib.Path(__file__).resolve().parent.parent


class QueryTest(unittest.TestCase):

    def tearDown(self):
        QueryService._instance = None

    @patch("queries.DB_BACKEND", "databricks")
    @patch("queries.PUBLIC_ONLY", False)
    def test_reads_the_execution_table(self):
        with patch.object(QueryService, "execute_query", return_value=execution_frame()) as run:
            df = QueryService.get_instance().get_togo_execution_data()
        query = run.call_args.args[0]
        self.assertIn("SELECT *", query)
        self.assertIn("prd_mega.boost.tgo_execution", query)
        self.assertTrue(run.call_args.kwargs["persistent"])
        self.assertEqual(len(df), len(execution_frame()))

    @patch("queries.DB_BACKEND", "databricks")
    @patch("queries.PUBLIC_ONLY", False)
    def test_bypasses_the_cache_on_request(self):
        with patch.object(QueryService, "execute_query", return_value=execution_frame()) as run:
            QueryService.get_instance().get_togo_execution_data(persistent=False)
        self.assertFalse(run.call_args.kwargs["persistent"])


class DetailQueryTest(unittest.TestCase):

    def tearDown(self):
        QueryService._instance = None

    @patch("queries.DB_BACKEND", "databricks")
    @patch("queries.PUBLIC_ONLY", False)
    def test_reads_one_year_of_budget_lines(self):
        with patch.object(QueryService, "execute_query", return_value=detail_frame()) as run:
            QueryService.get_instance().get_togo_execution_detail(DETAIL_YEAR)
        query = run.call_args.args[0]
        self.assertIn("prd_mega.boost.tgo_execution_detail", query)
        self.assertIn(f"year = {DETAIL_YEAR}", query)
        self.assertNotIn("admin2_code", query)
        self.assertTrue(run.call_args.kwargs["persistent"])

    @patch("queries.DB_BACKEND", "databricks")
    @patch("queries.PUBLIC_ONLY", False)
    def test_reads_one_ministry_without_the_cache(self):
        with patch.object(QueryService, "execute_query", return_value=detail_frame()) as run:
            QueryService.get_instance().get_togo_execution_detail("2025", "210", persistent=False)
        query = run.call_args.args[0]
        self.assertIn("year = 2025", query)
        self.assertIn("admin2_code = '210'", query)
        self.assertFalse(run.call_args.kwargs["persistent"])

    @patch("queries.DB_BACKEND", "databricks")
    @patch("queries.PUBLIC_ONLY", False)
    def test_refuses_a_ministry_code_that_is_not_digits(self):
        with patch.object(QueryService, "execute_query") as run:
            with self.assertRaises(ValueError):
                QueryService.get_instance().get_togo_execution_detail(2025, "210' OR '1'='1")
        run.assert_not_called()


class StoreKeyTest(unittest.TestCase):

    def test_store_key_loads_the_normalised_table(self):
        raw = execution_frame()
        with patch.object(data_mapping, "_db") as db:
            db.return_value.get_togo_execution_data.return_value = raw
            df = data_mapping.function_data_mapping["togo_execution"]()
        self.assertEqual(len(df), len(raw))
        self.assertEqual(df.loc[2, "green_code"], "")


class SidebarTest(unittest.TestCase):

    def test_execution_link_only_for_execution_countries(self):
        self.assertEqual(EXECUTION_VIEW_COUNTRIES, frozenset({"Togo"}))
        self.assertIn(("nav.execution", "execution"), nav_items("Togo"))
        self.assertNotIn(("nav.execution", "execution"), nav_items("Kenya"))
        self.assertNotIn(("nav.execution", "execution"), nav_items(None))

    def test_other_links_unchanged(self):
        self.assertEqual(nav_items("Kenya"), [
            ("nav.overview", "home"), ("nav.education", "education"),
            ("nav.health", "health"), ("nav.about", "about"),
        ])


class TranslationTest(unittest.TestCase):

    def test_execution_keys_in_every_language(self):
        keys = {k for k in EN if k.startswith("execution.")} | {"nav.execution"}
        self.assertGreater(len(keys), 20)
        self.assertEqual(keys, {k for k in FR if k.startswith("execution.")} | {"nav.execution"} & FR.keys())
        self.assertEqual(keys, {k for k in PT if k.startswith("execution.")} | {"nav.execution"} & PT.keys())

    def test_french_labels(self):
        self.assertEqual(FR["nav.execution"], "Exécution du budget")
        self.assertEqual(FR["execution.download"], "Télécharger les tableaux (Excel)")
        self.assertEqual(FR["execution.heading.overview"], "Budget initial, budget final et exécution")
        self.assertEqual(FR["execution.download_sigfip"], "Rapport d'exécution (tableaux SIGFIP)")
        self.assertEqual(FR["execution.download_ca"], "Compte administratif")
        self.assertEqual(EN["execution.download_ca"], "Administrative account")


class RequirementsTest(unittest.TestCase):

    def test_openpyxl_is_declared(self):
        lines = (ROOT / "requirements.txt").read_text().splitlines()
        self.assertTrue(any(line.split("==")[0].strip() == "openpyxl" for line in lines))


if __name__ == "__main__":
    unittest.main()
