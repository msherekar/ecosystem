import streamlit as st
import io
import pandas as pd
import matplotlib.pyplot as plt

def download_csv(dataframe: pd.DataFrame, filename: str):
    """
    Offer a Streamlit button to download a DataFrame as a CSV.
    """
    csv = dataframe.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"📥 Download {filename}",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

def download_png(fig: plt.Figure, filename: str = "volcano_plot.png"):
    """
    Offer a Streamlit button to download a matplotlib figure as a PNG.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    st.download_button(
        label=f"📤 Download {filename}",
        data=buf,
        file_name=filename,
        mime="image/png"
    )
