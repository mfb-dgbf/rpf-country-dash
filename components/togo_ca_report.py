"""The compte administratif, spending side, of one ministry for one budget year,
in the layout of the DGBF's « CA-DEPENSES » workbook, from boost.tgo_execution_detail.

Five sheets: forecasts (Dep_prev), execution recap (Dep_execut° RECAP), the detail by
programme or dotation, service, nature and budget line (DEP-execution -DETAILS),
commitments not liquidated and liquidations not ordered (DELNO), and programmes ×
natures (Tab croisé). Crédits votés are the final allocation (dotation finale);
ordonnancement is the total on internal and external resources. AE columns are
filled on capital natures only, as in the template. Lines are summed at econ3 level.
"""
import re

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from components.xlsx_output import workbook_bytes

AE, CP, ENG, LIQ, ORD = "dotation_ae", "dotation_finale", "engagement", "liquidation", "ordonnancer"
AMOUNTS = [AE, CP, ENG, LIQ, ORD]

NATURES = ["dette", "personnel", "biens", "transferts", "hors_pip", "pip_ri", "pip_re"]
CAPITAL_NATURES = {"hors_pip", "pip_ri", "pip_re"}
RECURRENT_NATURES = {"1": "dette", "2": "personnel", "3": "biens", "4": "transferts"}
LABELS = {
    "dette": "Charges financières dette",
    "personnel": "Dépenses de personnel",
    "biens": "Dépenses de biens et services",
    "transferts": "Dépenses de transferts courants",
    "hors_pip": "Dépenses d'investissement hors PIP",
    "pip_ri": "Dépenses d'investissement sur PIP/RI",
    "pip_re": "Dépenses d'investissement sur PIP/RE",
}
SHORT_LABELS = {
    "dette": "Charges financières dette",
    "personnel": "Personnel",
    "biens": "Biens et services",
    "transferts": "Transferts courants",
    "hors_pip": "Investissement hors PIP",
    "pip_ri": "Investissement PIP/RI",
    "pip_re": "Investissement PIP/RE",
}
CAPITAL = "5"
EXTERNAL = "RE"
OUTSIDE_PIP = "RI_HORS_PROJETS"

