"""Togo's budget execution (table boost.tgo_execution): data preparation,
narratives, figures and tables of the « Exécution du budget » page.

The preparation functions take the normalised table and a year and return
plain DataFrames, so the page, the Excel report and the tests share them.
Rates are fractions: ordonnancer / dotation_finale, NaN where the final
budget is zero.
"""
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from babel.numbers import format_decimal
from dash import html

import server_store
from queries import QueryService
from components.budget_funding_execution import (
    DOMESTIC_FUNDED_COLOR,
    FOREIGN_FUNDED_COLOR,
    TOTAL_BUDGET_COLOR,
)
from constants import END_YEAR, EXECUTION_VIEW_COUNTRIES
from translations import t
from utils import (
    apply_locale,
    empty_plot,
    format_currency,
    format_year_axis,
    scale_currency_axes,
)
from viz_theme import DIVERGING_SCALE, QUALITATIVE, QUALITATIVE_ALT

CURRENCY_CODE = "XOF"

MEASURES = [
    "dotation_ae", "dotation_initiale", "dotation_finale", "engagement",
    "liquidation", "ordonnancer_ri", "ordonnancer_re", "ordonnancer",
]
KEY_COLUMNS = [
    "country_name", "budget_type_code", "budget_type", "admin2_code", "admin2",
    "admin2_short", "prog_code", "prog", "func_code", "func", "func_sub",
    "econ1_code", "econ1", "econ", "funding_code", "funding", "funder",
    "gender_code", "gender", "green_code", "green", "social_code", "social",
    "project_code", "project",
]

# Keys of boost.tgo_execution_detail, one row per budget line (imputation)
DETAIL_KEY_COLUMNS = [
    "country_name", "budget_type_code", "budget_type", "admin2_code", "admin2", "admin2_short",
    "prog_code", "prog", "action_code", "action", "admin3_code", "admin3", "admin4_code", "admin4",
    "admin5_code", "func3_code", "econ1_code", "econ1", "econ2_code", "econ2", "econ3_code", "econ3",
    "econ4_code", "econ4", "funding_code", "funder", "gender_code", "green_code", "social_code",
    "imputation",
]

CAPITAL_CODE = "5"
EXTERNAL_FUNDING = "RE"
INVESTMENT_GROUPS = ["hors_pip", "pip_ri", "re"]

# (code column, label column) of each budget tagging.
TAG_DIMENSIONS = {
    "gender": ("gender_code", "gender"),
    "green": ("green_code", "green"),
    "social": ("social_code", "social"),
}
# Codes the narrative counts: gender score significant (4) or principal (5);
# green codes rated favourable (x1); social spending (2).
TAGGED_CODES = {
    "gender": {"4", "5"},
    "green": {"11", "21", "31", "41", "51", "61"},
    "social": {"2"},
}

INITIAL_COLOR = QUALITATIVE[0]
FINAL_COLOR = QUALITATIVE[1]
ORDERED_COLOR = QUALITATIVE[3]
# One distinct colour for each of up to 18 tag codes (the green tagging has 17 and blanks).
TAG_PALETTE = QUALITATIVE + QUALITATIVE_ALT

_LOCALES = {"en": "en_US", "fr": "fr_FR", "pt": "pt_BR"}


# --- Loading ---------------------------------------------------------------

def normalise_execution(df, keys=KEY_COLUMNS):
    """Empty strings for null keys, zeros for null amounts, a boolean ``pip``.

    Null keys stay as their own group ("") in every breakdown, so each
    breakdown adds up to the year's total.
    """
    df = df.copy()
    for col in MEASURES:
        df[col] = pd.to_numeric(df[col]).fillna(0)
    for col in keys:
        if col in df.columns:
            df[col] = [("" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v))
                       for v in df[col]]
    if "pip" in df.columns:
        df["pip"] = [bool(v) if v is not None and not pd.isna(v) else False for v in df["pip"]]
    df["year"] = df["year"].astype(int)
    return df


