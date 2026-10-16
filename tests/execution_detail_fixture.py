"""Budget lines of two ministries for the DGBF workbook tests: programmes and
dotations, every nature, internal and external capital, a CST line and a line
of the year before. ``detail_frame`` is shaped like boost.tgo_execution_detail
and ``fact_frame`` like boost.tgo_execution, both summed from the same lines."""
import pandas as pd

from constants import END_YEAR
from components import togo_execution as te

YEAR = END_YEAR
PRIOR_YEAR = END_YEAR - 1

_MEF = dict(admin2_code="210", admin2="MINISTERE DE L'ECONOMIE ET DES FINANCES", admin2_short="MEF")
_SANTE = dict(admin2_code="610", admin2="MINISTERE DE LA SANTE ET DE L'HYGIENE PUBLIQUE",
              admin2_short="MSHP")
_P003 = dict(prog_code="003", prog="PILOTAGE ET SOUTIEN AUX SERVICES DU MEF")
_P004 = dict(prog_code="004", prog="MOBILISATION DES RESSOURCES FINANCIERES")
_P900 = dict(prog_code="900", prog="DOTATION : CHARGES FINANCIERES DE LA DETTE PUBLIQUE")
_P902 = dict(prog_code="902", prog="DOTATION : DEPENSES COMMUNES D'INVESTISSEMENT")
_P042 = dict(prog_code="042", prog="PILOTAGE ET SOUTIEN AUX SERVICES DU MSHP")
_P043 = dict(prog_code="043", prog="LUTTE CONTRE LA MALADIE")

_ECON = {
    "661112": ("2", "PERSONNEL", "66", "CHARGES DE PERSONNEL", "661", "Traitements et salaires en espèces", "Wage bill"),
    "661114": ("2", "PERSONNEL", "66", "CHARGES DE PERSONNEL", "661", "Traitements et salaires en espèces", "Wage bill"),
    "601111": ("3", "BIENS ET SERVICES", "60", "ACHATS", "601", "Matières, matériel et fournitures", "Goods and services"),
    "611111": ("3", "BIENS ET SERVICES", "61", "SERVICES", "611", "Frais de transport et de mission", "Goods and services"),
    "649111": ("4", "TRANSFERTS COURANTS", "64", "TRANSFERTS", "649", "Autres transferts", "Other grants and transfers"),
    "671111": ("1", "CHARGES FINANCIERES DE LA DETTE", "67", "INTERETS", "671", "Intérêts de la dette", "Interest on debt"),
    "211111": ("5", "DEPENSES EN CAPITAL", "21", "IMMOBILISATIONS INCORPORELLES", "211", "Frais de recherche", "Capital expenditures"),
    "241111": ("5", "DEPENSES EN CAPITAL", "24", "MATERIEL", "241", "Mobilier et matériel de bureau", "Capital expenditures"),
    "234111": ("5", "DEPENSES EN CAPITAL", "23", "BATIMENTS", "234", "Ouvrages", "Capital expenditures"),
    "231111": ("5", "DEPENSES EN CAPITAL", "23", "BATIMENTS", "231", "Bâtiments administratifs", "Capital expenditures"),
}
_FUNCTIONS = {"01": "General public services", "04": "Economic affairs", "07": "Health",
              "10": "Social protection"}
_FUNDING = {"RI_HORS_PROJETS": "1100", "RI_PROJETS": "5101", "RI_CONTREPARTIE": "2101", "RE": None}

# (ministry, programme, action, admin4 code, admin4 label, econ4, funding, admin5 for RE,
#  funder, func, gender, green, social, budget type,
#  dotation_ae, finale, engagement, liquidation, ordonnancer_ri, ordonnancer_re)
_LINES = [
    (_MEF, _P003, "0031", "1111080041000", "CABINET DU MINISTRE", "661112", "RI_HORS_PROJETS", None, None,
     "01", "0", "90", "1", "1", 0, 1000, 800, 800, 800, 0),
    (_MEF, _P003, "0031", "1111080041000", "CABINET DU MINISTRE", "661114", "RI_HORS_PROJETS", None, None,
     "01", "0", "90", "1", "1", 0, 500, 300, 300, 300, 0),
    (_MEF, _P003, "0031", "1111080041000", "CABINET DU MINISTRE", "601111", "RI_HORS_PROJETS", None, None,
     "01", "0", "90", "1", "1", 0, 400, 350, 340, 330, 0),
    (_MEF, _P003, "0032", "1179001132000", "PROJET BONNE GOUVERNANCE FINANCIERE", "211111", "RI_CONTREPARTIE",
     None, None, "01", "4", "11", "2", "1", 900, 600, 500, 450, 450, 0),
    (_MEF, _P003, "0032", "1179001132000", "PROJET BONNE GOUVERNANCE FINANCIERE", "211111", "RE",
     "4101", "BANQUE MONDIALE/DONS", "04", "5", "31", "1", "1", 2000, 1200, 0, 0, 0, 700),
    (_MEF, _P004, "0041", "1141010041004", "UNITE DE POLITIQUE FISCALE", "649111", "RI_HORS_PROJETS", None, None,
     "01", "0", "90", "2", "1", 0, 2000, 2000, 2000, 2000, 0),
    (_MEF, _P004, "0041", "1141010041004", "UNITE DE POLITIQUE FISCALE", "241111", "RI_HORS_PROJETS", None, None,
     "01", "0", "90", "1", "1", 300, 300, 250, 250, 250, 0),
    (_MEF, _P900, "9001", "1131010042005", "CHARGES FINANCIERES DE LA DETTE", "671111", "RI_HORS_PROJETS",
     None, None, "01", "0", "90", "1", "1", 0, 5000, 5200, 5200, 5200, 0),
    (_MEF, _P902, "9021", "1179000308000", "PROG D'APPUI AUX POPULATIONS VULNERABLES", "234111", "RI_PROJETS",
     None, None, "10", "0", "13", "2", "1", 1500, 1500, 100, 100, 100, 0),
    (_SANTE, _P042, "0421", "1111080100000", "CABINET DU MINISTRE", "661112", "RI_HORS_PROJETS", None, None,
     "07", "0", "90", "2", "1", 0, 700, 650, 650, 650, 0),
    (_SANTE, _P043, "0431", "1179001200000", "PROJET SANTE COMMUNAUTAIRE", "231111", "RE",
     "4120", "FONDS MONDIAL/DONS", "07", "4", "61", "2", "1", 800, 800, 0, 0, 0, 200),
    (_SANTE, _P043, "0432", "2191000000000", "FONDS SPECIAL", "611111", "RI_HORS_PROJETS", None, None,
     "07", "0", "13", "1", "2", 0, 90, 90, 90, 90, 0),
]
_PRIOR_LINE = (_MEF, _P003, "0031", "1111080041000", "CABINET DU MINISTRE", "661112", "RI_HORS_PROJETS", None,
               None, "01", "0", "90", "1", "1", 0, 999, 999, 999, 999, 0)