AMOUNT_FORMAT = "#,##0"
RATE_FORMAT = "0.00%"
_BOLD = Font(bold=True)
_HEADER_FILL = PatternFill("solid", fgColor="DDE4EE")
_TOTAL_FILL = PatternFill("solid", fgColor="F2F2F2")
_THIN = Side(style="thin", color="A0A0A0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(wrap_text=True, horizontal="center", vertical="center")
_LABEL = Alignment(wrap_text=True, vertical="top")


# --- Data ----------------------------------------------------------------------

def nature(econ1_code, funding_code):
    """The CA nature of a line: debt, personnel, goods and services, transfers, or
    capital outside the PIP, in the PIP on internal resources, on external resources."""
    if econ1_code == CAPITAL:
        if funding_code == EXTERNAL:
            return "pip_re"
        return "hors_pip" if funding_code == OUTSIDE_PIP else "pip_ri"
    if econ1_code not in RECURRENT_NATURES:
        raise ValueError(f"economic nature {econ1_code!r} has no place in the compte administratif")
    return RECURRENT_NATURES[econ1_code]


def is_dotation(label):
    return (label or "").strip().upper().startswith("DOTATION")


def _without_dotation_prefix(label):
    return re.sub(r"^\s*DOTATION\s*:?\s*", "", label or "", flags=re.IGNORECASE)


def _prepare(df, year, admin2_code):
    d = df[(df["year"] == year) & (df["admin2_code"] == admin2_code)].copy()
    if d.empty:
        raise ValueError(f"no execution lines for ministry {admin2_code} in {year}")
    d["nature"] = [nature(e, f) for e, f in zip(d["econ1_code"], d["funding_code"])]
    d["capital"] = d["nature"].isin(CAPITAL_NATURES)
    d["dotation"] = [is_dotation(label) for label in d["prog"]]
    return d


def _figures(rows, show_ae=None):
    """Forecast and execution amounts of ``rows``. AE and AE engaged are the
    capital lines' and are shown when ``show_ae`` (default: rows hold capital lines)."""
    capital = rows[rows["capital"]]
    if show_ae is None:
        show_ae = not capital.empty
    sums = rows[AMOUNTS].sum()
    return {
        "ae": capital[AE].sum() if show_ae else None,
        "cp": sums[CP],
        "eng_ae": capital[ENG].sum() if show_ae else None,
        "eng": sums[ENG],
        "liq": sums[LIQ],
        "ord": sums[ORD],
    }


def _of(rows, key):
    return rows[rows["nature"] == key]


# --- Cells ---------------------------------------------------------------------

def _style(ws, row, col, to=None, fill=None, bold=False, align=None):
    end_row, end_col = to or (row, col)
    if (end_row, end_col) != (row, col):
        ws.merge_cells(start_row=row, start_column=col, end_row=end_row, end_column=end_col)
    for r in range(row, end_row + 1):
        for c in range(col, end_col + 1):
            cell = ws.cell(r, c)
            cell.border = _BORDER
            if fill:
                cell.fill = fill
            if bold:
                cell.font = _BOLD
            if align:
                cell.alignment = align
    return ws.cell(row, col)


def _header(ws, row, col, text, to=None):
    _style(ws, row, col, to, fill=_HEADER_FILL, bold=True, align=_CENTER).value = text


def _text(ws, row, col, value, bold=False, to=None):
    cell = _style(ws, row, col, to, bold=bold, align=_LABEL)
    cell.value = value
    return cell


def _amount(ws, row, col, value, bold=False):
    cell = _style(ws, row, col, bold=bold)
    if value is not None and not pd.isna(value):
        cell.value = int(round(value))
        cell.number_format = AMOUNT_FORMAT


def _rate(ws, row, col, numerator, denominator, bold=False):
    cell = _style(ws, row, col, bold=bold)
    if numerator is not None and denominator:
        cell.value = float(numerator) / float(denominator)
        cell.number_format = RATE_FORMAT


def _write_forecast(ws, row, figures, bold=False):
    _amount(ws, row, 5, figures["ae"], bold)
    _amount(ws, row, 6, figures["cp"], bold)


def _write_execution(ws, row, figures, bold=False):
    """Columns E to N: AE, CP, AE and CP engaged, their rates, liquidation, ordonnancement."""
    _write_forecast(ws, row, figures, bold)
    _amount(ws, row, 7, figures["eng_ae"], bold)
    _amount(ws, row, 8, figures["eng"], bold)
    _rate(ws, row, 9, figures["eng_ae"], figures["ae"], bold)
    _rate(ws, row, 10, figures["eng"], figures["cp"], bold)
    _amount(ws, row, 11, figures["liq"], bold)
    _rate(ws, row, 12, figures["liq"], figures["cp"], bold)
    _amount(ws, row, 13, figures["ord"], bold)
    _rate(ws, row, 14, figures["ord"], figures["cp"], bold)


def _column_header(ws, row, execution):
    """The three header rows of Dep_prev (``execution`` False) or of RECAP and DETAILS."""
    _header(ws, row, 1, "Imputation budgétaire", to=(row + 2, 3))
    _header(ws, row, 4, "Libellé du chapitre et de la nature ")
    _header(ws, row + 1, 4, "économique des dépenses")
    _header(ws, row + 2, 4, None)
    _header(ws, row, 5, "Crédits votés : LFI/LFR", to=(row, 6))
    columns = [("AE", "(A1)"), ("CP", "(A2)")]
    if execution:
        for col, title in ((7, "Crédits engagés "), (9, "Taux d'engagement"), (11, "Liquidation"),
                           (13, "Ordonnancement ")):
            _header(ws, row, col, title, to=(row, col + 1))
        columns += [("AE", "(B1)"), ("CP", "(B2)"), ("AE", "C1=B1/A1"), ("CP", "C2=B2/A2"),
                    ("Montant", "(D)"), ("Taux", "E=D/A2"), ("Montant", "(F)"), ("Taux", "G=F/A2")]
    for j, (second, third) in enumerate(columns, start=5):
        _header(ws, row + 1, j, second)
        _header(ws, row + 2, j, third)


def _widths(ws, widths, rest=16):
    for c in range(1, ws.max_column + 1):
        letter = get_column_letter(c)
        ws.column_dimensions[letter].width = widths.get(letter, rest)


_DETAIL_WIDTHS = {"A": 22, "B": 11, "C": 7, "D": 50, "I": 10, "J": 10, "L": 10, "N": 10}


class _Ministry:
    def __init__(self, d, year, code):
        self.d = d
        self.year = year
        self.code = code
        self.name = d["admin2"].iloc[0]
        self.short = d["admin2_short"].iloc[0] or self.name
        self.programmes = d[~d["dotation"]]
        self.dotations = d[d["dotation"]]

    @property
    def title(self):
        return f"Section {self.code} : {self.name} ({self.short})" if self.short != self.name \
            else f"Section {self.code} : {self.name}"

    def programme_natures(self):
        present = set(self.programmes["nature"])
        return [n for n in NATURES if n != "dette" or n in present]

    def blocks(self):
        """(caption, rows, natures, total label) of the three recap blocks."""
        return [
            (f"Récapitulation des dépenses des programmes {self.name}", self.programmes,
             self.programme_natures(), f"Total du {self.short}"),
            (f"Récapitulation des dépenses des dotations du {self.short}", self.dotations, NATURES,
             "Total des dotations"),
            (f"Total des dépenses du {self.name} (programmes et dotations)", self.d, NATURES,
             f"Cumul des crédits du {self.short} (Programmes et dotations)"),
        ]


def _recap_block(ws, row, caption, rows, natures, total_label, execution):
    """Nature rows under a caption, then the block's total row; returns the next row."""
    write = _write_execution if execution else _write_forecast
    _text(ws, row, 1, caption, to=(row + len(natures) - 1, 3))
    for i, key in enumerate(natures):
        _text(ws, row + i, 4, LABELS[key])
        write(ws, row + i, _figures(_of(rows, key), show_ae=key in CAPITAL_NATURES))
    row += len(natures)
    _text(ws, row, 1, total_label, bold=True, to=(row, 4))
    write(ws, row, _figures(rows, show_ae=True), bold=True)
    return row + 1


def _recap_sheet(wb, ministry, name, execution):
    ws = wb.create_sheet(name)
    ws["A1"] = ministry.title
    ws.cell(1, 14 if execution else 6, f"Exercice {ministry.year}")
    row = 2
    for caption, rows, natures, total_label in ministry.blocks():
        _column_header(ws, row, execution)
        row = _recap_block(ws, row + 3, caption, rows, natures, total_label, execution) + 1
    _widths(ws, {"A": 14, "B": 8, "C": 8, "D": 40, **({"I": 10, "J": 10, "L": 10, "N": 10} if execution else {})})


# --- DETAILS -------------------------------------------------------------------

def _detail_unit(ws, row, rows, heading, cumul_label, total_label):
    """A programme or dotation: heading, services with their natures and lines,
    the cumul by nature and the total; returns the next row."""
    _text(ws, row, 1, heading, bold=True, to=(row, 14))
    row += 1
    for (action, admin4), service in rows.groupby(["action_code", "admin4_code"], sort=True):
        _text(ws, row, 1, admin4, bold=True)
        _text(ws, row, 2, None)
        _text(ws, row, 3, None)
        _text(ws, row, 4, service["admin4"].iloc[0], bold=True)
        _write_execution(ws, row, _figures(service), bold=True)
        row += 1
        for key in NATURES:
            part = _of(service, key)
            if part.empty:
                continue
            show_ae = key in CAPITAL_NATURES
            _text(ws, row, 4, LABELS[key], bold=True)
            _write_execution(ws, row, _figures(part, show_ae))
            row += 1
            for (func3, admin5, econ3), line in part.groupby(["func3_code", "admin5_code", "econ3_code"],
                                                             sort=True):
                _text(ws, row, 1, f"{action} {admin4}")
                _text(ws, row, 2, f"{func3}{admin5}")
                _text(ws, row, 3, econ3)
                _text(ws, row, 4, line["econ3"].iloc[0])
                _write_execution(ws, row, _figures(line, show_ae))
                row += 1
    natures = [key for key in NATURES if not _of(rows, key).empty]
    _text(ws, row, 1, cumul_label, bold=True, to=(row + len(natures) - 1, 3))
    for i, key in enumerate(natures):
        _text(ws, row + i, 4, LABELS[key])
        _write_execution(ws, row + i, _figures(_of(rows, key), key in CAPITAL_NATURES))
    row += len(natures)
    _text(ws, row, 1, total_label, bold=True, to=(row, 4))
    _write_execution(ws, row, _figures(rows), bold=True)
    return row + 1


def _details(wb, ministry):
    ws = wb.create_sheet("DEP-execution -DETAILS")
    ws["A1"] = ministry.title
    ws["N1"] = f"Exercice {ministry.year}"
    _column_header(ws, 2, execution=True)
    ws.print_title_rows = "2:4"
    row = 5
    blocks = ministry.blocks()
    for code, rows in ministry.programmes.groupby("prog_code", sort=True):
        label = rows["prog"].iloc[0]
        row = _detail_unit(ws, row, rows, f"Programme {code} : {label}", f"Cumul programme {code}",
                           f"Total des dépenses du programme {code}")
    row = _recap_block(ws, row, *blocks[0], execution=True)
    for code, rows in ministry.dotations.groupby("prog_code", sort=True):
        label = _without_dotation_prefix(rows["prog"].iloc[0])
        row = _detail_unit(ws, row, rows, f"Dotation {code} : {label}", f"Cumul dotation {code}",
                           f"Total des dépenses de la dotation {code}")
    row = _recap_block(ws, row, *blocks[1], execution=True)
    _recap_block(ws, row, *blocks[2], execution=True)
    _widths(ws, _DETAIL_WIDTHS)


# --- DELNO ---------------------------------------------------------------------

def _delno_header(ws, row, reference):
    texts = [
        (1, ["Référence", "du", reference, None]),
        (2, ["Nature économique", "de la dépense", None, None]),
        (9, ["Dépenses", "engagés non", "liquidées sur CP", "E= C-B2"]),
        (10, ["Dépenses engagées", "liquidées non", "ordonnancées/CP", "F= D-C"]),
    ]
    for col, lines in texts:
        for i, text in enumerate(lines):
            _header(ws, row + i, col, text)
    for col, title, first, second in ((3, "Crédits votés LFI/LFR", ("en AE", "(A1)"), ("en CP", "(A2)")),
                                      (5, "Crédits engagés", ("en AE", "(B1)"), ("en CP", "(B2)")),
                                      (7, "Dépenses ", ("liquidées", "(C )"), ("ordonnancées", "(D)")),
                                      (11, "Reste à payer budgétaire", ("sur AE", "G1= D-B1"),
                                       ("sur CP", "G2= D-B2"))):
        _header(ws, row, col, title, to=(row, col + 1))
        for j, (third, fourth) in enumerate((first, second)):
            _header(ws, row + 1, col + j, third)
            _header(ws, row + 2, col + j, fourth)
            _header(ws, row + 3, col + j, None)


def _delno_values(ws, row, figures, capital_rest, bold=False):
    """C to L; ``capital_rest`` is the remainder on AE (H - B1) of capital lines, or None."""
    eng, liq, ord_ = figures["eng"], figures["liq"], figures["ord"]
    for col, value in ((3, figures["ae"]), (4, figures["cp"]), (5, figures["eng_ae"]), (6, eng), (7, liq),
                       (8, ord_), (9, liq - eng), (10, ord_ - liq), (11, capital_rest), (12, ord_ - eng)):
        _amount(ws, row, col, value, bold)


def _delno_rows(ws, row, rows, reference, labels):
    """A programme or dotation by nature; returns (next row, capital remainder on AE)."""
    natures = [key for key in NATURES if not _of(rows, key).empty]
    _text(ws, row, 1, reference, to=(row + len(natures) - 1, 1))
    rest = None
    for i, key in enumerate(natures):
        capital = key in CAPITAL_NATURES
        figures = _figures(_of(rows, key), capital)
        line_rest = figures["ord"] - figures["eng_ae"] if capital else None
        if capital:
            rest = (rest or 0) + line_rest
        _text(ws, row + i, 2, labels[key])
        _delno_values(ws, row + i, figures, line_rest)
    return row + len(natures), rest


def _delno_total(ws, row, label, rows, rest):
    figures = _figures(rows, show_ae=True)
    _text(ws, row, 1, label, bold=True, to=(row, 2))
    _delno_values(ws, row, figures, rest, bold=True)


def _delno(wb, ministry):
    ws = wb.create_sheet("DELNO")
    ws["A1"] = ministry.title
    ws["L1"] = f"Exercice {ministry.year}"
    _delno_header(ws, 2, "programme")
    row = 6
    for code, rows in ministry.programmes.groupby("prog_code", sort=True):
        row, rest = _delno_rows(ws, row, rows, f"Prog : {code}", SHORT_LABELS)
        _delno_total(ws, row, f"Total programme {code}", rows, rest)
        row += 1
    natures = ministry.programme_natures()
    _text(ws, row, 1, "Cumul", to=(row + len(natures) - 1, 1))
    rest = None
    for i, key in enumerate(natures):
        capital = key in CAPITAL_NATURES
        figures = _figures(_of(ministry.programmes, key), capital)
        line_rest = figures["ord"] - figures["eng_ae"] if capital else None
        if capital:
            rest = (rest or 0) + line_rest
        _text(ws, row + i, 2, SHORT_LABELS[key])
        _delno_values(ws, row + i, figures, line_rest)
    row += len(natures)
    _delno_total(ws, row, f"Total section {ministry.code}", ministry.programmes, rest)
    row += 3
    _delno_header(ws, row, "Dotations")
    row += 4
    rest = None
    for code, rows in ministry.dotations.groupby("prog_code", sort=True):
        row, part_rest = _delno_rows(ws, row, rows, f"Dotation {code}", LABELS)
        if part_rest is not None:
            rest = (rest or 0) + part_rest
    _delno_total(ws, row, "Total dotations", ministry.dotations, rest)
    _widths(ws, {"A": 16, "B": 34}, 16)
    ws.page_setup.orientation = "landscape"


# --- Tab croisé ----------------------------------------------------------------

_CROSS = [("personnel", ["personnel"]), ("biens", ["biens"]), ("transferts", ["transferts"]),
          ("hors_pip", ["hors_pip"]), ("pip", ["pip_ri", "pip_re"])]


def _cross_values(ws, row, rows, bold=False):
    for i, (_, keys) in enumerate(_CROSS):
        part = rows[rows["nature"].isin(keys)]
        col = 4 + 2 * i
        if part.empty:
            _amount(ws, row, col, None, bold)
            _amount(ws, row, col + 1, None, bold)
        else:
            _amount(ws, row, col, part[CP].sum(), bold)
            _amount(ws, row, col + 1, part[ORD].sum(), bold)


def _tab_croise(wb, ministry):
    ws = wb.create_sheet("Tab croisé")
    ws["A3"] = ministry.title
    ws["M3"] = f"Exercice {ministry.year}"
    _header(ws, 4, 1, "Numéro programme", to=(6, 1))
    _header(ws, 4, 2, "Intitulé des Programmes ", to=(6, 3))
    _header(ws, 4, 4, "Dépenses courantes", to=(4, 9))
    _header(ws, 4, 10, "Dépenses en capital", to=(4, 13))
    for i, title in enumerate(["Dépenses de personnel", "Dépenses de biens et services",
                               "Dépenses de transferts courants", "Dép. d'investissement hors PIP",
                               "Dép. d'investissement sur PIP"]):
        col = 4 + 2 * i
        _header(ws, 5, col, title, to=(5, col + 1))
        _header(ws, 6, col, "Prévision")
        _header(ws, 6, col + 1, "Exécution")
    row = 7
    for code, rows in ministry.programmes.groupby("prog_code", sort=True):
        _text(ws, row, 1, code)
        _text(ws, row, 2, rows["prog"].iloc[0], to=(row, 3))
        _cross_values(ws, row, rows)
        row += 1
    _text(ws, row, 1, "Total", bold=True, to=(row, 3))
    _cross_values(ws, row, ministry.programmes, bold=True)
    _widths(ws, {"A": 12, "B": 30, "C": 20}, 16)
    ws.page_setup.orientation = "landscape"


def build_ca_report(df_detail, year, admin2_code):
    """The ministry's compte administratif for the year from the normalised detail table, as xlsx bytes."""
    ministry = _Ministry(_prepare(df_detail, year, str(admin2_code)), year, str(admin2_code))
    wb = Workbook()
    wb.remove(wb.active)
    _recap_sheet(wb, ministry, "Dep_prev", execution=False)
    _recap_sheet(wb, ministry, "Dep_execut° RECAP", execution=True)
    _details(wb, ministry)
    _delno(wb, ministry)
    _tab_croise(wb, ministry)
    return workbook_bytes(wb)
