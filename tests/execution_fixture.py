"""A small boost.tgo_execution extract: both budget types, null keys, an
external (RE) capital line, and years on both sides of END_YEAR."""
import pandas as pd

from constants import END_YEAR

PRIOR_YEAR = END_YEAR - 1
YEAR = END_YEAR
OPEN_YEAR = END_YEAR + 1

_KEYS = dict(
    country_name="Togo", budget_type_code="1", budget_type="BUDGET GENERAL",
    admin2_code="210", admin2="MINISTERE DE L'ECONOMIE ET DES FINANCES", admin2_short="MEF",
    prog_code="003", prog="PILOTAGE ET SOUTIEN AUX SERVICES DU MEF",
    func_code="701", func="General public services", func_sub=None,
    econ1_code="2", econ1="PERSONNEL", econ="Wage bill",
    funding_code="RI_HORS_PROJETS", funding="Ressources internes hors projets", pip=False, funder=None,
    gender_code="0", gender="SCORE NON CIBLE", green_code="90", green="NON COTEE",
    social_code="1", social="DEPENSES NON SOCIALES", project_code=None, project=None,
)
_MEASURES = ("dotation_ae", "dotation_initiale", "dotation_finale", "engagement",
             "liquidation", "ordonnancer_ri", "ordonnancer_re", "ordonnancer")

_MEF_CAPITAL = dict(econ1_code="5", econ1="DEPENSES EN CAPITAL", econ="Capital expenditures")
_HEALTH = dict(admin2_code="320", admin2="MINISTERE DE LA SANTE", admin2_short="MS",
               prog_code="010", prog="SANTE DE BASE", func_code="707", func="Health")

# (overrides, dotation_ae, initiale, finale, engagement, liquidation, ord_ri, ord_re, ord)
_ROWS = [
    (dict(year=YEAR), 100, 100, 120, 110, 105, 100, 0, 100),
    (dict(year=YEAR, **_MEF_CAPITAL, funding_code="RI_PROJETS", funding="Ressources internes projets",
          pip=True, project_code="P1", project="ROUTE A", gender_code="4", gender="SCORE SIGNIFICATIF",
          green_code="11", green="ADAPTATION FAVORABLE", social_code="2", social="DEPENSES SOCIALES"),
     300, 200, 250, 200, 180, 150, 0, 150),
    (dict(year=YEAR, **_MEF_CAPITAL, prog_code="004", prog="MOBILISATION DES RESSOURCES",
          funding_code="RE", funding="Ressources externes", pip=True, funder="BANQUE MONDIALE",
          project_code="P2", project="HOPITAL B", gender_code="5", gender="SCORE PRINCIPAL",
          green_code=None, green=None, social_code=None, social=None),
     0, 400, 400, 0, 0, 0, 300, 300),
    (dict(year=YEAR, **_HEALTH, budget_type_code="2", budget_type="COMPTES SPECIAUX DU TRESOR",
          econ1_code="3", econ1="BIENS ET SERVICES", econ="Goods and services",
          social_code="2", social="DEPENSES SOCIALES"),
     50, 60, 50, 40, 40, 40, 0, 40),
    ({**_HEALTH, **_MEF_CAPITAL, "year": YEAR, "func_code": None, "func": None,
      "gender_code": None, "gender": None},
     30, 30, 0, 0, 0, 10, 0, 10),
    (dict(year=YEAR, **{**_HEALTH, "prog_code": None, "prog": None},
          econ1_code="4", econ1="TRANSFERTS COURANTS", econ="Other grants and transfers"),
     80, 70, 80, 80, 80, 80, 0, 80),
    (dict(year=PRIOR_YEAR), 900, 900, 1000, 960, 955, 950, 0, 950),
    (dict(year=OPEN_YEAR), 5000, 5000, 5000, 0, 0, 0, 0, 0),
]

# Totals of YEAR, by hand from the rows above.
TOTAL_FINALE = 900
TOTAL_INITIALE = 860
TOTAL_ORDONNANCER = 680


def execution_frame():
    rows = []
    for overrides, *values in _ROWS:
        row = {**_KEYS, **overrides}
        row.update(zip(_MEASURES, values))
        rows.append(row)
    return pd.DataFrame(rows)