def normalise_detail(df):
    """The detail table's rows, normalised as ``normalise_execution`` does."""
    return normalise_execution(df, DETAIL_KEY_COLUMNS)


def load_execution(country):
    """The execution table's rows for ``country``, or None when there are none."""
    if country not in EXECUTION_VIEW_COUNTRIES:
        return None
    df = server_store.lookup("togo_execution")
    if df is None or df.empty:
        return None
    df = df[df["country_name"] == country]
    return None if df.empty else df


def load_execution_detail(country, year, admin2_code=None):
    """The year's budget lines for ``country`` (one ministry's when ``admin2_code``
    is given), normalised, or None when there are none."""
    if country not in EXECUTION_VIEW_COUNTRIES:
        return None
    df = QueryService.get_instance().get_togo_execution_detail(year, admin2_code)
    df = df[df["country_name"] == country]
    return None if df.empty else normalise_detail(df)


# --- Preparation -----------------------------------------------------------

def _rate(numerator, denominator):
    return numerator / denominator.where(denominator != 0)


def _with_rate(df):
    df = df.copy()
    df["rate"] = _rate(df["ordonnancer"], df["dotation_finale"])
    return df


def _year(df, year):
    return df[df["year"] == year]


def _aggregate(df, keys, labels=()):
    """Measures summed by ``keys``; each label column takes its first value."""
    spec = {label: (label, "first") for label in labels}
    spec.update({m: (m, "sum") for m in MEASURES})
    return df.groupby(keys, as_index=False, sort=True).agg(**spec)


def execution_years(df, end_year=END_YEAR):
    """Years up to ``end_year`` present in the table, latest first."""
    return sorted({int(y) for y in df["year"] if y <= end_year}, reverse=True)


def yearly_totals(df, end_year=END_YEAR):
    totals = df[df["year"] <= end_year].groupby("year", as_index=False)[MEASURES].sum()
    return _with_rate(totals.sort_values("year"))


def spending_stages(df, year):
    """The year's totals per stage, with the final budget, commitments and
    liquidations split by internal (RI) and external (RE) funding."""
    d = _year(df, year)
    stages = {m: d[m].sum() for m in MEASURES}
    external = d["funding_code"] == EXTERNAL_FUNDING
    for m in ("dotation_finale", "engagement", "liquidation"):
        stages[f"{m}_re"] = d.loc[external, m].sum()
        stages[f"{m}_ri"] = d.loc[~external, m].sum()
    return stages


def by_ministry(df, year):
    ministries = _aggregate(_year(df, year), ["admin2_code"], ["admin2", "admin2_short"])
    ministries = ministries.sort_values(["dotation_finale", "admin2_code"], ascending=[False, True])
    return _with_rate(ministries.reset_index(drop=True))


def ministry_by_nature(df, year):
    cells = _aggregate(_year(df, year), ["admin2_code", "econ1_code"],
                       ["admin2", "admin2_short", "econ1"])
    return _with_rate(cells)


def by_nature(df, year):
    return _with_rate(_aggregate(_year(df, year), ["econ1_code"], ["econ1"]))


def by_function(df, year):
    return _with_rate(_aggregate(_year(df, year), ["func_code", "func"]))


def programmes(df, year, admin2_code=None):
    d = _year(df, year)
    if admin2_code is not None:
        d = d[d["admin2_code"] == admin2_code]
    rows = _aggregate(d, ["admin2_code", "prog_code", "econ1_code"], ["admin2", "prog", "econ1"])
    return _with_rate(rows)


def _capital(df, year):
    d = _year(df, year)
    return d[d["econ1_code"] == CAPITAL_CODE]


def investment_by_funding(df, year):
    """Capital spending split into outside the PIP, PIP on internal resources,
    and external resources; the three parts add up to capital spending."""
    capital = _capital(df, year)
    group = np.select(
        [capital["funding_code"] == EXTERNAL_FUNDING, capital["pip"]],
        ["re", "pip_ri"],
        "hors_pip",
    )
    parts = capital.assign(group=group).groupby("group")[MEASURES].sum()
    parts = parts.reindex(INVESTMENT_GROUPS, fill_value=0).reset_index()
    return _with_rate(parts)


