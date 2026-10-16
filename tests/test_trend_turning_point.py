"""A trend fitted as one segment is called steady only when the series is monotone.

trend-narrative fits a short series that rises then falls as a single segment
and ends its sentence with "maintaining a consistent trajectory". The wrapper
names the turning point instead.
"""

import unittest

from trend_narrative import InsightExtractor, get_segment_narrative

from translations import t
from trend_narrative_i18n import get_segment_narrative_i18n

YEARS = [2021, 2022, 2023, 2024, 2025]
# Togo's total real expenditure, 2021-2025 (boost.pov_expenditure_by_country_year): up to
# 2023, then down. The detector fits these exact values as one segment.
PEAKED = [1065745195540.0, 1240880745965.2266, 1383989780702.3333, 1346081842591.6455,
          1313615150230.8774]
RISING = [1000e9, 1100e9, 1200e9, 1300e9, 1400e9]


def narrative(values, lang):
    return get_segment_narrative_i18n(
        extractor=InsightExtractor(YEARS, values),
        metric=t("metric.total_real_expenditure", lang, meta=True),
        lang=lang,
    )


class TurningPointTest(unittest.TestCase):
    def test_french_names_the_peak_instead_of_a_constant_trajectory(self):
        text = narrative(PEAKED, "fr")
        self.assertNotIn("trajectoire constante", text)
        self.assertTrue(text.endswith(", avec un point haut de 1\u202f383,99 Md en 2023."), text)

    def test_english_names_the_peak(self):
        text = narrative(PEAKED, "en")
        self.assertNotIn("consistent trajectory", text)
        self.assertTrue(text.endswith(", after peaking at 1.38 T in 2023."), text)

    def test_portuguese_names_the_peak(self):
        text = narrative(PEAKED, "pt")
        self.assertNotIn("trajetória consistente", text)
        self.assertTrue(text.endswith(", após atingir um pico de 1,38 tri em 2023."), text)

    def test_the_change_over_the_period_is_kept(self):
        self.assertIn("ont augmenté de 247,87 Md (+23,26 %)", narrative(PEAKED, "fr"))

    def test_a_monotone_series_keeps_the_library_sentence(self):
        metric = t("metric.total_real_expenditure", "fr", meta=True)
        expected = get_segment_narrative(
            extractor=InsightExtractor(YEARS, RISING), metric=metric, lang="fr"
        )
        self.assertEqual(narrative(RISING, "fr"), expected)


if __name__ == "__main__":
    unittest.main()
