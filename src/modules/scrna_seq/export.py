import streamlit as st
import pandas as pd
from modules.scrna_seq.tracking import status

def export_outputs():
    with st.expander(status("📤 Export Processed Data")):
        anndata = st.session_state.get("anndata")
        if anndata is not None:
            if st.button("💾 Export as .h5ad", key="export_h5ad"):
                path = "anndata_processed.h5ad"
                anndata.write(path)
                st.download_button("⬇️ Download .h5ad", data=open(path, "rb"), file_name="anndata_processed.h5ad")

            if st.button("💾 Export obs as .csv", key="export_obs_csv"):
                obs_csv = anndata.obs.to_csv().encode()
                st.download_button("⬇️ Download Cell Metadata (.csv)", data=obs_csv, file_name="obs_metadata.csv")

            if st.button("💾 Export raw counts as .csv", key="export_counts_csv"):
                count_csv = pd.DataFrame(
                    anndata.X.toarray() if hasattr(anndata.X, "toarray") else anndata.X,
                    index=anndata.obs_names, columns=anndata.var_names
                ).to_csv().encode()
                st.download_button("⬇️ Download Count Matrix (.csv)", data=count_csv, file_name="counts_matrix.csv")
        else:
            st.warning("No processed data found to export.")