def top_projects(df, year, n=20):
    capital = _capital(df, year)
    capital = capital[capital["project_code"] != ""]
    projects = _aggregate(capital, ["project_code"], ["project"])
    projects = projects.sort_values(["dotation_finale", "project_code"], ascending=[False, True])
    return _with_rate(projects.head(n).reset_index(drop=True))


def projects(df, year):
    """Capital lines by project, funding and funder."""
    rows = _aggregate(_capital(df, year), ["project_code", "funding_code", "funder"],
                      ["project", "funding"])
    return _with_rate(rows)


def tag_shares(df, year, dim):
    """The year's final budget and ordered amounts by tag code, with shares."""
    code_col, label_col = TAG_DIMENSIONS[dim]
    shares = _aggregate(_year(df, year), [code_col], [label_col])
    shares = shares.rename(columns={code_col: "code", label_col: "label"})
    for m, share in (("dotation_finale", "share_finale"), ("ordonnancer", "share_ordonnancer")):
        total = shares[m].sum()
        shares[share] = shares[m] / total if total else np.nan
    return _with_rate(shares)


# --- Formatting ------------------------------------------------------------

def format_amount(value, lang="en"):
    """A whole amount with the language's digit grouping: 7 136 488 000."""
    return format_decimal(int(round(value)), locale=_LOCALES.get(lang, "en_US"))


def format_rate(rate, lang="en"):
    if rate is None or pd.isna(rate):
        return "–"
    text = f"{rate * 100:.1f}"
    if lang in {"fr", "pt"}:
        text = text.replace(".", ",")
    return text + (" %" if lang == "fr" else "%")


def _money(value, lang):
    return format_currency(value, CURRENCY_CODE, lang=lang)


def label_or_unspecified(value, lang):
    return value if value else t("execution.unspecified", lang)


def nature_label(code, label, lang):
    key = f"execution.econ1.{code}"
    text = t(key, lang)
    return label_or_unspecified(label, lang) if text == key else text


def ministry_label(row, lang):
    return row["admin2_short"] or label_or_unspecified(row["admin2"], lang)


def unavailable(lang):
    message = t("error.data_unavailable", lang)
    return empty_plot(message), message


# --- Narratives ------------------------------------------------------------

def overview_narrative(totals, year, lang="en"):
    row = totals[totals["year"] == year]
    if row.empty or not row.iloc[0]["dotation_finale"]:
        return t("error.data_unavailable", lang)
    row = row.iloc[0]
    return t(
        "execution.narrative.overview", lang, year=year,
        initial=_money(row["dotation_initiale"], lang),
        final=_money(row["dotation_finale"], lang),
        ordered=_money(row["ordonnancer"], lang),
        rate=row["rate"] * 100,
    )


def stages_narrative(stages, year, lang="en"):
    final = stages["dotation_finale"]
    if not final:
        return t("error.data_unavailable", lang)
    ordered = stages["ordonnancer"]
    return t(
        "execution.narrative.stages", lang, year=year,
        final=_money(final, lang),
        engaged=stages["engagement"] / final * 100,
        liquidated=stages["liquidation"] / final * 100,
        ordered=ordered / final * 100,
        re_share=stages["ordonnancer_re"] / ordered * 100 if ordered else 0,
    )


def external_note(stages, year, lang="en"):
    """What external-resource lines carry before the payment-order stage."""
    engaged, liquidated = stages["engagement_re"], stages["liquidation_re"]
    if not engaged and not liquidated:
        return t("execution.note.external_none", lang, year=year)
    return t(
        "execution.note.external_some", lang, year=year,
        engaged=_money(engaged, lang), liquidated=_money(liquidated, lang),
        ordered=_money(stages["ordonnancer_re"], lang),
    )


