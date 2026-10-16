"""Data preparation, narratives and figures of the « Exécution du budget » page."""
import math
import unittest
from unittest.mock import patch

import pandas as pd

import server_store
from components import togo_execution as te
from translations import t
from tests.execution_fixture import (
    OPEN_YEAR,
    PRIOR_YEAR,
    TOTAL_FINALE,
    TOTAL_INITIALE,
    TOTAL_ORDONNANCER,
    YEAR,
    execution_frame,
)


def _df():
    return te.normalise_execution(execution_frame())


def _records(df, columns):
    return [tuple(row) for row in df[columns].itertuples(index=False)]


class NormaliseTest(unittest.TestCase):

    def test_null_keys_become_empty_codes_and_measures_numbers(self):
        raw = execution_frame()
        raw.loc[0, "engagement"] = None
        df = te.normalise_execution(raw)
        self.assertEqual(df.loc[2, "green_code"], "")
        self.assertEqual(df.loc[5, "prog_code"], "")
        self.assertEqual(df.loc[0, "engagement"], 0)
        self.assertEqual(df["pip"].tolist()[:3], [False, True, True])

    def test_pip_none_is_not_pip(self):
        raw = execution_frame()
        raw["pip"] = raw["pip"].astype(object)
        raw.loc[0, "pip"] = None
        self.assertFalse(te.normalise_execution(raw).loc[0, "pip"])


class YearsTest(unittest.TestCase):

    def test_years_stop_at_end_year_latest_first(self):
        self.assertEqual(te.execution_years(_df()), [YEAR, PRIOR_YEAR])

    def test_yearly_totals(self):
        totals = te.yearly_totals(_df())
        self.assertEqual(totals["year"].tolist(), [PRIOR_YEAR, YEAR])
        self.assertNotIn(OPEN_YEAR, totals["year"].tolist())
        latest = totals.iloc[-1]
        self.assertEqual(latest["dotation_initiale"], TOTAL_INITIALE)
        self.assertEqual(latest["dotation_finale"], TOTAL_FINALE)
        self.assertEqual(latest["ordonnancer"], TOTAL_ORDONNANCER)
        self.assertAlmostEqual(latest["rate"], TOTAL_ORDONNANCER / TOTAL_FINALE)


class StagesTest(unittest.TestCase):

    def test_stages_of_the_year(self):
        stages = te.spending_stages(_df(), YEAR)
        self.assertEqual(stages["dotation_finale"], 900)
        self.assertEqual(stages["engagement"], 430)
        self.assertEqual(stages["liquidation"], 405)
        self.assertEqual(stages["ordonnancer"], 680)
        self.assertEqual(stages["ordonnancer_ri"], 380)
        self.assertEqual(stages["ordonnancer_re"], 300)
        self.assertEqual(stages["dotation_finale_re"], 400)
        self.assertEqual(stages["dotation_finale_ri"], 500)


class BreakdownTest(unittest.TestCase):

    def test_ministries_sorted_by_final_budget(self):
        ministries = te.by_ministry(_df(), YEAR)
        self.assertEqual(
            _records(ministries, ["admin2_code", "admin2_short", "dotation_finale", "ordonnancer"]),
            [("210", "MEF", 770, 550), ("320", "MS", 130, 130)],
        )
        self.assertAlmostEqual(ministries.iloc[0]["rate"], 550 / 770)

    def test_ministry_by_nature_keeps_undefined_rate(self):
        cells = te.ministry_by_nature(_df(), YEAR)
        self.assertEqual(
            _records(cells, ["admin2_code", "econ1_code", "dotation_finale", "ordonnancer"]),
            [("210", "2", 120, 100), ("210", "5", 650, 450),
             ("320", "3", 50, 40), ("320", "4", 80, 80), ("320", "5", 0, 10)],
        )
        self.assertTrue(math.isnan(cells.iloc[-1]["rate"]))

    def test_natures_add_up_to_the_year(self):
        natures = te.by_nature(_df(), YEAR)
        self.assertEqual(natures["econ1_code"].tolist(), ["2", "3", "4", "5"])
        self.assertEqual(natures["dotation_finale"].sum(), TOTAL_FINALE)
        self.assertEqual(natures["ordonnancer"].sum(), TOTAL_ORDONNANCER)
        self.assertEqual(natures["dotation_initiale"].sum(), TOTAL_INITIALE)

    def test_programmes_of_one_ministry_keep_unnamed_programme(self):
        programmes = te.programmes(_df(), YEAR, "320")
        self.assertEqual(
            _records(programmes, ["prog_code", "econ1_code", "dotation_finale", "ordonnancer"]),
            [("", "4", 80, 80), ("010", "3", 50, 40), ("010", "5", 0, 10)],
        )

    def test_investment_parts_partition_capital(self):
        parts = te.investment_by_funding(_df(), YEAR)
        self.assertEqual(
            _records(parts, ["group", "dotation_finale", "ordonnancer"]),
            [("hors_pip", 0, 10), ("pip_ri", 250, 150), ("re", 400, 300)],
        )

    def test_top_projects_skip_lines_without_project(self):
        projects = te.top_projects(_df(), YEAR, n=20)
        self.assertEqual(
            _records(projects, ["project_code", "project", "dotation_finale", "ordonnancer"]),
            [("P2", "HOPITAL B", 400, 300), ("P1", "ROUTE A", 250, 150)],
        )

    def test_tag_shares_cover_the_whole_year(self):
        shares = te.tag_shares(_df(), YEAR, "social")
        self.assertEqual(
            _records(shares, ["code", "dotation_finale", "ordonnancer"]),
            [("", 400, 300), ("1", 200, 190), ("2", 300, 190)],
        )
        self.assertAlmostEqual(shares["share_finale"].sum(), 1)
        self.assertAlmostEqual(shares["share_ordonnancer"].sum(), 1)


