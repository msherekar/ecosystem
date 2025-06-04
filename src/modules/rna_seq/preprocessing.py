import pandas as pd
import streamlit as st

def validate_and_clean_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and optionally clean RNA-seq counts DataFrame.
    Assumes genes are in the first column if that column is not numeric.
    """
    # Check if gene names are in the first column
    if not pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
        df = df.set_index(df.columns[0])
    
    # Drop rows with NA
    df_clean = df.dropna()
    
    # Keep genes with counts > 10 in at least one sample
    df_filtered = df_clean[df_clean.sum(axis=1) > 10]
    
    st.info(f"Preprocessed: {df.shape[0]} → {df_filtered.shape[0]} genes after filtering.")
    
    return df_filtered