def ministries_narrative(ministries, year, lang="en"):
    funded = ministries[ministries["dotation_finale"] > 0]
    if funded.empty:
        return t("error.data_unavailable", lang)
    top = funded.iloc[0]
    low = funded.loc[funded["rate"].idxmin()]
    high = funded.loc[funded["rate"].idxmax()]
    return t(
        "execution.narrative.ministries", lang, year=year, n=len(funded),
        top=ministry_label(top, lang), top_final=_money(top["dotation_finale"], lang),
        top_rate=top["rate"] * 100,
        low=ministry_label(low, lang), low_rate=low["rate"] * 100,
        high=ministry_label(high, lang), high_rate=high["rate"] * 100,
    )


def nature_narrative(natures, year, lang="en"):
    funded = natures[natures["dotation_finale"] > 0]
    if funded.empty:
        return t("error.data_unavailable", lang)
    low = funded.loc[funded["rate"].idxmin()]
    high = funded.loc[funded["rate"].idxmax()]
    return t(
        "execution.narrative.natures", lang, year=year,
        low=nature_label(low["econ1_code"], low["econ1"], lang), low_rate=low["rate"] * 100,
        high=nature_label(high["econ1_code"], high["econ1"], lang), high_rate=high["rate"] * 100,
    )


def programmes_narrative(rows, ministry, lang="en"):
    final = rows["dotation_finale"].sum()
    if rows.empty or not final:
        return t("error.data_unavailable", lang)
    ordered = rows["ordonnancer"].sum()
    return t(
        "execution.narrative.programmes", lang, ministry=ministry,
        n=rows["prog_code"].nunique(), final=_money(final, lang),
        ordered=_money(ordered, lang), rate=ordered / final * 100,
    )


def investment_narrative(parts, year, lang="en"):
    final = parts["dotation_finale"].sum()
    if not final:
        return t("error.data_unavailable", lang)
    by_group = parts.set_index("group")
    return t(
        "execution.narrative.investment", lang, year=year,
        final=_money(final, lang),
        rate=parts["ordonnancer"].sum() / final * 100,
        re_share=by_group.loc["re", "dotation_finale"] / final * 100,
        pip_share=by_group.loc["pip_ri", "dotation_finale"] / final * 100,
    )


def tag_narrative(shares, dim, year, lang="en"):
    final = shares["dotation_finale"].sum()
    ordered = shares["ordonnancer"].sum()
    if not final:
        return t("error.data_unavailable", lang)
    tagged = shares[shares["code"].isin(TAGGED_CODES[dim])]
    return t(
        f"execution.narrative.{dim}", lang, year=year,
        share_finale=tagged["dotation_finale"].sum() / final * 100,
        share_ordonnancer=tagged["ordonnancer"].sum() / ordered * 100 if ordered else 0,
    )


# --- Figures ---------------------------------------------------------------

def _source_note(fig, lang):
    fig.add_annotation(
        text=t("source.boost_wb", lang),
        xref="paper", yref="paper", x=0, y=0,
        xanchor="left", yanchor="top", yshift=-64,
        showarrow=False, font=dict(size=11),
    )
    fig.update_layout(margin=dict(b=100))
    return fig


def _money_column(values, lang):
    return [_money(v, lang) for v in values]


