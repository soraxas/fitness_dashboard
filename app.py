import bisect
import datetime
from typing import Optional

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
import humanize
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output

from lib import update_csv_via_rest
from lib.interface import construct_page_content
from lib.my_plotter import (
    get_plotted_fig_all,
    get_xaxis_zoomed_range,
    _get_resampled_df,
    get_fig_body_composite_trend,
)
from lib.utils import md5

############################################
CSV_FILE_NAME = "data/mifit.csv"

fig_to_plot = {}
composite_trend_fig_to_plot = {}
cur_file_hash = None
cur_df: Optional[pd.DataFrame] = None
cur_resampled_df: Optional[pd.DataFrame] = None
############################################

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        # tag to make mobile more zoomed-in
        {"name": "viewport", "content": "width=device-width, " "initial-scale=1"}
    ],
)
sidebar, content = construct_page_content(app)

app.layout = html.Div([sidebar, content])

_EMW_SPAN_GLOBAL_VARIABLE = 24


def _plot_fig(labels_to_plot):
    print("Plotting...")
    fig = get_plotted_fig_all(
        cur_df, cur_resampled_df, labels_to_plot, emw_span=_EMW_SPAN_GLOBAL_VARIABLE
    )
    # setup margin for the plot
    set_tight_margin(fig)
    return fig


def get_fig(labels_to_plot, force_update=False):
    # first check if file content had changed
    global cur_file_hash, cur_df, cur_resampled_df
    if md5(CSV_FILE_NAME) != cur_file_hash:
        # remove all existing plot.
        fig_to_plot.clear()
        composite_trend_fig_to_plot.clear()
        # reset the file hash
        cur_file_hash = md5(CSV_FILE_NAME)
        cur_df = pd.read_csv(CSV_FILE_NAME)
        cur_df.index = (
            pd.to_datetime(cur_df.TIMESTAMP, unit="ms")
            # .dt.tz_localize("UTC")
            # .dt.tz_convert("Australia/Sydney")
        )

        cur_resampled_df = _get_resampled_df(cur_df)

    # plot if necessary
    _hash = hash(tuple(labels_to_plot))
    if force_update or _hash not in fig_to_plot:
        fig_to_plot[_hash] = _plot_fig(labels_to_plot)

    return fig_to_plot[_hash]


# get_fig(["WEIGHT"])


############################################


# cache fig to plot


