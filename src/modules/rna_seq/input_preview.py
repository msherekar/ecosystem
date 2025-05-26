import pandas as pd
import streamlit as st
from modules.rna_seq.preprocessing import validate_and_clean_counts  # reuse your preprocessing logic

def show_rnaseq_inputs():
    """
    Show count file preview, metadata preview, validation, and preprocessing.
    Updates st.session_state in-place.
    """
    # Preview uploaded counts file
    if "rnaseq_counts_df" in st.session_state:
        st.subheader("RNA-seq Counts File Preview")
        st.write(f"File: `{st.session_state.rnaseq_counts_filename}`")
        st.dataframe(st.session_state.rnaseq_counts_df.head())
    else:
        st.info("Please upload a counts CSV file in the sidebar to begin RNA-seq analysis.")
        return  # No file to proceed with

    df = st.session_state["rnaseq_counts_df"]

    # Basic validation
    if not pd.api.types.is_integer_dtype(df.iloc[:, 0]):
        st.warning("First column might be gene names. Please confirm.")
        if st.checkbox("✔️ Yes, treat the first column as gene names"):
            df = df.set_index(df.columns[0])
            st.session_state["rnaseq_counts_df"] = df
            st.success("First column set as gene names.")
            st.write(df.head())

    if not df.dtypes.apply(pd.api.types.is_integer_dtype).all():
        st.warning("Some columns may not contain integer (count) values.")

    # Metadata preview
    if "rnaseq_metadata_df" in st.session_state:
        st.subheader("Sample Metadata")
        st.write(f"📄 File: `{st.session_state['rnaseq_metadata_filename']}`")
        st.dataframe(st.session_state["rnaseq_metadata_df"].head())

    # Metadata format help
    with st.expander("ℹ️ Metadata format help"):
        st.markdown("""
        Your metadata CSV should:
        - Have **sample IDs as the first column** (will be used as index)
        - Include a column named **`condition`**
        - Contain **exactly 2 conditions** for DE analysis

        **Example:**
        ```
        sample_id,condition
        Sample_01,Control
        Sample_02,Treated
        ```
        """)

    # Preprocessing
    st.subheader("Preprocessing")
    if st.button("Run Preprocessing", key="preview_preprocessing_button"):
        cleaned_df = validate_and_clean_counts(df)
        st.session_state["rnaseq_counts_cleaned"] = cleaned_df
        st.write("✅ Cleaned Counts (top rows):")
        st.dataframe(cleaned_df.head())
