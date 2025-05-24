import streamlit as st
import pandas as pd
from modules.scrna_seq.tracking import status

def export_outputs():
    with st.expander(status("📤 Export Processed Data")):
        adata = st.session_state.get("adata")
        if adata is not None:
            if st.button("💾 Export as .h5ad"):
                path = "adata_processed.h5ad"
                adata.write(path)
                st.download_button("⬇️ Download .h5ad", data=open(path, "rb"), file_name="adata_processed.h5ad")

            if st.button("💾 Export obs as .csv"):
                obs_csv = adata.obs.to_csv().encode()
                st.download_button("⬇️ Download Cell Metadata (.csv)", data=obs_csv, file_name="obs_metadata.csv")

            if st.button("💾 Export raw counts as .csv"):
                count_csv = pd.DataFrame(
                    adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X,
                    index=adata.obs_names, columns=adata.var_names
                ).to_csv().encode()
                st.download_button("⬇️ Download Count Matrix (.csv)", data=count_csv, file_name="counts_matrix.csv")
        else:
            st.warning("No processed data found to export.")