@app.callback(
    [
        Output("graph_all", "figure"),
        Output("composite_trend", "figure"),
        Output("card_weight_text", "children"),
        Output("card_body_fat_text", "children"),
        Output("card_muscle_text", "children"),
        Output("card_moisture_text", "children"),
    ],
    [
        Input("refresh_button", "n_clicks"),
        Input("fig_height", "value"),
        Input("recent_months_to_dis", "value"),
        Input("check_list", "value"),
        Input("dropdown", "value"),
        Input("stat_smoothing_span", "value"),
        Input("trend_show_past_x_days", "value"),
        Input("trend_smoothing_span", "value"),
    ],
    [],
)
@profile
def update_figure_cb(
    n_clicks,
    fig_height,
    recent_months_to_dis,
    check_list_value,
    dropdown_value,
    stat_smoothing_span,
    trend_show_past_x_days,
    trend_smoothing_span,
):
    force_update = False
    ctx = dash.callback_context
    triggered = []
    if ctx.triggered:
        triggered = [t["prop_id"].split(".")[0] for t in ctx.triggered]
        if "refresh_button" in triggered:
            force_update = True

        if "stat_smoothing_span" in triggered:
            force_update = True
            global _EMW_SPAN_GLOBAL_VARIABLE
            _EMW_SPAN_GLOBAL_VARIABLE = stat_smoothing_span

    fig = get_fig(dropdown_value, force_update=force_update)

    if not ctx.triggered:
        # initial call when no fig had been created yet
        composite_fig = get_composit_trend_fig(
            trend_show_past_x_days, trend_smoothing_span, force_update=force_update
        )
    elif any(
        token in triggered
        for token in ["trend_show_past_x_days", "trend_smoothing_span"]
    ):
        composite_fig = get_composit_trend_fig(
            trend_show_past_x_days, trend_smoothing_span, force_update=force_update
        )
        return (
            dash.no_update,
            composite_fig,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )
    else:
        composite_fig = dash.no_update

    # if not ctx.triggered:
    #     button_id = 'No clicks yet'
    # else:
    #     button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    ##########################################################

    assert fig.data[1].name == "Actual Measurement", fig.data[1]
    last_measurement_time = fig.data[0].x[-1]

    fig.update_layout(height=int(fig_height))
    fig.update_layout(
        **get_xaxis_zoomed_range(last_measurement_time, recent_months_to_dis)
    )

    title = (
        f"This month"
        if recent_months_to_dis == 1
        else f"Recent {recent_months_to_dis} months"
    )

    # make the data fill to zero
    if "fill_under" in check_list_value:
        for d in fig.data:
            if d.name and d.name.startswith("Moving"):
                d.fill = "tozeroy"

    # make sure the y-zoom level are correct on the part that we are interested in
    currently_in_range = fig.layout.xaxis.range
    _margin = 0.5
    for d in fig.data:
        if d.name and d.name.startswith("Actual"):
            # find the first index that our target is greater than x
            _yaxis_start_idx = bisect.bisect_left(d.x, currently_in_range[0])
            _yaxis_end_idx = bisect.bisect_left(d.x, currently_in_range[1])
            _currently_inrange_yvalues = d.y[_yaxis_start_idx:_yaxis_end_idx]
            # compute the yrange for this subplot
            yrange = (
                np.nanmin(_currently_inrange_yvalues) - _margin,
                np.nanmax(_currently_inrange_yvalues) + _margin,
            )
            # find the corresponding yaxis in the layout object and set the yrange
            fig.layout[f'yaxis{d["yaxis"][1:]}'].range = yrange

    # update title and the latest data point
    last_update_time = humanize.naturaltime(last_measurement_time.replace(tzinfo=None))
    fig.update_layout(title=f"{title} (last update: {last_update_time})")

    ############################################################

    def zoom(layout, xrange):
        print("hiiii")
        for d in fig.data:
            if d.name and d.name.startswith("Actual"):
                # find the first index that our target is greater than x
                _yaxis_start_idx = bisect.bisect_left(d.x, currently_in_range[0])
                _yaxis_end_idx = bisect.bisect_left(d.x, currently_in_range[1])
                _currently_inrange_yvalues = d.y[_yaxis_start_idx:_yaxis_end_idx]
                # compute the yrange for this subplot
                yrange = (
                    np.nanmin(_currently_inrange_yvalues) - _margin,
                    np.nanmax(_currently_inrange_yvalues) + _margin,
                )
                # find the corresponding yaxis in the layout object and set the yrange
                fig.layout[f'yaxis{d["yaxis"][1:]}'].range = yrange

    return (
        fig,
        composite_fig,
        f"{cur_df['WEIGHT'][-1]:.1f} KG",
        f"{cur_df['BODY_FAT'][-1]:.1f} %",
        f"{cur_df['MUSCLE'][-1]:.1f} KG",
        f"{cur_df['MOISTURE'][-1]:.1f} %",
    )


def get_composit_trend_fig(last_x_days, trend_smoothing_span, force_update=False):
    # plot if necessary
    # NOTE that we do not need to handle file-changing here as it's handled by the
    # main stat plotting.
    _hash = hash((last_x_days, trend_smoothing_span))
    if force_update or _hash not in composite_trend_fig_to_plot:
        composite_trend_fig_to_plot[_hash] = _plot_composit_trend_fig(
            last_x_days, trend_smoothing_span, force_update
        )
    return composite_trend_fig_to_plot[_hash]


def _plot_composit_trend_fig(last_x_days, trend_smoothing_span, force_update=False):
    beginning_date = datetime.datetime.now() - datetime.timedelta(days=last_x_days)
    composite_fig = get_fig_body_composite_trend(
        cur_df.copy(),
        cur_resampled_df.copy(),
        beginning_date=beginning_date,
        trend_smoothing_span=trend_smoothing_span,
    )
    set_tight_margin(composite_fig)
    composite_fig.update_layout(
        title=f"Body Composite Trend ({humanize.naturaltime(beginning_date.replace(tzinfo=None))})"
    )
    return composite_fig


def set_tight_margin(fig):
    fig.update_layout(margin=dict(l=0, r=0, t=80, b=80), dragmode="pan")


############################################
# test GET
from flask import jsonify

# # app = Flask(__name__)

tasks = [
    {
        "id": 1,
        "title": "Buy groceries",
        "description": "Milk, Cheese, Pizza, Fruit, Tylenol",
        "done": False,
    },
    {
        "id": 2,
        "title": "Learn Python",
        "description": "Need to find a good Python tutorial on the web",
        "done": False,
    },
]


@app.server.route("/todo/api/v1.0/tasks", methods=["GET"])
def get_tasks():
    return jsonify({"tasks": tasks})


############################################

# build route to upload csv content
update_csv_via_rest.build_route(app, CSV_FILE_NAME)

if __name__ == "__main__":
    app.run_server(
        host="0.0.0.0",
        port="8085",
        # debug=True
    )
