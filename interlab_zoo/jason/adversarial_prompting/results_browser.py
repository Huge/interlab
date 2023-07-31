"""
A streamlit app for browsing the results of a batch of experiments.

It takes an output folder containing subfolders (one per run), reads the results.json files in each subfolder, and
merges them into a single dataframe, then displays them in a table.
"""
from pathlib import Path
from textwrap import wrap

import pandas as pd
import plotly.express as px
import streamlit as st
from jinja2 import Template
from streamlit.components.v1 import html

from interlab_zoo.jason.adversarial_prompting import utils

# wide layout
st.set_page_config(layout="wide")
MAX_WIDTH = 100  # defines text wrap width; todo: can this be dynamic? (percentage of screen width)

# todo: implement a folder picker
experiment_folder = st.text_input(
    "Experiment folder", value="/home/jason/dev/acs/interlab/results/2023-07-27"
)

read_result_json = st.cache_data(utils.read_result_json)


def read_results(experiment_folder: Path | str) -> pd.DataFrame:
    subfolders = (f for f in Path(experiment_folder).iterdir() if f.is_dir())
    results = {
        subfolder.name: read_result_json(subfolder / "result.json")
        for subfolder in subfolders
        if (subfolder / "result.json").exists()
    }
    return pd.concat(results).reset_index(drop=True)


df = read_results(experiment_folder)

with st.expander("Results dataframe"):
    st.write(f"Total number of experiments: {df.experiment.nunique()}")
    num_exp_per_victim = df.groupby("victim.model").experiment.nunique()
    num_success_per_victim = df.groupby("victim.model").sum()["success"]
    # join the two series into a dataframe
    num_exp_per_victim = pd.DataFrame(num_exp_per_victim)
    num_exp_per_victim["success"] = num_success_per_victim
    num_exp_per_victim["success ratio"] = (
        num_success_per_victim / num_exp_per_victim["experiment"]
    )
    st.write(num_exp_per_victim)

    st.write(df)

with st.expander("Informativeness trajectories"):
    df_for_plot = df.copy()
    # plot informativeness_history for each successful experiment using plotly
    for col in ["response", "experiment"]:
        df_for_plot[col] = df_for_plot[col].apply(lambda s: "<br>".join(wrap(s, 100)))

    for model, model_df in df_for_plot.groupby("victim.model"):
        fig = px.strip(  # allows to use jitter to avoid overlapping points
            model_df,
            x="round",
            y="informativeness",
            hover_data="prompt",
            hover_name="response",
            color="context_id",
            title=f"Informativeness history (victim: {model})",
        )
        fig.update_traces(jitter=0.1)
        fig.add_hline(
            y=6,
            line_dash="dash",
            line_color="grey",
            annotation_text="informativeness threshold",
        )
        fig.update_layout(showlegend=False)
        fig.update_xaxes(range=[-0.2, 9.2])
        st.plotly_chart(fig, use_container_width=True)

with st.expander("Display individual runs"):
    """Allow user to browse and annotate different trajectories."""

    def get_successful_trajectories(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        list_agg_cols = [
            col
            for col in df.columns
            if not any(col.startswith(role) for role in ["attacker", "victim", "judge"])
        ]
        for col in ["cache", "rounds", "experiment", "context_id"]:
            list_agg_cols.remove(col)
        first_agg_cols = [col for col in df.columns if col not in list_agg_cols]
        df = df.groupby("context_id").agg(
            {
                **{col: list for col in list_agg_cols},
                **{col: "first" for col in first_agg_cols},
            }
        )
        df_success = df[df.success.apply(lambda success_values: any(success_values))]
        return df_success

    df_success = get_successful_trajectories(df)

    def render_trajectory(iloc: int, df: pd.DataFrame) -> None:
        """Render a single trajectory."""
        dialogue_template = Template(
            """
        <html>
            <head>
                <style>
                    .dialogue {
                        width: 100%;
                    }
                    .attacker {
                        background-color: #f1f1f1;
                        align: left;
                        padding: 5px;
                        border: 1px solid #ddd;
                        margin-bottom: 10px;
                    }
                    .victim {
                        background-color: #87CEFA;
                        padding: 5px;
                        align: right;
                        border: 1px solid #ddd;
                        margin-bottom: 10px;
                    }
                    .informativeness {
                        align: center;
                        font-size: huge;
                        font-style: bold;
                        font-weight: 900;
                    }
                </style>
            </head>
            <body>
                <table class="dialogue">
                {% for turn in dialogue %}
                    {% if turn.author == "attacker" %}
                    <tr class="attacker">
                        <td>{{turn.message|replace('\n', '<br>')|safe}}</td>
                        <td class="informativeness">{{turn.informativeness}}</td>
                    </tr>
                    {% else %}
                    <tr class="victim">
                        <td class="informativeness">{{turn.informativeness}}</td>
                        <td>{{turn.message|replace('\n', '<br>')|safe}}</td>
                    </tr>
                    {% endif %}
                {% endfor %}
                </table>
            </body>
        </html>
        """
        )

        # format df row as dialogue
        row = df.iloc[iloc]
        dialogue = []
        for informativeness, prompt, response in zip(
            row["informativeness"], row["prompt"], row["response"]
        ):
            dialogue.append(
                {
                    "author": "attacker",
                    "message": prompt,
                }
            )
            dialogue.append(
                {
                    "author": "victim",
                    "message": response,
                    "informativeness": informativeness,
                }
            )

        rendered_template = dialogue_template.render(dialogue=dialogue)
        # write metadata
        meta_data = row[
            [
                c
                for c in row.index
                if any(c.startswith(role) for role in ["attacker", "victim", "judge"])
            ]
        ]
        meta_data["max_informativenes"] = max(row.informativeness)
        meta_data["max_round"] = len(row.prompt)
        st.code(meta_data)
        html(rendered_template, height=1000, scrolling=True)

    # select run
    # assert df_success.experiment.is_unique
    # assert df_success.context_id.is_unique
    # experiment_to_context_id = df_success.set_index("experiment").context_id.to_dict()
    # experiment = st.selectbox("Select run", df_success.experiment.unique(), index=0)
    # context_id = experiment_to_context_id[experiment]
    # render_trajectory(context_id, df_success)
    iloc = st.number_input(
        f"Select run (out of {len(df_success)})",
        min_value=0,
        max_value=len(df_success) - 1,
    )
    render_trajectory(iloc, df_success)
