"""« Exécution du budget »: Togo's budget execution by year, ministry,
programme, economic nature, funding and budget tagging, with the DGBF's
standard tables, its execution report tables (SIGFIP) and a ministry's
compte administratif as Excel downloads."""
import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from components import togo_execution as te
from components.country_title import country_title, register_country_title
from components.togo_ca_report import build_ca_report
from components.togo_execution_report import build_report
from components.togo_sigfip_report import build_sigfip_report
from translations import t
from utils import require_login

dash.register_page(__name__, path="/execution")

logger = logging.getLogger(__name__)

GRAPH_CONFIG = {"displayModeBar": False}


@require_login
def layout():
    return html.Div(
        children=[
            dbc.Card(
                dbc.CardBody(
                    [
                        country_title("execution"),
                        html.Div(id="execution-content"),
                    ]
                ),
            ),
            dcc.Store(id="stored-data-execution"),
            dcc.Download(id="execution-download"),
            dcc.Download(id="execution-sigfip-download"),
            dcc.Download(id="execution-ca-download"),
        ]
    )


register_country_title("execution")


def _graph(graph_id):
    return dcc.Graph(id=graph_id, config=GRAPH_CONFIG)


def _section(heading_key, lang, *children):
    return [
        dbc.Row(dbc.Col(html.Hr())),
        dbc.Row(dbc.Col(html.H3(t(heading_key, lang)))),
        *children,
    ]


def _narrative(narrative_id, lang):
    return dbc.Row(dbc.Col(html.P(id=narrative_id, children=t("loading", lang))))


@callback(
    Output("execution-content", "children"),
    Input("stored-language", "data"),
)
def render_execution_content(lang):
    lang = lang or "en"
    controls = dbc.Row(
        [
            dbc.Col(
                [
                    html.Label(t("execution.year", lang), htmlFor="execution-year"),
                    dcc.Dropdown(id="execution-year", clearable=False, searchable=False),
                ],
                xs=12, md=3,
            ),
            dbc.Col(
                dbc.Button(t("execution.download", lang), id="execution-download-button",
                           color="primary", disabled=True),
                xs=12, md="auto", className="align-self-end mt-2 mt-md-0",
            ),
            dbc.Col(
                dbc.Button(t("execution.download_sigfip", lang), id="execution-sigfip-button",
                           color="primary", outline=True, disabled=True),
                xs=12, md="auto", className="align-self-end mt-2 mt-md-0",
            ),
        ],
        className="mb-3",
    )
    tags = []
    for dim in te.TAG_DIMENSIONS:
        tags += _section(
            f"execution.heading.{dim}", lang,
            _narrative(f"execution-{dim}-narrative", lang),
            dbc.Row(dbc.Col(_graph(f"execution-{dim}"))),
        )
    return html.Div(
        [
            controls,
            dbc.Row(dbc.Col(html.H3(t("execution.heading.overview", lang)))),
            _narrative("execution-overview-narrative", lang),
            dbc.Row(dbc.Col(_graph("execution-overview"))),
            *_section(
                "execution.heading.stages", lang,
                _narrative("execution-stages-narrative", lang),
                dbc.Row(dbc.Col(_graph("execution-stages"))),
            ),
            *_section(
                "execution.heading.ministries", lang,
                _narrative("execution-ministries-narrative", lang),
                dbc.Row(dbc.Col(_graph("execution-ministries"))),
                dbc.Row(dbc.Col(html.Div(id="execution-ministries-table"))),
            ),
            *_section(
                "execution.heading.ministry_nature", lang,
                _narrative("execution-ministry-nature-narrative", lang),
                dbc.Row(dbc.Col(_graph("execution-ministry-nature"))),
            ),
            *_section(
                "execution.heading.programmes", lang,
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label(t("execution.ministry", lang), htmlFor="execution-ministry"),
                                dcc.Dropdown(id="execution-ministry", clearable=False),
                            ],
                            xs=12, md=6,
                        ),
                        dbc.Col(
                            dbc.Button(t("execution.download_ca", lang), id="execution-ca-button",
                                       color="primary", outline=True, disabled=True),
                            xs=12, md="auto", className="align-self-end mt-2 mt-md-0",
                        ),
                    ],
                    className="mb-2",
                ),
                _narrative("execution-programmes-narrative", lang),
                dbc.Row(dbc.Col(html.Div(id="execution-programmes-table"))),
            ),
            *_section(
                "execution.heading.investment", lang,
                _narrative("execution-investment-narrative", lang),
                dbc.Row(dbc.Col(_graph("execution-investment"))),
                dbc.Row(
                    dbc.Col(
                        [
                            html.H5(t("execution.heading.top_projects", lang)),
                            html.Div(id="execution-projects-table"),
                        ]
                    )
                ),
            ),
            *tags,
        ]
    )


@callback(
    Output("stored-data-execution", "data"),
    Input("country-select", "value"),
)
def fetch_execution_data(country):
    if not country:
        raise PreventUpdate
    return {"country": country, "ready": te.load_execution(country) is not None}


def _frame(store, country):
    """The country's execution rows, None when the table has none for it;
    PreventUpdate while the store has not caught up with the country."""
    if not store or store.get("country") != country:
        raise PreventUpdate
    if not store.get("ready"):
        return None
    return te.load_execution(country)


