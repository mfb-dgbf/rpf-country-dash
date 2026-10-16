"""« Agriculture »: public spending on agriculture (BOOST sub-function
"Agriculture") next to crop area, yield and production (FAOSTAT), by year.
The page describes both series; it draws no link between them."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import server_store
from components.togo_execution import format_amount
from constants import AGRICULTURE_VIEW_COUNTRIES
from translations import t
from utils import (
    apply_locale,
    currency_axis_title,
    empty_plot,
    filter_country_sort_year,
    format_year_axis,
    millify,
    scale_currency_axes,
)

DEFAULT_CROP = "Maize (corn)"
CURRENCY = "XOF"
SPENDING_COLOR, BUDGET_COLOR, REAL_COLOR = "#2E8B57", "#C9D3DD", "#1B2A41"
PRODUCTION_COLOR, YIELD_COLOR, CROP_BUDGET_COLOR = "#F2B705", "#006A4E", "#1F5F99"


# --- Data ------------------------------------------------------------------

def _load(key, country):
    """The store table ``key`` for ``country`` within START_YEAR..END_YEAR,
    oldest year first, or None when the country has no rows."""
    if country not in AGRICULTURE_VIEW_COUNTRIES:
        return None
    df = server_store.lookup(key)
    if df is None or df.empty:
        return None
    df = filter_country_sort_year(df, country).sort_values("year")
    return None if df.empty else df


def load_spending(country):
    return _load("agriculture_spending", country)


def load_crops(country):
    return _load("fao_crop_production", country)


def crop_options(df):
    """Crops with a production figure in the latest year, largest first."""
    latest = df[df["year"] == df["year"].max()].dropna(subset=["production_t"])
    return list(latest.sort_values("production_t", ascending=False)["item"])


def crop_label(df, crop, lang):
    """The crop's name in ``lang`` where the catalogs have one, else FAO's name."""
    code = int(df.loc[df["item"] == crop, "item_code"].iloc[0])
    key = f"agriculture.crop.{code}"
    label = t(key, lang)
    return crop if label == key else label


def unavailable(lang):
    message = t("error.data_unavailable", lang)
    return empty_plot(message), message


# --- Figures ---------------------------------------------------------------

def _amount_hover(values, lang):
    return [millify(v, lang, decimals=1) for v in values]


def spending_figure(df, lang):
    fig = go.Figure()
    for column, name_key, color in (("budget", "agriculture.trace.budget", BUDGET_COLOR),
                                    ("expenditure", "agriculture.trace.executed", SPENDING_COLOR)):
        fig.add_trace(go.Bar(
            name=t(name_key, lang), x=df["year"], y=df[column], marker_color=color,
            customdata=_amount_hover(df[column], lang),
            hovertemplate="%{customdata}<extra>" + t(name_key, lang) + "</extra>",
        ))
    fig.add_trace(go.Scatter(
        name=t("trace.inflation_adjusted", lang), x=df["year"], y=df["real_expenditure"],
        mode="lines+markers", line=dict(color=REAL_COLOR),
        customdata=_amount_hover(df["real_expenditure"], lang),
        hovertemplate="%{customdata}<extra>" + t("trace.inflation_adjusted", lang) + "</extra>",
    ))
    fig.update_layout(
        barmode="group", hovermode="x unified", plot_bgcolor="white",
        title=t("agriculture.chart.spending", lang),
        legend=dict(orientation="h", yanchor="bottom", y=1), margin=dict(t=120),
    )
    format_year_axis(fig)
    peak = df[["budget", "expenditure", "real_expenditure"]].max().max()
    fig.update_yaxes(title_text=scale_currency_axes(fig, ["y"], peak, CURRENCY, lang), fixedrange=True)
    return apply_locale(fig, lang)


def _add_budget_axis(fig, spending, lang):
    """Approved budget and executed spending on agriculture, on a third axis
    to the right of the yield axis."""
    for column, name_key, dash in (("budget", "agriculture.trace.budget", "dash"),
                                   ("expenditure", "agriculture.trace.executed", "solid")):
        fig.add_trace(go.Scatter(
            name=t(name_key, lang), x=spending["year"], y=spending[column], yaxis="y3",
            mode="lines+markers", line=dict(color=CROP_BUDGET_COLOR, dash=dash),
            customdata=_amount_hover(spending[column], lang),
            hovertemplate="%{customdata}<extra>" + t(name_key, lang) + "</extra>",
        ))
    fig.update_layout(
        xaxis=dict(domain=[0, 0.84]),
        yaxis3=dict(overlaying="y", side="right", anchor="free", position=0.97,
                    rangemode="tozero", showgrid=False, fixedrange=True),
    )
    unit = scale_currency_axes(fig, ["y3"], spending[["budget", "expenditure"]].max().max(), CURRENCY, lang)
    fig.update_layout(yaxis3_title_text=currency_axis_title(t("agriculture.axis.budget", lang), unit))


def crop_figure(df, crop, lang, spending=None):
    rows = df[df["item"] == crop]
    if rows.empty:
        return empty_plot(t("error.no_data_period", lang))
    label = crop_label(df, crop, lang)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        name=t("agriculture.trace.production", lang), x=rows["year"], y=rows["production_t"],
        marker_color=PRODUCTION_COLOR,
        customdata=[format_amount(v, lang) if pd.notna(v) else "–" for v in rows["production_t"]],
        hovertemplate="%{customdata} t<extra>" + t("agriculture.trace.production", lang) + "</extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        name=t("agriculture.trace.yield", lang), x=rows["year"], y=rows["yield_kg_ha"],
        mode="lines+markers", line=dict(color=YIELD_COLOR),
        hovertemplate="%{y:,.0f} kg/ha<extra>" + t("agriculture.trace.yield", lang) + "</extra>",
    ), secondary_y=True)
    format_year_axis(fig)
    fig.update_yaxes(title_text=t("agriculture.axis.production", lang), secondary_y=False, fixedrange=True)
    fig.update_yaxes(title_text=t("agriculture.axis.yield", lang), secondary_y=True, fixedrange=True,
                     rangemode="tozero", showgrid=False)
    fig.update_layout(
        hovermode="x unified", plot_bgcolor="white",
        title=t("agriculture.chart.crop_budget" if spending is not None else "agriculture.chart.crop",
                lang, crop=label),
        legend=dict(orientation="h", yanchor="bottom", y=1), margin=dict(t=120),
    )
    if spending is not None:
        _add_budget_axis(fig, spending, lang)
    return apply_locale(fig, lang)


# --- Narratives ------------------------------------------------------------

def spending_narrative(df, lang):
    first, last = df.iloc[0], df.iloc[-1]
    peak = df.loc[df["expenditure"].idxmax()]
    rate = df["expenditure"].sum() / df["budget"].sum() * 100
    return t(
        "agriculture.narrative.spending", lang,
        first=millify(first["expenditure"], lang, decimals=1), start=int(first["year"]),
        last=millify(last["expenditure"], lang, decimals=1), end=int(last["year"]),
        peak=millify(peak["expenditure"], lang, decimals=1), peak_year=int(peak["year"]),
        rate=rate,
    )


def _spending_and_production(rows, spending, lang):
    """Executed spending and the crop's production over the years both have."""
    both = rows.merge(spending, on="year").dropna(subset=["production_t", "expenditure"])
    if len(both) < 2:
        return ""
    first, last = both.iloc[0], both.iloc[-1]
    return t(
        "agriculture.narrative.crop_spending", lang,
        start=int(first["year"]), end=int(last["year"]),
        s_first=millify(first["expenditure"], lang, decimals=1),
        s_last=millify(last["expenditure"], lang, decimals=1),
        s_change=(last["expenditure"] / first["expenditure"] - 1) * 100,
        p_first=format_amount(first["production_t"], lang), p_last=format_amount(last["production_t"], lang),
        p_change=(last["production_t"] / first["production_t"] - 1) * 100,
    )