def overview_figure(totals, lang="en"):
    fig = go.Figure()
    for col, key, color in (
        ("dotation_initiale", "execution.measure.dotation_initiale", INITIAL_COLOR),
        ("dotation_finale", "execution.measure.dotation_finale", FINAL_COLOR),
        ("ordonnancer", "execution.measure.ordonnancer", ORDERED_COLOR),
    ):
        name = t(key, lang)
        fig.add_trace(go.Bar(
            name=name, x=totals["year"], y=totals[col], marker_color=color,
            customdata=_money_column(totals[col], lang),
            hovertemplate="<b>" + name + "</b>: %{customdata}<extra></extra>",
        ))
    rate_name = t("execution.measure.rate", lang)
    fig.add_trace(go.Scatter(
        name=rate_name, x=totals["year"], y=totals["rate"] * 100, yaxis="y2",
        mode="lines+markers", marker_color=TOTAL_BUDGET_COLOR,
        hovertemplate="<b>" + rate_name + "</b>: %{y:.1f}%<extra></extra>",
    ))
    format_year_axis(fig)
    peak = totals[["dotation_initiale", "dotation_finale", "ordonnancer"]].max().max()
    unit = scale_currency_axes(fig, ["y"], peak, CURRENCY_CODE, lang)
    fig.update_yaxes(title_text=unit, rangemode="tozero", fixedrange=True)
    fig.update_layout(
        barmode="group",
        title=t("execution.chart.overview", lang),
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis2=dict(title_text=rate_name, overlaying="y", side="right", ticksuffix="%",
                    rangemode="tozero", showgrid=False, fixedrange=True),
    )
    return apply_locale(_source_note(fig, lang), lang)


def stages_figure(stages, lang="en"):
    labels = [t(f"execution.measure.{m}", lang)
              for m in ("dotation_finale", "engagement", "liquidation", "ordonnancer")]
    parts = (
        ("execution.funding.ri", DOMESTIC_FUNDED_COLOR,
         [stages["dotation_finale_ri"], stages["engagement_ri"], stages["liquidation_ri"],
          stages["ordonnancer_ri"]]),
        ("execution.funding.re", FOREIGN_FUNDED_COLOR,
         [stages["dotation_finale_re"], stages["engagement_re"], stages["liquidation_re"],
          stages["ordonnancer_re"]]),
    )
    fig = go.Figure()
    for key, color, values in parts:
        name = t(key, lang)
        fig.add_trace(go.Bar(
            name=name, x=labels, y=values, marker_color=color,
            customdata=_money_column(values, lang),
            hovertemplate="<b>" + name + "</b>: %{customdata}<extra></extra>",
        ))
    peak = max(sum(stage) for stage in zip(*(values for _, _, values in parts)))
    fig.update_yaxes(title_text=scale_currency_axes(fig, ["y"], peak, CURRENCY_CODE, lang), fixedrange=True)
    fig.update_layout(
        barmode="stack",
        title=t("execution.chart.stages", lang),
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return apply_locale(_source_note(fig, lang), lang)


def ministries_figure(ministries, lang="en"):
    # Largest at the top: plotly draws the first category at the bottom.
    rows = ministries.iloc[::-1]
    names = [ministry_label(r, lang) for _, r in rows.iterrows()]
    full_names = [label_or_unspecified(v, lang) for v in rows["admin2"]]
    rates = [format_rate(r, lang) for r in rows["rate"]]
    fig = go.Figure()
    # Within a group plotly also draws the first trace at the bottom, so the
    # final budget goes last to sit above the ordered amount.
    for col, key, color in (
        ("ordonnancer", "execution.measure.ordonnancer", ORDERED_COLOR),
        ("dotation_finale", "execution.measure.dotation_finale", FINAL_COLOR),
    ):
        name = t(key, lang)
        fig.add_trace(go.Bar(
            name=name, y=names, x=rows[col], orientation="h", marker_color=color,
            customdata=np.column_stack([full_names, _money_column(rows[col], lang), rates]),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>" + name + ": %{customdata[1]}<br>"
                + t("execution.measure.rate", lang) + ": %{customdata[2]}<extra></extra>"
            ),
        ))
    peak = rows[["ordonnancer", "dotation_finale"]].max().max()
    fig.update_xaxes(title_text=scale_currency_axes(fig, ["x"], peak, CURRENCY_CODE, lang), fixedrange=True)
    fig.update_yaxes(fixedrange=True, type="category")
    fig.update_layout(
        barmode="group",
        title=t("execution.chart.ministries", lang),
        plot_bgcolor="white",
        height=max(450, 26 * len(rows) + 160),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, traceorder="reversed"),
        bargap=0.25,
    )
    return apply_locale(_source_note(fig, lang), lang)


