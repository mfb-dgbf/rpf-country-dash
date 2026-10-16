"""The outcome charts of the « Répartition spatiale » tabs (education and health).

They read boost.expenditure_and_outcome_by_country_geo1_func_year: one row per
region, spending year and sector, with ``outcome_index`` — school attendance
for education, Global Data Lab's health index for health. Years count back
from END_YEAR (E): with E = 2025, education spending 2021-2025 is paired with
2020 attendance.
"""

import copy
import unittest
from unittest.mock import patch

import pandas as pd

from constants import END_YEAR as E
from translations import t

with patch("dash.register_page"):
    from components import edu_health_across_space as space

REGIONS = ["Centrale", "Kara", "Maritime", "Plateaux", "Savanes"]
GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"country": "Togo", "region": region},
            "geometry": {"type": "Polygon", "coordinates": [[[i, 8], [i + 1, 8], [i + 1, 9], [i, 8]]]},
        }
        for i, region in enumerate(REGIONS)
    ],
}


def _rows(func, years, outcome):
    """Five regions and Central Scope for each spending year; ``outcome`` maps a
    spending year to (outcome_index base, outcome_year) or None."""
    rows = []
    for year in years:
        paired = outcome(year)
        for i, region in enumerate(REGIONS):
            rows.append({
                "country_name": "Togo", "year": year, "func": func, "adm1_name": region,
                "expenditure": 1e9 * (i + 1), "per_capita_expenditure": 1_000.0 * (i + 1),
                "outcome_index": None if paired is None else paired[0] + 0.01 * i,
                "outcome_year": None if paired is None else paired[1],
            })
        rows.append({
            "country_name": "Togo", "year": year, "func": func, "adm1_name": "Central Scope",
            "expenditure": 9e9, "per_capita_expenditure": None,
            "outcome_index": None, "outcome_year": None,
        })
    return pd.DataFrame(rows)


def _store(geo):
    values = {
        "basic_country_info": {"Togo": {"currency_code": "XOF", "display_lat": 8, "display_lon": 1, "zoom": 5}},
        "geo1_func_expenditure": geo,
        "subnat_boundaries": GEOJSON,
        "disputed_boundaries": {},
    }
    return (
        patch.object(space.server_store, "get", side_effect=lambda key: copy.deepcopy(values[key])),
        patch.object(space.server_store, "lookup",
                     side_effect=lambda key, default=None: copy.deepcopy(values.get(key, default))),
    )


def _health_exact_year():
    """The table before outcome_year: an outcome only where GDL has that year."""
    geo = _rows("Health", range(E - 3, E + 1), lambda y: (0.62, y) if y <= E - 1 else None)
    return geo.drop(columns="outcome_year")


class HealthIndexNameTest(unittest.TestCase):
    """The health maps plot GDL's health index (life expectancy), not the UHC index."""

    def test_outcome_map_names_the_health_index(self):
        get, lookup = _store(_health_exact_year())
        with get, lookup:
            fig = space.update_hd_index_map(["d"], ["d"], "Togo", E - 1, ["d"], "Health", "light", lang="fr")
        self.assertEqual(fig.layout.title.text, "Indice de santé (espérance de vie) au niveau infranational")
        self.assertIn("Indice de santé (espérance de vie)", fig.data[0].hovertemplate)

    def test_sankey_names_the_health_index(self):
        get, lookup = _store(_health_exact_year())
        with get, lookup:
            fig, narrative = space.render_func_subnat_rank(["d"], "Togo", E - 1, "Health", "XOF", lang="fr")
        headers = [a.text for a in fig.layout.annotations]
        self.assertTrue(any("Indice de santé (espérance de vie)" in h for h in headers), headers)
        self.assertNotIn("CSU", " ".join(headers))
        self.assertIn("mesuré par l'indice de santé (espérance de vie)", narrative)

    def test_section_introduction_names_the_health_index(self):
        for lang, phrase in (("fr", "espérance de vie"), ("en", "life expectancy"), ("pt", "expectativa de vida")):
            with self.subTest(lang=lang):
                text = t("narrative.health_subnational_motivation", lang, country="le Togo", year=2023)
                self.assertIn(phrase, text)
                self.assertNotIn("CSU", text)
                self.assertNotIn("UHC", text)



def _education_paired():
    """The table with outcome_year: every spending year paired with the
    attendance of the year before the first one."""
    return _rows("Education", range(E - 4, E + 1), lambda y: (0.80, E - 5))


def _health_paired():
    """Health index up to E - 2; the last two spending years paired with it."""
    return _rows("Health", range(E - 4, E + 1), lambda y: (0.62, min(y, E - 2)))


def _notes(fig):
    return [a.text for a in fig.layout.annotations]


