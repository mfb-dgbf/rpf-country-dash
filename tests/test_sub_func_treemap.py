"""The sub-function treemap (« Combien l'État a-t-il dépensé aux différents
niveaux de l'éducation ? ») adds up to the sector.

Spending without a sub-function (education COFOG 095, 097, 098; health 076)
gets its own box, the sector total minus the spending that has one.
"""

import unittest
from unittest.mock import patch

import pandas as pd

with patch("dash.register_page"):
    from components import edu_health_across_space as space


def _sub_func_rows(unclassified=30e9):
    return pd.DataFrame({
        "func_sub": ["Primary Education", "Primary Education", "Tertiary Education", None],
        "geo0": ["Central", "Regional", "Regional", "Regional"],
        "expenditure": [6e9, 87e9, 25e9, unclassified],
        "real_expenditure": [6e9, 80e9, 23e9, unclassified * 0.9],
    })


def _top_level(fig):
    trace = fig.data[0]
    return {
        id_: (label, value)
        for id_, label, value, parent in zip(trace.ids, trace.labels, trace.values, trace.parents)
        if parent == ""
    }


class RemainderBoxTest(unittest.TestCase):
    def test_boxes_add_up_to_the_sector_total(self):
        fig = space._sub_func_fig(_sub_func_rows(), "Education", "XOF", lang="fr",
                                  sector_total=(148e9, 136e9))
        top = _top_level(fig)
        self.assertAlmostEqual(sum(value for _, value in top.values()), 148e9)
        label, value = top[space.UNALLOCATED_ID]
        self.assertAlmostEqual(value, 30e9)
        self.assertTrue(label.startswith("Non réparti par niveau"), label)
        self.assertIn("(20%)", label)  # 30 of 148
        primary_label, _ = top["Primary Education"]
        self.assertIn("(63%)", primary_label)  # 93 of 148

    def test_without_a_sector_total_the_table_total_is_the_sector(self):
        fig = space._sub_func_fig(_sub_func_rows(), "Education", "XOF", lang="en")
        top = _top_level(fig)
        self.assertAlmostEqual(top[space.UNALLOCATED_ID][1], 30e9)
        self.assertTrue(top[space.UNALLOCATED_ID][0].startswith("Not broken down by level"))

    def test_no_box_when_every_amount_has_a_sub_function(self):
        fig = space._sub_func_fig(_sub_func_rows(unclassified=0.0), "Education", "XOF", lang="fr",
                                  sector_total=(118e9, 109e9))
        self.assertNotIn(space.UNALLOCATED_ID, _top_level(fig))

    def test_health_with_its_two_levels(self):
        data = pd.DataFrame({
            "func_sub": ["Primary and Secondary Health", "Tertiary and Quaternary Health", None],
            "geo0": ["Regional", "Regional", "Central"],
            "expenditure": [20e9, 10e9, 60e9],
            "real_expenditure": [18e9, 9e9, 54e9],
        })
        fig = space._sub_func_fig(data, "Health", "XOF", lang="fr", sector_total=(90e9, 81e9))
        top = _top_level(fig)
        self.assertAlmostEqual(top[space.UNALLOCATED_ID][1], 60e9)
        self.assertIn("(67%)", top[space.UNALLOCATED_ID][0])

    def test_no_sub_function_at_all_stays_empty(self):
        data = _sub_func_rows().assign(func_sub=None)
        fig = space._sub_func_fig(data, "Health", "XOF", lang="fr", sector_total=(148e9, 136e9))
        self.assertEqual(fig.data, ())

    def test_labels_are_never_drawn_below_a_readable_size(self):
        fig = space._sub_func_fig(_sub_func_rows(), "Education", "XOF", lang="fr",
                                  sector_total=(148e9, 136e9))
        self.assertGreaterEqual(fig.layout.uniformtext.minsize, 11)
        self.assertEqual(fig.layout.uniformtext.mode, "hide")
        # A sub-function's header holds its two lines: name, then amount and share.
        self.assertGreaterEqual(fig.data[0].marker.pad.t, 2 * 14)


if __name__ == "__main__":
    unittest.main()