def crop_narrative(df, crop, lang, spending=None):
    rows = df[(df["item"] == crop)].dropna(subset=["production_t"])
    if len(rows) < 2:
        return t("error.data_unavailable", lang)
    first, last = rows.iloc[0], rows.iloc[-1]
    text = t(
        "agriculture.narrative.crop", lang,
        crop=crop_label(df, crop, lang), start=int(first["year"]), end=int(last["year"]),
        p_first=format_amount(first["production_t"], lang), p_last=format_amount(last["production_t"], lang),
        change=(last["production_t"] / first["production_t"] - 1) * 100,
        y_first=format_amount(first["yield_kg_ha"], lang), y_last=format_amount(last["yield_kg_ha"], lang),
    )
    flag_key = f"agriculture.flag.{last['production_flag']}"
    if t(flag_key, lang) != flag_key:
        text += t("agriculture.narrative.flag", lang, end=int(last["year"]), flag=t(flag_key, lang))
    if spending is not None:
        text += _spending_and_production(rows[["year", "production_t"]],
                                         spending[["year", "expenditure"]], lang)
    return text


def render_spending(df, lang):
    if df is None:
        return unavailable(lang)
    return spending_figure(df, lang), spending_narrative(df, lang)


def render_crop(df, crop, lang, spending=None):
    if df is None or crop is None:
        return unavailable(lang)
    if spending is not None:
        spending_years = spending.loc[spending["expenditure"].notna(), "year"]
        if not spending_years.empty:
            df = df[df["year"] >= spending_years.min()]
    return crop_figure(df, crop, lang, spending), crop_narrative(df, crop, lang, spending)
