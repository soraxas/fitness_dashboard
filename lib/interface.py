import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
from dash.dependencies import Input, Output, State

from .my_plotter import MI_FIT_LABELS_NICE_NAME_DICT, STATS_NAME_TO_COLOR


def construct_page_content(app):
    # the style arguments for the main content page.

    TEXT_STYLE = {"textAlign": "center", "color": "#191970"}

    CARD_TEXT_STYLE = {
        "textAlign": "center",
        # "color": "#0074D9",
        # 'maxWidth': 600,
        # 'width': 600
    }

    _ui_dropdown = [
        html.P("Dropdown", style={"textAlign": "center"}),
        dcc.Dropdown(
            id="dropdown",
            options=[
                *[
                    {"label": v, "value": k}
                    for (k, v) in MI_FIT_LABELS_NICE_NAME_DICT.items()
                ],
            ],
            # default value
            value=[
                "WEIGHT",
                "BODY_FAT",
                "MUSCLE",
                "BONE_MASS",
                "MOISTURE",
                "IMPEDANCE",
                # "BMI",
                # "BODY_SHAPE_TYPE",
                # "BASAL_METABOLISM",
                # "VISCERAL_FAT",
                # "SCORE",
            ],
            multi=True,
        ),
    ]

    _ui_checkbox = [
        html.P("Check Box", style={"textAlign": "center"}),
        dbc.Card(
            [
                dbc.Checklist(
                    id="check_list",
                    options=[
                        {"label": "Fill under curve", "value": "fill_under"},
                        {"label": "Only plot recent", "value": "only_plot_in_range"},
                    ],
                    value=["fill_under", "only_plot_in_range"],
                    inline=True,
                )
            ]
        ),
    ]

    _ui_figure_display_control = [
        html.P("Stat: Smoothing span"),
        dcc.Slider(
            id="stat_smoothing_span",
            min=1,
            max=100,
            step=1,
            value=10,
            marks={x: str(x) for x in list(range(5, 101, 15))},
        ),
        html.Br(),
        html.P("Figure Height"),
        dcc.Slider(
            id="fig_height",
            min=1000,
            max=3000,
            step=25,
            value=1600,
            marks={x: str(x) for x in list(range(1000, 3001, 500))},
        ),
        html.Br(),
        html.P("Stats: Recent Months"),
        dcc.Slider(
            id="recent_months_to_dis",
            min=1,
            max=24,
            step=1,
            value=1,
            marks={x: str(x) for x in list(range(5, 41, 5))},
        ),
        html.Br(),
        html.P("Trend: Recent days"),
        daq.NumericInput(id="trend_show_past_x_days", min=1, max=90, value=15,),
        html.P("Trend: Smoothing span"),
        dcc.Slider(
            id="trend_smoothing_span",
            min=1,
            max=100,
            step=1,
            value=10,
            marks={x: str(x) for x in list(range(5, 101, 15))},
        ),
    ]

    controls = dbc.FormGroup(
        [
            *_ui_dropdown,
            html.Br(),
            *_ui_checkbox,
            html.Br(),
            dbc.Button(
                id="refresh_button",
                n_clicks=0,
                children="Refresh",
                color="primary",
                block=True,
            ),
            html.Hr(),
            *_ui_figure_display_control,
        ]
    )

    # we use the Row and Col components to construct the sidebar header
    # it consists of a title, and a toggle, the latter is hidden on large screens
    sidebar_header = dbc.Row(
        [
            dbc.Col(html.H2("Fitness", className="display-4")),
            dbc.Col(
                html.Button(
                    # use the Bootstrap navbar-toggler classes to style the toggle
                    html.Span(className="navbar-toggler-icon"),
                    className="navbar-toggler",
                    # the navbar-toggler classes don't set color, so we do it here
                    style={
                        "color": "rgba(0,0,0,.5)",
                        "border-color": "rgba(0,0,0,.1)",
                    },
                    id="toggle",
                ),
                # the column containing the toggle will be only as wide as the
                # toggle, resulting in the toggle being right aligned
                width="auto",
                # vertically align the toggle in the center
                align="center",
            ),
        ]
    )

    sidebar = html.Div(
        [
            sidebar_header,
            # we wrap the horizontal rule and short blurb in a div that can be
            # hidden on a small screen
            # html.Div([html.Hr(), html.P("Fitness", className="lead",),], id="blurb",),
            # use the Collapse component to animate hiding / revealing links
            dbc.Collapse(
                dbc.Nav(
                    [
                        # html.H2("Parameters", style=TEXT_STYLE),
                        html.Hr(),
                        controls,
                        # dbc.NavLink("Home", href="/", active="exact"),
                        # dbc.NavLink("Page 1", href="/page-1", active="exact"),
                        # dbc.NavLink("Page 2", href="/page-2", active="exact"),
                    ],
                    vertical=True,
                    pills=True,
                ),
                id="collapse",
            ),
        ],
        id="sidebar",
    )

    @app.callback(
        Output("collapse", "is_open"),
        [Input("toggle", "n_clicks")],
        [State("collapse", "is_open")],
    )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open

    content_first_row = dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.H4(
                                    # id="card_title_1",
                                    children=[title],
                                    className="card-title",
                                    style={
                                        "color": STATS_NAME_TO_COLOR[card_id.upper()],
                                        **CARD_TEXT_STYLE,
                                    },
                                ),
                                html.P(
                                    id=f"card_{card_id}_text",
                                    children=["Loading..."],
                                    style={
                                        "color": STATS_NAME_TO_COLOR[card_id.upper()],
                                        **CARD_TEXT_STYLE,
                                    },
                                ),
                            ]
                        )
                    ]
                ),
                # md=3,
            )
            for (card_id, title) in {
                "weight": "Weight",
                "muscle": "Muscle",
                "body_fat": "Body Fat",
                "moisture": "Moisture",
            }.items()
        ]
    )

    all_stats = dbc.Row([dbc.Col(dcc.Graph(id=f"graph_all"), md=12,)])
    composite_trend = dbc.Row([dbc.Col(dcc.Graph(id=f"composite_trend"), md=12,)])

    content = html.Div(
        [
            html.H2("Analytics Dashboard Template", style=TEXT_STYLE),
            html.Hr(),
            content_first_row,
            # *content_rows,
            all_stats,
            composite_trend,
        ],
        id="page-content",
    )

    return sidebar, content
