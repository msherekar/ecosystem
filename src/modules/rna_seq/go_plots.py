import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import plotly.express as px

# 1️⃣ Basic Horizontal Bar Plot
# e.g. plot_go_bar() becomes:
def plot_go_bar(go_df: pd.DataFrame):
    go_df["-log10(p)"] = -np.log10(go_df["p_value"])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(go_df["term_name"], go_df["-log10(p)"], color="skyblue")
    ax.set_xlabel("-log10(p-value)")
    ax.set_ylabel("GO Term")
    ax.set_title(f"Top Enriched GO Terms")
    ax.invert_yaxis()
    return fig

# 2️⃣ Bubble Plot
def plot_go_bubble(go_df: pd.DataFrame, top_n: int = 20):
    df = go_df.sort_values("p_value").head(top_n).copy()
    df["-log10(p)"] = -np.log10(df["p_value"])

    fig, ax = plt.subplots(figsize=(10, 6))
    bubble = ax.scatter(
        x=df["-log10(p)"],
        y=df["term_name"],
        s=df["intersection_size"] * 20,
        alpha=0.6,
        color="mediumseagreen",
        edgecolors="black"
    )
    ax.set_xlabel("-log10(p-value)")
    ax.set_ylabel("GO Term")
    ax.set_title("GO Enrichment Bubble Plot (Size = intersection size)")
    return fig

# 3️⃣ Faceted Bar Plot (GO:BP, GO:MF, GO:CC)
def plot_go_faceted(go_df: pd.DataFrame, top_n: int = 10):
    df = go_df.copy()
    df["-log10(p)"] = -np.log10(df["p_value"])
    df = df[df["source"].isin(["GO:BP", "GO:MF", "GO:CC"])]
    df = df.groupby("source").apply(lambda g: g.nsmallest(top_n, "p_value")).reset_index(drop=True)

    g = sns.catplot(
        data=df,
        kind="bar",
        y="term_name",
        x="-log10(p)",
        col="source",
        sharex=False,
        height=5,
        aspect=1.1
    )
    g.set_titles("{col_name}")
    g.set_axis_labels("-log10(p-value)", "GO Term")
    g.set(xlabel="-log10(p)", ylabel="")

    fig = g.fig
    fig.suptitle("Top Enriched GO Terms by Category", y=1.05)
    return fig

# 4️⃣ Interactive Plotly Plot
def plot_go_plotly(go_df: pd.DataFrame, top_n: int = 15):
    df = go_df.sort_values("p_value").head(top_n).copy()
    df["-log10(p)"] = -np.log10(df["p_value"])

    fig = px.bar(
        df,
        x="-log10(p)",
        y="term_name",
        orientation="h",
        color="source",
        hover_data={
            "term_name": True,
            "p_value": True,
            "intersection_size": True,
            "source": True
        },
        title="⚡ Interactive GO Term Bar Plot",
        labels={
            "term_name": "GO Term",
            "-log10(p)": "-log10(p-value)",
            "source": "GO Category"
        },
        height=400 + (top_n * 20)  # Adaptive height
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis_title="-log10 Adjusted p-value",
        margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig

