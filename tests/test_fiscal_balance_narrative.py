import unittest
from unittest.mock import patch

import pandas as pd

from components.fiscal_balance import narrative
from tests.fiscal_balance_fixture import dgbf_file_rows


class TestFiscalBalanceNarrativeWEO(unittest.TestCase):

    @patch("components.fiscal_balance._extract_balance_insights")
    def test_weo_mode_uses_actual_tense_when_all_rows_non_forecast(self, mock_extract):
        mock_extract.return_value = {
            "trend": {"start_year": 2020, "end_year": 2022, "slope": 1.0},
            "extrema": {},
        }

        weo_df = pd.DataFrame(
            {
                "year": [2020, 2021, 2022],
                "revenue": [10, 12, 15],
                "expenditure": [12, 13, 14],
                "is_forecast": [False, False, False],
            }
        )

        text = narrative(None, None, weo_df, "USD", view_mode="weo", lang="en")

        self.assertIn("improved overall", text)
        self.assertNotIn("is expected to improve overall", text)

    @patch("components.fiscal_balance._extract_balance_insights")
    def test_weo_mode_uses_forecast_tense_for_forecast_rows(self, mock_extract):
        mock_extract.return_value = {
            "trend": {"start_year": 2023, "end_year": 2025, "slope": 1.0},
            "extrema": {},
        }

        weo_df = pd.DataFrame(
            {
                "year": [2023, 2024, 2025],
                "revenue": [10, 12, 15],
                "expenditure": [12, 13, 14],
                "is_forecast": [True, True, True],
            }
        )

        text = narrative(None, None, weo_df, "USD", view_mode="weo", lang="en")

        self.assertIn("is expected to improve overall", text)

    @patch("components.fiscal_balance._extract_balance_insights")
    def test_composite_weo_period_starts_after_gfs_when_no_national(self, mock_extract):
        mock_extract.return_value = {
            "trend": {"start_year": 2021, "end_year": 2022, "slope": 1.0},
            "extrema": {},
        }

        gfs_df = pd.DataFrame(
            {
                "year": [2018, 2019, 2020],
                "revenue": [10, 11, 12],
                "expenditure": [12, 13, 14],
            }
        )
        weo_df = pd.DataFrame(
            {
                "year": [2019, 2020, 2021, 2022],
                "revenue": [10, 11, 12, 13],
                "expenditure": [12, 13, 14, 15],
            }
        )

        narrative(None, gfs_df, weo_df, "USD", view_mode="composite", lang="en")

        self.assertEqual(mock_extract.call_count, 2)
        gfs_call_df = mock_extract.call_args_list[0][0][0]
        weo_call_df = mock_extract.call_args_list[1][0][0]

        self.assertEqual(gfs_call_df["year"].tolist(), [2018, 2019, 2020])
        self.assertEqual(weo_call_df["year"].tolist(), [2021, 2022])

    def test_composite_weo_mixed_actual_and_forecast_uses_mixed_tense(self):
        weo_df = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023],
                "revenue": [100.0, 102.0, 104.0, 106.0],
                "expenditure": [102.0, 103.0, 104.2, 104.5],
                "is_forecast": [False, False, True, True],
            }
        )

        text = narrative(None, None, weo_df, "USD", view_mode="composite", lang="en")

        self.assertIn("improved overall", text)
        self.assertIn("is expected to improve overall", text)


class TestFiscalBalanceNarrativeOfficial(unittest.TestCase):
    """The official view over the DGBF's file, whose years cite different documents."""

    EXPECTED = {
        "fr": "Selon les chiffres de la DGBF, le budget a enregistré un déficit moyen "
              "de 249,88 Md XOF entre 2019 et 2025.",
        "en": "According to DGBF figures, the budget averaged a deficit of 249.88 B XOF from 2019 to 2025.",
        "pt": "Segundo os dados da DGBF, o orçamento teve déficit médio de 249,88 bi XOF de 2019 a 2025.",
    }

    def test_official_view_cites_the_dgbf_over_every_year(self):
        for lang, expected in self.EXPECTED.items():
            with self.subTest(lang=lang):
                text = narrative(dgbf_file_rows(), None, None, "XOF",
                                 view_mode="official", lang=lang, country="Togo")
                self.assertEqual(text, expected)

    def test_without_a_selected_view_togo_reads_the_official_sentence(self):
        weo_df = pd.DataFrame({
            "year": [2024, 2025, 2026],
            "revenue": [1.2e12, 1.3e12, 1.4e12],
            "expenditure": [1.5e12, 1.8e12, 2.1e12],
            "is_forecast": [False, True, True],
        })
        text = narrative(dgbf_file_rows(), None, weo_df, "XOF",
                         view_mode=None, lang="fr", country="Togo")
        self.assertEqual(text, self.EXPECTED["fr"])


if __name__ == "__main__":
    unittest.main()
