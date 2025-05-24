import pandas as pd
import numpy as np
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats
from pydeseq2.default_inference import DefaultInference


def run_pydeseq2(counts_df: pd.DataFrame, metadata_df: pd.DataFrame, condition_column: str = "condition"):
    # Ensure sample names match
    counts_df.columns = counts_df.columns.str.strip()
    metadata_df.index = metadata_df.index.astype(str).str.strip()

    common_samples = list(set(counts_df.columns) & set(metadata_df.index))
    counts_df = counts_df[common_samples].T
    metadata_df = metadata_df.loc[common_samples]

    # Filter low-expressed genes
    counts_df = counts_df.loc[:, counts_df.sum(axis=0) >= 10]

    # Optional: allow user to select subset of conditions
    # You can expand this later to take user input

    # Inference engine
    inference = DefaultInference(n_cpus=4)

    # Prepare DESeqDataSet
    dds = DeseqDataSet(
        counts=counts_df,
        metadata=metadata_df,
        design=f"~{condition_column}",
        refit_cooks=True,
        inference=inference,
    )

    # Run DESeq2
    dds.deseq2()

    # Calculate statistics
    conditions = metadata_df[condition_column].unique().tolist()
    assert len(conditions) == 2, "Only 2-condition comparisons are currently supported."

    stats = DeseqStats(dds, contrast=[condition_column, conditions[1], conditions[0]], inference=inference)
    stats.summary()
    results = stats.results_df

    # Add significance labels
    results["-log10(padj)"] = -results["padj"].apply(lambda x: np.log10(x) if pd.notnull(x) and x > 0 else 0)
    results["significant"] = (results["padj"] < 0.05) & (results["log2FoldChange"].abs() >= 1)

    # Ensure 'gene' column exists
    results["gene"] = results.index

    return results
