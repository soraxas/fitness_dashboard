import os
import csv

import datetime
import dateutil

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .utils import get_df_after_given_date

moving_average_window_size = 3 * 8

MI_FIT_LABELS_NICE_NAME_DICT = {
    "WEIGHT": "Weight",
    "BODY_FAT": "Body Fat",
    "MUSCLE": "Muscle",
    "BMI": "BMI",
    # "BODY_SHAPE_TYPE": "Body Shape Type",
    "BASAL_METABOLISM": "Basal Metabolism",
    "VISCERAL_FAT": "Visceral Fat",
    "BONE_MASS": "Bone Mass",
    "SCORE": "Score",
    "MOISTURE": "Moisture",
    # electrical resistance (for these type of scale to work)
    "IMPEDANCE": "Impedance",
}

MI_FIT_LABELS = list(MI_FIT_LABELS_NICE_NAME_DICT.keys())

import plotly.express as pe

# a dictionary that maps a stats to a color (consistently)
STATS_NAME_TO_COLOR = {
    label: color for (label, color) in zip(MI_FIT_LABELS, pe.colors.qualitative.Dark24)
}


def stats_to_yaxis_title(label):
    if label == "WEIGHT":
        return "Weight (kg)"
    elif label == "BODY_FAT":
        return "Body fat (%)"
    elif label == "MUSCLE":
        return "Muscle (kg)"
    elif label == "BMI":
        return "BMI"
    elif label == "BASAL_METABOLISM":
        return stats_to_title(label)
    elif label == "VISCERAL_FAT":
        return stats_to_title(label)
    elif label == "BONE_MASS":
        return "Bone mass (kg)"
    elif label == "SCORE":
        return stats_to_title(label)
    elif label == "MOISTURE":
        return "Moisture (%)"
    elif label == "IMPEDANCE":
        return stats_to_title(label)
    return stats_to_title(label)


def stats_to_title(label):
    if label == "XXX":
        pass
    return label.replace("_", " ").title()


def get_xaxis_zoomed_range(right_most_date, recent_months_to_zoom):
    # the following is to create whitespace on the right
    # such that the series does not end at the right boarder
    right_margin_duration = datetime.timedelta(days=5)

    # the initial duration to display (3 months)
    initial_display_duration = datetime.timedelta(days=30 * recent_months_to_zoom)

    # calculate the most recent 3 month period
    _to = right_most_date + right_margin_duration
    _from = _to - initial_display_duration

    return dict(xaxis_range=[_from, _to])


