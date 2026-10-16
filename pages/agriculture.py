"""« Agriculture »: public spending on agriculture next to crop production and
yield, for the countries in AGRICULTURE_VIEW_COUNTRIES."""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from components import agriculture as ag
from components.country_title import country_title, register_country_title
from components.source_metadata_popover import chart_container
from translations import t
from utils import require_login

dash.register_page(__name__, path="/agriculture")


@require_login
def layout():
    return html.Div(
        children=[
            dbc.Card(dbc.CardBody([country_title("agriculture"), html.Div(id="agriculture-content")])),
            dcc.Store(id="stored-data-agriculture"),
        ]
    )


register_country_title("agriculture")


@callback(
    Output("agriculture-content", "children"),
    Input("stored-language", "data"),
)
def render_agriculture_content(lang):
    lang = lang or "en"
    return html.Div(
        [
            dbc.Row(dbc.Col(html.P(t("agriculture.intro", lang)))),
            dbc.Row(dbc.Col(html.H3(t("agriculture.heading.spending", lang)))),
            dbc.Row(dbc.Col(html.P(id="agriculture-spending-narrative", children=t("loading", lang)))),
            dbc.Row(dbc.Col(chart_container("agriculture-spending"))),
            dbc.Row(dbc.Col(html.Hr())),
            dbc.Row(dbc.Col(html.H3(t("agriculture.heading.crops", lang)))),
            dbc.Row(
                dbc.Col(
                    [
                        html.Label(t("agriculture.crop", lang), htmlFor="agriculture-crop"),
                        dcc.Dropdown(id="agriculture-crop", clearable=False),
                    ],
                    xs=12, md=4,
                ),
                className="mb-2",
            ),
            dbc.Row(dbc.Col(html.P(id="agriculture-crops-narrative", children=t("loading", lang)))),
            dbc.Row(dbc.Col(chart_container("agriculture-crops"))),
        ]
    )


@callback(
    Output("stored-data-agriculture", "data"),
    Input("country-select", "value"),
)
def fetch_agriculture_data(country):
    if not country:
        raise PreventUpdate
    return {
        "country": country,
        "spending": ag.load_spending(country) is not None,
        "crops": ag.load_crops(country) is not None,
    }


def _ready(store, country, part):
    """Whether the store has ``part`` for ``country``; PreventUpdate while the
    store has not caught up with the country."""
    if not store or store.get("country") != country:
        raise PreventUpdate
    return bool(store.get(part))


@callback(
    Output("agriculture-spending", "figure"),
    Output("agriculture-spending-narrative", "children"),
    Input("stored-data-agriculture", "data"),
    Input("country-select", "value"),
    Input("stored-language", "data"),
)
def update_spending(store, country, lang):
    lang = lang or "en"
    df = ag.load_spending(country) if _ready(store, country, "spending") else None
    return ag.render_spending(df, lang)


@callback(
    Output("agriculture-crop", "options"),
    Output("agriculture-crop", "value"),
    Input("stored-data-agriculture", "data"),
    Input("country-select", "value"),
    Input("stored-language", "data"),
    State("agriculture-crop", "value"),
)
def update_crop_options(store, country, lang, current):
    lang = lang or "en"
    df = ag.load_crops(country) if _ready(store, country, "crops") else None
    if df is None:
        return [], None
    crops = ag.crop_options(df)
    if not crops:
        return [], None
    options = [{"label": ag.crop_label(df, crop, lang), "value": crop} for crop in crops]
    if current in crops:
        return options, current
    return options, ag.DEFAULT_CROP if ag.DEFAULT_CROP in crops else crops[0]


@callback(
    Output("agriculture-crops", "figure"),
    Output("agriculture-crops-narrative", "children"),
    Input("stored-data-agriculture", "data"),
    Input("country-select", "value"),
    Input("agriculture-crop", "value"),
    Input("stored-language", "data"),
)
def update_crops(store, country, crop, lang):
    lang = lang or "en"
    df = ag.load_crops(country) if _ready(store, country, "crops") else None
    spending = ag.load_spending(country) if store.get("spending") else None
    return ag.render_crop(df, crop, lang, spending)