class OutcomeYearTest(unittest.TestCase):
    """An outcome paired with a later spending year is shown with its own year."""

    def _maps(self, geo, func, year, lang="fr"):
        get, lookup = _store(geo)
        with get, lookup:
            outcome = space.update_hd_index_map(["d"], ["d"], "Togo", year, ["d"], func, "light", lang=lang)
            spending = space.update_func_expenditure_map(
                ["d"], ["d"], "Togo", year, "per_capita_expenditure", ["d"], func, "light", lang=lang)
            sankey, narrative = space.render_func_subnat_rank(["d"], "Togo", year, func, "XOF", lang=lang)
        return outcome, spending, sankey, narrative

    def test_education_last_year_shows_the_attendance_with_its_own_year(self):
        # With E = 2025: selected 2025, attendance from 2020, the note names 2020.
        outcome, spending, sankey, narrative = self._maps(_education_paired(), "Education", E)
        self.assertIn(t("annotation.displaying_data_from", "fr", year=E - 5), _notes(outcome))
        self.assertEqual(len(outcome.data[0].locations), 5)
        # The spending map labels its own year, since the two maps differ.
        self.assertIn(t("annotation.displaying_data_from", "fr", year=E), _notes(spending))
        headers = _notes(sankey)
        self.assertIn(str(E - 5), headers[1])
        self.assertIn(str(E), headers[0])
        self.assertIn(str(E), narrative)
        self.assertIn(str(E - 5), narrative)

    def test_health_shows_the_last_measured_index_with_its_year(self):
        outcome, spending, sankey, _ = self._maps(_health_paired(), "Health", E - 1)
        self.assertIn(t("annotation.displaying_data_from", "fr", year=E - 2), _notes(outcome))
        self.assertIn(t("annotation.displaying_data_from", "fr", year=E - 1), _notes(spending))
        self.assertIn(str(E - 2), _notes(sankey)[1])

    def test_same_year_outcome_needs_no_note(self):
        outcome, spending, sankey, narrative = self._maps(_health_paired(), "Health", E - 3)
        notes = _notes(outcome) + _notes(spending)
        self.assertFalse([n for n in notes if n.startswith("Affichage")], notes)
        self.assertIn(str(E - 3), _notes(sankey)[1])
        self.assertTrue(narrative.startswith(f"En {E - 3}, "), narrative)

    def test_without_outcome_year_the_latest_outcome_year_is_carried(self):
        outcome, spending, sankey, _ = self._maps(_health_exact_year(), "Health", E)
        self.assertIn(t("annotation.displaying_data_from", "fr", year=E - 1), _notes(outcome))
        self.assertIn(t("annotation.displaying_data_from", "fr", year=E), _notes(spending))
        # Without the column the ranking pairs only same-year rows.
        self.assertEqual(sankey.data, ())

    def test_without_outcome_year_a_same_year_outcome_needs_no_note(self):
        outcome, spending, sankey, _ = self._maps(_health_exact_year(), "Health", E - 1)
        notes = _notes(outcome) + _notes(spending)
        self.assertFalse([n for n in notes if n.startswith("Affichage")], notes)
        self.assertIn(str(E - 1), _notes(sankey)[1])


class SankeyLayoutTest(unittest.TestCase):
    def _sankey(self):
        get, lookup = _store(_health_exact_year())
        with get, lookup:
            fig, _ = space.render_func_subnat_rank(["d"], "Togo", E - 1, "Health", "XOF", lang="fr")
        return fig

    def test_rank_label_ends_before_the_first_node(self):
        fig = self._sankey()
        rank = next(a for a in fig.layout.annotations if a.text == "<b>1er</b>")
        node = fig.data[0].node
        self.assertEqual((rank.xref, rank.xanchor), ("paper", "right"))
        self.assertLessEqual(rank.x, node.x[0])
        # Node x is a node's centre: the label ends left of the node's edge.
        self.assertLess(rank.xshift, -node.thickness / 2)

    def test_region_labels_are_readable(self):
        fig = self._sankey()
        self.assertGreaterEqual(fig.data[0].textfont.size, 13)
        # Both columns name the regions as they are.
        self.assertEqual(sorted(fig.data[0].node.label[:5]), sorted(fig.data[0].node.label[5:]))


class YearSliderTest(unittest.TestCase):
    """A year counts as complete only when its outcome was measured that year."""

    def _slider(self, geo, func):
        get, lookup = _store(geo)
        with get, lookup:
            return space.update_year_slider(["d"], "Togo", func)

    def test_carried_outcomes_do_not_complete_a_year(self):
        from components.year_slider import YEAR_PARTIAL_STYLE
        _, marks, value, *_ = self._slider(_education_paired(), "Education")
        self.assertEqual(value, E)
        self.assertTrue(all(mark["style"] == YEAR_PARTIAL_STYLE for mark in marks.values()))

    def test_health_defaults_to_its_last_measured_year(self):
        _, _, value, *_ = self._slider(_health_paired(), "Health")
        self.assertEqual(value, E - 2)
        _, _, value, *_ = self._slider(_health_exact_year(), "Health")
        self.assertEqual(value, E - 1)


if __name__ == "__main__":
    unittest.main()