def ministry_nature_figure(cells, ministries, natures, lang="en"):
    """Execution rate per ministry and nature; amounts in the hover."""
    ministry_codes = list(ministries["admin2_code"])[::-1]
    nature_codes = list(natures["econ1_code"])
    names = {r["admin2_code"]: ministry_label(r, lang) for _, r in ministries.iterrows()}
    nature_names = {r["econ1_code"]: nature_label(r["econ1_code"], r["econ1"], lang)
                    for _, r in natures.iterrows()}
    indexed = cells.set_index(["admin2_code", "econ1_code"])
    z, hover = [], []
    for m in ministry_codes:
        z_row, hover_row = [], []
        for n in nature_codes:
            if (m, n) in indexed.index:
                cell = indexed.loc[(m, n)]
                rate = cell["rate"]
                z_row.append(None if pd.isna(rate) else rate * 100)
                hover_row.append([
                    _money(cell["dotation_finale"], lang), _money(cell["ordonnancer"], lang),
                    format_rate(rate, lang),
                ])
            else:
                z_row.append(None)
                hover_row.append(["–", "–", "–"])
        z.append(z_row)
        hover.append(hover_row)
    fig = go.Figure(go.Heatmap(
        z=z,
        x=[nature_names[n] for n in nature_codes],
        y=[names[m] for m in ministry_codes],
        customdata=hover,
        colorscale=DIVERGING_SCALE, zmin=0, zmid=100, zmax=200,
        colorbar=dict(title=t("execution.measure.rate", lang), ticksuffix="%"),
        hoverongaps=False,
        hovertemplate=(
            "<b>%{y}</b> — %{x}<br>"
            + t("execution.measure.dotation_finale", lang) + ": %{customdata[0]}<br>"
            + t("execution.measure.ordonnancer", lang) + ": %{customdata[1]}<br>"
            + t("execution.measure.rate", lang) + ": %{customdata[2]}<extra></extra>"
        ),
    ))
    fig.update_xaxes(side="top", fixedrange=True)
    fig.update_yaxes(fixedrange=True, type="category")
    fig.update_layout(
        title=t("execution.chart.ministry_nature", lang),
        plot_bgcolor="white",
        height=max(450, 22 * len(ministry_codes) + 200),
        margin=dict(t=140),
    )
    return apply_locale(_source_note(fig, lang), lang)


