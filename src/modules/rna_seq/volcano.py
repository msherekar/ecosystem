import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def volcano_plot(results_df: pd.DataFrame, padj_thresh: float, lfc_thresh: float, lfc_se_thresh: float, top_n_genes: int):
    """
    Generate a volcano plot and return the figure and filtered gene DataFrame.

    Parameters:
    - results_df: DESeq2 results dataframe (must contain 'gene', 'padj', 'log2FoldChange', 'lfcSE')
    - padj_thresh: threshold for adjusted p-value
    - lfc_thresh: threshold for absolute log2 fold change
    - lfc_se_thresh: threshold for max standard error
    - top_n_genes: number of top genes to label on the plot

    Returns:
    - fig: matplotlib figure
    - filtered: filtered DataFrame based on significance criteria
    """
    # Apply filters
    filtered = results_df[
        (results_df["padj"] < padj_thresh) &
        (results_df["log2FoldChange"].abs() >= lfc_thresh) &
        (results_df["lfcSE"] <= lfc_se_thresh)
    ].copy()

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(
        results_df["log2FoldChange"],
        results_df["-log10(padj)"],
        s=10, alpha=0.3, color="lightgray", label="All genes"
    )
    ax.scatter(
        filtered["log2FoldChange"],
        filtered["-log10(padj)"],
        s=10, alpha=0.7, color="red", label="Significant"
    )

    if top_n_genes > 0 and len(filtered) > 0:
        to_label = filtered.sort_values("padj").head(top_n_genes)
        for _, row in to_label.iterrows():
            ax.text(row["log2FoldChange"], row["-log10(padj)"], row["gene"], fontsize=8, alpha=0.7)

    ax.axhline(y=-np.log10(padj_thresh), linestyle="--", color="black", linewidth=1)
    ax.axvline(x=lfc_thresh, linestyle="--", color="black", linewidth=1)
    ax.axvline(x=-lfc_thresh, linestyle="--", color="black", linewidth=1)

    ax.set_xlabel("log2 Fold Change")
    ax.set_ylabel("-log10 Adjusted p-value")
    ax.set_title("Volcano Plot")
    ax.legend()

    return fig, filtered