class FormatTest(unittest.TestCase):

    def test_full_amounts_per_language(self):
        self.assertEqual(te.format_amount(7136488000, "fr"), "7 136 488 000")
        self.assertEqual(te.format_amount(7136488000, "en"), "7,136,488,000")
        self.assertEqual(te.format_amount(7136488000, "pt"), "7.136.488.000")

    def test_rates_per_language(self):
        self.assertEqual(te.format_rate(0.9343, "fr"), "93,4 %")
        self.assertEqual(te.format_rate(0.9343, "en"), "93.4%")
        self.assertEqual(te.format_rate(float("nan"), "fr"), "–")


class NarrativeTest(unittest.TestCase):

    def test_overview_names_the_year_amounts_and_rate(self):
        text = te.overview_narrative(te.yearly_totals(_df()), YEAR, lang="fr")
        self.assertIn(str(YEAR), text)
        self.assertIn("860,00 XOF", text)
        self.assertIn("900,00 XOF", text)
        self.assertIn("680,00 XOF", text)
        self.assertIn("75,6 %", text)

    def test_stages_narrative(self):
        text = te.stages_narrative(te.spending_stages(_df(), YEAR), YEAR, lang="fr")
        self.assertIn("47,8 %", text)  # 430 / 900 engaged
        self.assertIn("44,1 %", text)  # 300 / 680 ordered on external resources

    def test_external_note_when_external_lines_carry_no_commitment(self):
        note = te.external_note(te.spending_stages(_df(), YEAR), YEAR, lang="fr")
        self.assertEqual(note, t("execution.note.external_none", "fr", year=YEAR))

    def test_external_note_states_the_amounts_otherwise(self):
        raw = execution_frame()
        raw.loc[2, ["engagement", "liquidation"]] = [56805200, 55848869]
        stages = te.spending_stages(te.normalise_execution(raw), YEAR)
        note = te.external_note(stages, YEAR, lang="fr")
        self.assertIn("56,81 M XOF", note)
        self.assertIn("55,85 M XOF", note)
        self.assertIn("300,00 XOF", note)

    def test_tag_narrative_uses_the_tagged_codes(self):
        text = te.tag_narrative(te.tag_shares(_df(), YEAR, "social"), "social", YEAR, lang="fr")
        self.assertIn("33,3 %", text)  # 300 / 900
        self.assertIn("27,9 %", text)  # 190 / 680


class RenderTest(unittest.TestCase):

    def test_every_block_renders_from_the_fixture(self):
        df = _df()
        for render in (te.render_overview, te.render_stages, te.render_ministries,
                       te.render_ministry_nature, te.render_investment):
            fig, text = render(df, YEAR, "fr")
            self.assertTrue(fig.data, render.__name__)
            self.assertTrue(text, render.__name__)
        for dim in te.TAG_DIMENSIONS:
            fig, text = te.render_tag(df, YEAR, dim, "fr")
            self.assertTrue(fig.data, dim)

    def test_unavailable_data_gives_the_unavailable_state(self):
        fig, text = te.render_overview(None, None, "fr")
        self.assertEqual(text, t("error.data_unavailable", "fr"))
        self.assertFalse(fig.data)


class LoadTest(unittest.TestCase):

    def setUp(self):
        server_store.clear()
        self.addCleanup(server_store.clear)

    def test_missing_table_gives_none(self):
        def missing():
            raise RuntimeError('relation "boost.tgo_execution" does not exist')

        with patch.dict("data_mapping.function_data_mapping", {"togo_execution": missing}):
            self.assertIsNone(te.load_execution("Togo"))

    def test_other_country_gives_none(self):
        server_store.set("togo_execution", _df())
        self.assertIsNone(te.load_execution("Kenya"))

    def test_togo_rows(self):
        server_store.set("togo_execution", _df())
        self.assertEqual(len(te.load_execution("Togo")), len(execution_frame()))


if __name__ == "__main__":
    unittest.main()