def _frame_and_year(store, country, year):
    df = _frame(store, country)
    if df is None:
        return None, None
    if year is None:
        raise PreventUpdate
    return df, year


@callback(
    Output("execution-year", "options"),
    Output("execution-year", "value"),
    Output("execution-download-button", "disabled"),
    Input("stored-data-execution", "data"),
    Input("country-select", "value"),
    State("execution-year", "value"),
)
def update_year_options(store, country, current_year):
    df = _frame(store, country)
    if df is None:
        return [], None, True
    years = te.execution_years(df)
    if not years:
        return [], None, True
    options = [{"label": str(y), "value": y} for y in years]
    return options, current_year if current_year in years else years[0], False


def _block_callback(output_id, render):
    @callback(
        Output(output_id, "figure"),
        Output(f"{output_id}-narrative", "children"),
        Input("stored-data-execution", "data"),
        Input("country-select", "value"),
        Input("execution-year", "value"),
        Input("stored-language", "data"),
    )
    def update_block(store, country, year, lang):
        df, year = _frame_and_year(store, country, year)
        return render(df, year, lang or "en")

    return update_block


update_overview = _block_callback("execution-overview", te.render_overview)
update_stages = _block_callback("execution-stages", te.render_stages)
update_ministries = _block_callback("execution-ministries", te.render_ministries)
update_ministry_nature = _block_callback("execution-ministry-nature", te.render_ministry_nature)
update_investment = _block_callback("execution-investment", te.render_investment)
update_tags = {
    dim: _block_callback(f"execution-{dim}", lambda df, year, lang, dim=dim: te.render_tag(df, year, dim, lang))
    for dim in te.TAG_DIMENSIONS
}


@callback(
    Output("execution-ministries-table", "children"),
    Output("execution-projects-table", "children"),
    Input("stored-data-execution", "data"),
    Input("country-select", "value"),
    Input("execution-year", "value"),
    Input("stored-language", "data"),
)
def update_tables(store, country, year, lang):
    df, year = _frame_and_year(store, country, year)
    lang = lang or "en"
    return te.render_ministries_table(df, year, lang), te.render_top_projects(df, year, lang)


@callback(
    Output("execution-ministry", "options"),
    Output("execution-ministry", "value"),
    Input("stored-data-execution", "data"),
    Input("country-select", "value"),
    Input("execution-year", "value"),
    Input("stored-language", "data"),
    State("execution-ministry", "value"),
)
def update_ministry_options(store, country, year, lang, current):
    df, year = _frame_and_year(store, country, year)
    if df is None:
        return [], None
    options = te.ministry_options(df, year, lang or "en")
    codes = [o["value"] for o in options]
    return options, current if current in codes else (codes[0] if codes else None)


@callback(
    Output("execution-programmes-table", "children"),
    Output("execution-programmes-narrative", "children"),
    Input("stored-data-execution", "data"),
    Input("country-select", "value"),
    Input("execution-year", "value"),
    Input("execution-ministry", "value"),
    Input("stored-language", "data"),
)
def update_programmes(store, country, year, ministry, lang):
    df, year = _frame_and_year(store, country, year)
    return te.render_programmes(df, year, ministry, lang or "en")


@callback(
    Output("execution-download", "data"),
    Input("execution-download-button", "n_clicks"),
    State("execution-year", "value"),
    State("country-select", "value"),
    prevent_initial_call=True,
)
def download_report(n_clicks, year, country):
    df = te.load_execution(country)
    if not n_clicks or df is None or year is None:
        raise PreventUpdate
    return dcc.send_bytes(build_report(df, year), f"execution_budget_{country.lower()}_{year}.xlsx")


@callback(
    Output("execution-sigfip-button", "disabled"),
    Output("execution-ca-button", "disabled"),
    Input("execution-year", "value"),
    Input("execution-ministry", "value"),
)
def update_workbook_buttons(year, ministry):
    return year is None, year is None or not ministry


def _detail(country, year, admin2_code=None):
    """The year's budget lines, or PreventUpdate when there are none or the table
    cannot be read."""
    try:
        detail = te.load_execution_detail(country, year, admin2_code)
    except Exception:
        logger.exception("execution detail for %s %s %s could not be read", country, year, admin2_code)
        raise PreventUpdate
    if detail is None:
        raise PreventUpdate
    return detail


@callback(
    Output("execution-sigfip-download", "data"),
    Input("execution-sigfip-button", "n_clicks"),
    State("execution-year", "value"),
    State("country-select", "value"),
    prevent_initial_call=True,
)
def download_sigfip(n_clicks, year, country):
    df = te.load_execution(country)
    if not n_clicks or df is None or year is None:
        raise PreventUpdate
    content = build_sigfip_report(df, _detail(country, year), year)
    return dcc.send_bytes(content, f"tableaux_sigfip_{country.lower()}_{year}.xlsx")


@callback(
    Output("execution-ca-download", "data"),
    Input("execution-ca-button", "n_clicks"),
    State("execution-year", "value"),
    State("execution-ministry", "value"),
    State("country-select", "value"),
    prevent_initial_call=True,
)
def download_ca(n_clicks, year, ministry, country):
    if not n_clicks or year is None or not ministry:
        raise PreventUpdate
    content = build_ca_report(_detail(country, year, ministry), year, ministry)
    return dcc.send_bytes(content, f"compte_administratif_{ministry}_{year}.xlsx")