def get_layout(title):
    layout = go.Layout(
        title=title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return layout


# def get_plotted_fig(df, stats_label, recent_months=5):
#     """Get a plotted fig for one stat."""
#
#     fig = go.Figure(layout=get_layout(stats_to_title(stats_label)))
#
#     traces = _get_trace_for_stat(df, _get_resampled_df(df), stats_label)
#
#     for t in traces:
#         fig.add_trace(t)
#
#     fig.update_xaxes(title_text="Time")
#     fig.update_yaxes(title_text=stats_to_yaxis_title(stats_label))
#     return fig


def _get_resampled_df(df):
    # resample the dataframe to be equally-spaced
    # (3 hr apart which is reasonable)
    resampled_df = (
        df.resample("3h").ffill(limit=1).interpolate(method="linear", order=2)
    )
    return resampled_df


def _get_trace_for_stat(
    df,
    resampled_df,
    stats_label,
    ma_color="rgba(119,173,59,0.8)",
    actual_color="rgba(119,173,59,1)",
    emw_span=3 * 8 * 1,
):
    traces = [
        # plot the moving average
        go.Scatter(
            x=resampled_df.index,
            y=resampled_df[stats_label].ewm(span=emw_span).mean(),
            # y=resampled_df[stats_label]
            # .rolling(window=moving_average_window_size)
            # .mean(),
            mode="lines",
            line_width=4,
            line_color=ma_color,
            hoverinfo="skip",
            name="Moving Average",
        ),
        # plot the actual scatters
        go.Scatter(
            x=df.index,
            y=df[stats_label],
            mode="markers",
            marker=dict(
                size=6,
                color=actual_color,
                # symbol="circle-open"
                symbol="diamond-open",
            ),
            name="Actual Measurement",
        ),
    ]
    add_annotate_for_last_point = True
    if add_annotate_for_last_point:
        traces.append(
            go.Scatter(
                x=[df.index[-1]],
                y=[df[stats_label].iloc[-1]],
                text=[f"{df[stats_label].iloc[-1]:.1f}"],
                mode="text",
                # marker=dict(color='red', size=10),
                # textfont=dict(color='green', size=20),
                textposition="top right",
                showlegend=False,
            )
        )

    return traces


def get_plotted_fig_all(df, resampled_df, stats_labels, emw_span):
    fig = make_subplots(
        rows=len(stats_labels), cols=1, shared_xaxes=True, vertical_spacing=0.03
    )

    for i, stats_label in enumerate(stats_labels):
        color = STATS_NAME_TO_COLOR[stats_label]
        traces = _get_trace_for_stat(
            df,
            resampled_df,
            stats_label,
            ma_color=color,
            actual_color=color,
            emw_span=emw_span,
        )

        for t in traces:
            fig.add_trace(t, row=i + 1, col=1)

    fig.update_layout(
        get_layout(stats_to_title(stats_label)),
        # height=600, width=600, title_text="Multiple Subplots with Shared Y-Axes"
        showlegend=False,
    )

    # update all y axis
    fig.update_xaxes(title_text="Time", row=len(stats_labels), col=1)
    # Update yaxis properties
    for i, stats_label in enumerate(stats_labels):
        fig.update_yaxes(title_text=stats_to_yaxis_title(stats_label), row=i + 1, col=1)

    # force show ticks for all subplot
    for xaxis_attr in (attr for attr in dir(fig.layout) if attr.startswith("xaxis")):
        getattr(fig.layout, xaxis_attr).showticklabels = True

    add_annotations(fig,
                    [f"x{i}" for i in range(1, len(stats_labels) + 1)],
                    [f"y{i}" for i in range(1, len(stats_labels) + 1)])

    return fig


def get_fig_body_composite_trend(
    df, resampled_df, beginning_date, trend_smoothing_span
):
    # only plot all data after the given date
    df = get_df_after_given_date(df, beginning_date).copy()
    resampled_df = get_df_after_given_date(resampled_df, beginning_date).copy()

    body_fat = resampled_df["BODY_FAT"] * resampled_df["WEIGHT"] / 100
    muscle_mass = resampled_df["MUSCLE"]
    bone_mass = resampled_df["BONE_MASS"]
    body_fat_actual = df["BODY_FAT"] * df["WEIGHT"] / 100
    muscle_mass_actual = df["MUSCLE"]
    bone_mass_actual = df["BONE_MASS"]

    def normalise_offset_with_first_val(series: pd.Series, series_actual: pd.Series):
        # # ===== compute_normalise =====
        # datum = series.dropna()[0]
        # series /= datum
        # series_actual /= datum
        # ===== compute_offset =====
        datum = series.dropna()[0]
        series -= datum
        series_actual -= datum
        return series, series_actual

    body_fat, body_fat_actual = normalise_offset_with_first_val(
        body_fat, body_fat_actual
    )
    muscle_mass, muscle_mass_actual = normalise_offset_with_first_val(
        muscle_mass, muscle_mass_actual
    )
    bone_mass, bone_mass_actual = normalise_offset_with_first_val(
        bone_mass, bone_mass_actual
    )

    fig = go.Figure(layout=get_layout("Body Composite Trend"))

    for name, stat_id, stat, stat_actual in zip(
        ["Body Fat", "Muscle", "Bone Mass"],
        ["BODY_FAT", "MUSCLE", "BONE_MASS"],
        [body_fat, muscle_mass, bone_mass],
        [body_fat_actual, muscle_mass_actual, bone_mass_actual],
    ):
        fig.add_trace(
            go.Scatter(
                x=resampled_df.index,
                y=stat.ewm(span=trend_smoothing_span).mean(),
                mode="lines",
                # fill='tozeroy',
                marker=dict(
                    size=6,
                    color=STATS_NAME_TO_COLOR[stat_id],
                    # symbol="circle-open"
                    # symbol="diamond-open",
                ),
                name=name,
                line_width=4,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=stat_actual.index,
                y=stat_actual,
                mode="markers",
                marker=dict(
                    size=6,
                    color=STATS_NAME_TO_COLOR[stat_id],
                    # symbol="circle-open"
                    symbol="diamond-open",
                ),
                name=name,
                showlegend=False,
            ),
        )

    fig.add_hline(y=0, line_dash="dash", line_width=0.9, opacity=0.9)
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text=f"Cumulative delta since origin (KG)")

    add_annotations(fig, xrefs=["x"], yrefs=["y"], y=0)

    return fig

def add_annotations(fig, xrefs, yrefs, y=None):
    if os.path.exists("data/annotation.csv"):
        for xref, yref in zip(xrefs, yrefs):
            with open("data/annotation.csv", 'r') as f:
                reader = csv.reader(f)
                next(reader)
                for date, text in reader:
                    date = dateutil.parser.parse(date)
                    if date >= fig.data[0].x[0]:
                        add_annotation(fig, date, text, xref=xref, yref=yref, y=y)

def add_annotation(fig, date, text, xref="x", yref="y", y=None):
    fig.add_annotation(
            x=date,
            y=y,
            xref=xref,
            yref=yref,
            text=text,
            showarrow=True,
            font=dict(
                family="Courier New, monospace",
                size=16,
                color="#ffffff"
                ),
            # align="center",
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            # arrowcolor="#636363",
            # ax=20,
            # ay=-30,
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
            bgcolor="#ff7f0e",
            opacity=0.8
            )


if __name__ == "__main__":

    def run():
        df = pd.read_csv("mifit.csv")

        # get_plotted_fig(df, 'BODY_FAT', recent_months=10).show()

        # print(get_plotted_fig(df, "BODY_FAT", recent_months=10).data)

        get_plotted_fig_all(df, _get_resampled_df(df), MI_FIT_LABELS).show()

    run()
