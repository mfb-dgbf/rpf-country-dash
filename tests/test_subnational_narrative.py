"""The education and health spending narratives when subnational spending
is missing or zero in the first year of the series: the central-spending
sentence closes and nothing is said of subnational spending.
"""

import unittest
from unittest.mock import patch

import dash
import pandas as pd

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education, health  # noqa: E402


def _spending(decentralized):
    return pd.DataFrame({
        "country_name": "Togo",
        "year": [2021, 2022, 2023],
        "expenditure": [150e9, 160e9, 210e9],
        "real_expenditure": [150e9, 150e9, 190e9],
        "central_expenditure": [150e9, 160e9, 210e9],
        "decentralized_expenditure": decentralized,
        "expenditure_decentralization": [0.0, 0.0, 0.0],
    })


class NoSubnationalSpendingTest(unittest.TestCase):
    def _narratives(self, decentralized, lang):
        out = {}
        for page, key in ((education, "edu_public_expenditure"), (health, "health_public_expenditure")):
            store = {key: _spending(decentralized)}
            with patch.object(page.server_store, "get", side_effect=store.__getitem__):
                narrative = education.education_narrative if page is education else health.health_narrative
                out[page.__name__] = narrative(["d"], "Togo", lang=lang)
        return out

    def test_says_nothing_of_subnational_spending(self):
        for decentralized in ([0.0, 0.0, 0.0], [float("nan")] * 3):
            for page, text in self._narratives(decentralized, "fr").items():
                with self.subTest(page=page, decentralized=decentralized):
                    self.assertNotIn("collectivités territoriales", text)
                    self.assertNotIn("décentralis", text)
                    self.assertNotIn(" . ", text)
                    self.assertTrue(text.endswith(". "), text)

    def test_other_languages(self):
        for lang, word in (("en", "subnational"), ("pt", "subnaciona")):
            for page, text in self._narratives([0.0, 0.0, 0.0], lang).items():
                with self.subTest(lang=lang, page=page):
                    self.assertNotIn(word, text)
                    self.assertNotIn(" . ", text)


if __name__ == "__main__":
    unittest.main()