# Totals of YEAR, by hand from the lines above.
TOTAL_AE = 5500
TOTAL_FINALE = 14090
TOTAL_ENGAGEMENT = 10240
TOTAL_LIQUIDATION = 10180
TOTAL_ORDONNANCER_RI = 10170
TOTAL_ORDONNANCER_RE = 900
TOTAL_ORDONNANCER = 11070

_FUNDING_LABELS = {"RI_HORS_PROJETS": "Ressources internes hors projets",
                   "RI_PROJETS": "Ressources internes, projets",
                   "RI_CONTREPARTIE": "Fonds de contrepartie", "RE": "Ressources externes"}


def _line(year, spec):
    (ministry, programme, action, admin4_code, admin4, econ4, funding, re_admin5, funder, func,
     gender, green, social, budget_type, ae, finale, engagement, liquidation, ord_ri, ord_re) = spec
    econ1_code, econ1, econ2_code, econ2, econ3_code, econ3, econ = _ECON[econ4]
    admin5 = re_admin5 or _FUNDING[funding]
    func3 = func + "10"
    capital = econ1_code == "5"
    return {
        "country_name": "Togo", "year": year,
        "budget_type_code": budget_type,
        "budget_type": "BUDGET GENERAL" if budget_type == "1" else "COMPTES SPECIAUX DU TRESOR",
        **ministry, **programme, "action_code": action, "action": f"ACTION {action}",
        "admin3_code": admin4_code[:2], "admin3": f"SERVICES {admin4_code[:2]}",
        "admin4_code": admin4_code, "admin4": admin4, "admin5_code": admin5, "func3_code": func3,
        "econ1_code": econ1_code, "econ1": econ1, "econ2_code": econ2_code, "econ2": econ2,
        "econ3_code": econ3_code, "econ3": econ3, "econ4_code": econ4, "econ4": f"LIGNE {econ4}",
        "econ": econ, "func_code": func, "func": _FUNCTIONS[func], "func_sub": None,
        "funding_code": funding, "funding": _FUNDING_LABELS[funding],
        "pip": funding != "RI_HORS_PROJETS", "funder": funder,
        "gender_code": gender, "gender": f"GENRE {gender}", "green_code": green, "green": f"VERT {green}",
        "social_code": social, "social": f"SOCIAL {social}",
        "project_code": admin4_code if capital else None, "project": admin4 if capital else None,
        "imputation": action + admin4_code + func3 + admin5 + econ4,
        "dotation_ae": ae, "dotation_initiale": finale, "dotation_finale": finale,
        "engagement": engagement, "liquidation": liquidation,
        "ordonnancer_ri": ord_ri, "ordonnancer_re": ord_re, "ordonnancer": ord_ri + ord_re,
    }


def _lines():
    return pd.DataFrame([_line(YEAR, spec) for spec in _LINES] + [_line(PRIOR_YEAR, _PRIOR_LINE)])


DETAIL_KEYS = [
    "country_name", "year", "budget_type_code", "budget_type",
    "admin2_code", "admin2", "admin2_short", "prog_code", "prog", "action_code", "action",
    "admin3_code", "admin3", "admin4_code", "admin4", "admin5_code", "func3_code",
    "econ1_code", "econ1", "econ2_code", "econ2", "econ3_code", "econ3", "econ4_code", "econ4",
    "funding_code", "funder", "gender_code", "green_code", "social_code", "imputation",
]
FACT_KEYS = ["year"] + te.KEY_COLUMNS[:16] + ["pip"] + te.KEY_COLUMNS[16:]


def _summed(keys):
    return _lines().groupby(keys, dropna=False, as_index=False)[te.MEASURES].sum()


def detail_frame():
    return _summed(DETAIL_KEYS)


def fact_frame():
    return _summed(FACT_KEYS)
