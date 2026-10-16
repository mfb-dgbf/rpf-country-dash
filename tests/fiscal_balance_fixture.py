"""Togo's official fiscal rows as the dashboard reads them from
indicator.togo_revenue_budget, loaded from the DGBF's solde_budgetaire.csv."""

import pandas as pd

DGBF_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
DGBF_REVENUE = [818.40e9, 830.45e9, 921.58e9, 1051.36e9, 1326.70e9, 1336.10e9, 1381.70e9]
DGBF_EXPENDITURE = [840.43e9, 1082.77e9, 1137.29e9, 1432.88e9, 1643.00e9, 1674.20e9, 1604.90e9]


def dgbf_file_rows():
    """2019-2022 carry a tax expenditure; the 2023-2025 table gives none."""
    return pd.DataFrame({
        "country_name": "Togo",
        "year": DGBF_YEARS,
        "revenue": DGBF_REVENUE,
        "expenditure": DGBF_EXPENDITURE,
        "tax_expenditure": [84.15e9, 76.06e9, 135.80e9, 160.34e9, None, None, None],
        "source": [
            "Rapport d'exécution du budget 2019",
            "Rapport d'exécution du budget 2020",
            "Rapport d'exécution du budget 2021",
            "Rapport d'exécution du budget 2022",
            "CBMT, tableau 7",
            "CBMT, tableau 7",
            "CBMT, tableau 7",
        ],
    })