def investment_figure(parts, lang="en"):
    labels = [t(f"execution.invest.{g}", lang) for g in parts["group"]]
    rates = [format_rate(r, lang) for r in parts["rate"]]
    fig = go.Figure()
    for col, key, color in (
        ("dotation_finale", "execution.measure.dotation_finale", FINAL_COLOR),
        ("ordonnancer", "execution.measure.ordonnancer", ORDERED_COLOR),
    ):
        name = t(key, lang)
        fig.add_trace(go.Bar(
            name=name, x=labels, y=parts[col], marker_color=color,
            customdata=np.column_stack([_money_column(parts[col], lang), rates]),
            hovertemplate=(
                "<b>" + name + "</b>: %{customdata[0]}<br>"
                + t("execution.measure.rate", lang) + ": %{customdata[1]}<extra></extra>"
            ),
        ))
    peak = parts[["dotation_finale", "ordonnancer"]].max().max()
    fig.update_yaxes(title_text=scale_currency_axes(fig, ["y"], peak, CURRENCY_CODE, lang), fixedrange=True)
    fig.update_layout(
        barmode="group",
        title=t("execution.chart.investment", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return apply_locale(_source_note(fig, lang), lang)


def tag_figure(shares, dim, lang="en"):
    """Two 100% bars, final budget and ordered amounts, split by tag code."""
    bars = [t("execution.measure.dotation_finale", lang), t("execution.measure.ordonnancer", lang)]
    fig = go.Figure()
    for i, (_, row) in enumerate(shares.iterrows()):
        name = label_or_unspecified(row["label"], lang)
        amounts = [_money(row["dotation_finale"], lang), _money(row["ordonnancer"], lang)]
        fig.add_trace(go.Bar(
            name=name, y=bars, orientation="h",
            x=[row["share_finale"] * 100, row["share_ordonnancer"] * 100],
            marker_color=TAG_PALETTE[i % len(TAG_PALETTE)],
            customdata=amounts,
            hovertemplate="<b>" + name + "</b>: %{x:.1f}% (%{customdata})<extra></extra>",
        ))
    fig.update_xaxes(ticksuffix="%", range=[0, 100], fixedrange=True)
    fig.update_yaxes(fixedrange=True, autorange="reversed")
    fig.update_layout(
        barmode="stack",
        title=t(f"execution.chart.{dim}", lang),
        plot_bgcolor="white",
        height=max(360, 24 * len(shares) + 220),
        legend=dict(orientation="v", x=1.02, y=1, traceorder="normal"),
    )
    return apply_locale(_source_note(fig, lang), lang)


# --- Tables ----------------------------------------------------------------

# Plain HTML tables: the Bootstrap theme colours .table cells.
_TABLE = {"width": "100%", "borderCollapse": "collapse", "fontSize": "0.875rem"}
_CELL = {"padding": "4px 8px", "borderBottom": "1px solid #dee2e6", "verticalAlign": "top"}
_TEXT_CELL = _CELL
_NUMBER_CELL = {**_CELL, "textAlign": "right", "whiteSpace": "nowrap"}
_HEADER_CELL = {**_CELL, "borderBottom": "2px solid #002244", "position": "sticky", "top": 0,
                "background": "white"}


def amount_table(rows, columns, lang="en", total=None):
    """A table of ``rows``; ``columns`` lists (header, key, kind), kind being
    "text", "amount" or "rate". ``total`` is an optional last row (a dict)."""
    def cell(value, kind, tag=html.Td):
        if kind == "amount":
            return tag(format_amount(value, lang), style=_NUMBER_CELL)
        if kind == "rate":
            return tag(format_rate(value, lang), style=_NUMBER_CELL)
        return tag(value, style=_TEXT_CELL)

    head = html.Thead(html.Tr([
        html.Th(header, style={**_HEADER_CELL, "textAlign": "left" if kind == "text" else "right"})
        for header, _, kind in columns
    ]))
    body = [html.Tr([cell(row[key], kind) for _, key, kind in columns]) for row in rows]
    if total is not None:
        body.append(html.Tr([cell(total.get(key, ""), kind, html.Th) for _, key, kind in columns]))
    return html.Div(
        html.Table([head, html.Tbody(body)], style=_TABLE),
        style={"maxHeight": "520px", "overflowY": "auto"},
    )


def _total_row(frame, label_key, lang):
    final, ordered = frame["dotation_finale"].sum(), frame["ordonnancer"].sum()
    return {
        label_key: t("execution.col.total", lang),
        "dotation_finale": final,
        "ordonnancer": ordered,
        "rate": ordered / final if final else np.nan,
    }


def ministries_table(ministries, lang="en"):
    rows = [{**r, "name": label_or_unspecified(r["admin2"], lang)} for r in ministries.to_dict("records")]
    columns = [
        (t("execution.col.code", lang), "admin2_code", "text"),
        (t("execution.col.ministry", lang), "name", "text"),
        (t("execution.measure.dotation_finale", lang), "dotation_finale", "amount"),
        (t("execution.measure.ordonnancer", lang), "ordonnancer", "amount"),
        (t("execution.measure.rate", lang), "rate", "rate"),
    ]
    return amount_table(rows, columns, lang, total=_total_row(ministries, "name", lang))


def programmes_table(rows_df, lang="en"):
    rows = [
        {**r, "prog_label": label_or_unspecified(r["prog"], lang),
         "nature": nature_label(r["econ1_code"], r["econ1"], lang)}
        for r in rows_df.to_dict("records")
    ]
    columns = [
        (t("execution.col.code", lang), "prog_code", "text"),
        (t("execution.col.programme", lang), "prog_label", "text"),
        (t("execution.col.nature", lang), "nature", "text"),
        (t("execution.measure.dotation_finale", lang), "dotation_finale", "amount"),
        (t("execution.measure.ordonnancer", lang), "ordonnancer", "amount"),
        (t("execution.measure.rate", lang), "rate", "rate"),
    ]
    return amount_table(rows, columns, lang, total=_total_row(rows_df, "prog_label", lang))


def projects_table(projects_df, lang="en"):
    rows = [{**r, "name": label_or_unspecified(r["project"], lang)}
            for r in projects_df.to_dict("records")]
    columns = [
        (t("execution.col.code", lang), "project_code", "text"),
        (t("execution.col.project", lang), "name", "text"),
        (t("execution.measure.dotation_finale", lang), "dotation_finale", "amount"),
        (t("execution.measure.ordonnancer", lang), "ordonnancer", "amount"),
        (t("execution.measure.rate", lang), "rate", "rate"),
    ]
    return amount_table(rows, columns, lang)


def ministry_options(df, year, lang="en"):
    """Dropdown options for the year's ministries, largest final budget first."""
    return [
        {"label": f"{r['admin2_short']} — {label_or_unspecified(r['admin2'], lang)}"
         if r["admin2_short"] else label_or_unspecified(r["admin2"], lang),
         "value": r["admin2_code"]}
        for _, r in by_ministry(df, year).iterrows()
    ]


# --- Blocks: (figure or table, narrative) ------------------------------------

def render_overview(df, year, lang="en"):
    if df is None or year is None:
        return unavailable(lang)
    totals = yearly_totals(df)
    return overview_figure(totals, lang), overview_narrative(totals, year, lang)


def render_stages(df, year, lang="en"):
    if df is None or year is None:
        return unavailable(lang)
    stages = spending_stages(df, year)
    narrative = stages_narrative(stages, year, lang)
    if stages["dotation_finale"]:
        narrative = f"{narrative} {external_note(stages, year, lang)}"
    return stages_figure(stages, lang), narrative


def render_ministries(df, year, lang="en"):
    if df is None or year is None:
        return unavailable(lang)
    ministries = by_ministry(df, year)
    return ministries_figure(ministries, lang), ministries_narrative(ministries, year, lang)


def render_ministries_table(df, year, lang="en"):
    if df is None or year is None:
        return None
    return ministries_table(by_ministry(df, year), lang)


def render_ministry_nature(df, year, lang="en"):
    if df is None or year is None:
        return unavailable(lang)
    natures = by_nature(df, year)
    fig = ministry_nature_figure(ministry_by_nature(df, year), by_ministry(df, year), natures, lang)
    return fig, nature_narrative(natures, year, lang)


def render_programmes(df, year, admin2_code, lang="en"):
    """(table, narrative) of one ministry's programmes."""
    if df is None or year is None or not admin2_code:
        return None, t("error.data_unavailable", lang)
    rows = programmes(df, year, admin2_code)
    if rows.empty:
        return None, t("error.data_unavailable", lang)
    first = rows.iloc[0]
    ministry = first["admin2"] or first["admin2_short"] or admin2_code
    return programmes_table(rows, lang), programmes_narrative(rows, ministry, lang)


def render_investment(df, year, lang="en"):
    if df is None or year is None:
        return unavailable(lang)
    parts = investment_by_funding(df, year)
    return investment_figure(parts, lang), investment_narrative(parts, year, lang)


def render_top_projects(df, year, lang="en"):
    if df is None or year is None:
        return None
    return projects_table(top_projects(df, year), lang)


def render_tag(df, year, dim, lang="en"):
    if df is None or year is None:
        return unavailable(lang)
    shares = tag_shares(df, year, dim)
    if shares.empty:
        return unavailable(lang)
    return tag_figure(shares, dim, lang), tag_narrative(shares, dim, year, lang)
