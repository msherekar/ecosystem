import streamlit as st
from modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from modules.search.geo import geo_search, geo_display
from modules.reader.pubmed import reader
from chat.chatbot import ask_chatbot
from interface.welcome import show_welcome_message
from modules.rna_seq.preprocessing import validate_and_clean_counts
from modules.rna_seq.pydeseq import run_pydeseq2
from modules.rna_seq.go import run_go_enrichment
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

def render_center_panel(data_col):
    with data_col:
        if not any([
            st.session_state.tabular_analysis,
            st.session_state.image_analysis,
            st.session_state.scRNAseq_analysis,
            st.session_state.rnaseq_analysis,
            st.session_state.reader,
            st.session_state.search
        ]):
            show_welcome_message(data_col)  # ✅ Use the new modular function
            return  # Optional: stop further rendering if no module is selected

def render_center_panel(data_col):
    with data_col:
        if not any([
            st.session_state.tabular_analysis,
            st.session_state.image_analysis,
            st.session_state.scRNAseq_analysis,
            st.session_state.rnaseq_analysis,
            st.session_state.reader,
            st.session_state.search
        ]):
            from chat.chatbot import ask_chatbot
            if st.session_state.welcome_message == "":
                message = ask_chatbot(
                    [{"role": "user", "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."}],
                    model_choice='gpt4'
                )
                st.session_state.welcome_message = message.content
            st.markdown(st.session_state.welcome_message)

        if st.session_state.reader:
            reader(st.session_state.user_interest)

        if st.session_state.pubmed_search:
            if st.session_state.pubmed_search_query.strip():
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False
            st.session_state.pubmed_search_query = ''

        if st.session_state.search:
            if st.session_state.geo_search_query.strip():
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.geo_search = False
            st.session_state.geo_search_query = ''
        
        # RNA-seq analysis
        if st.session_state.rnaseq_analysis:
            
            # Preview uploaded counts file
            if "rnaseq_counts_df" in st.session_state:
                st.subheader("RNA-seq Counts File Preview")
                st.write(f"File: `{st.session_state.rnaseq_counts_filename}`")
                st.dataframe(st.session_state.rnaseq_counts_df.head())
            else:
                st.info("Please upload a counts CSV file in the sidebar to begin RNA-seq analysis.")

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

            # Preprocessing step
            st.subheader("Preprocessing")
            if st.button("Run Preprocessing"):
                cleaned_df = validate_and_clean_counts(df)
                st.session_state["rnaseq_counts_cleaned"] = cleaned_df
                st.write("✅ Cleaned Counts (top rows):")
                st.dataframe(cleaned_df.head())

            # Differential expression
            st.subheader("Differential Expression (PyDESeq2)")

            if "rnaseq_metadata_df" not in st.session_state:
                st.warning("⚠️ Please upload a metadata CSV file with sample conditions (e.g., columns: sample, condition).")
            elif "rnaseq_counts_cleaned" not in st.session_state:
                st.warning("⚠️ Please run preprocessing before running DE analysis.")
            else:
                if st.button("Run PyDESeq2"):
                    try:
                        results_df = run_pydeseq2(
                            st.session_state["rnaseq_counts_cleaned"],
                            st.session_state["rnaseq_metadata_df"]
                        )
                        st.session_state["deseq_results"] = results_df
                        st.success("✅ Differential expression analysis complete.")
                    except Exception as e:
                        st.error(f"Error during DE analysis: {e}")

            # ✅ Everything below runs independently if results exist
            if "deseq_results" in st.session_state:
                
                st.subheader("Volcano Plot and Filtering")

                results_df = st.session_state["deseq_results"]

                # Step 1: User-defined filters
                padj_thresh = st.slider("Adjusted p-value threshold", 0.0, 1.0, 0.05, 0.01)
                lfc_thresh = st.slider("Absolute log2 Fold Change threshold", 0.0, 5.0, 1.0, 0.1)
                lfc_se_thresh = st.slider("Maximum Standard Error (lfcSE)", 0.0, 10.0, 1.0, 0.1)
                top_n_genes = st.slider("Top genes to label on plot", 0, 50, 10, 1)

                # Step 2: Apply filters
                filtered = results_df[
                    (results_df["padj"] < padj_thresh) &
                    (results_df["log2FoldChange"].abs() >= lfc_thresh) &
                    (results_df["lfcSE"] <= lfc_se_thresh)
                ].copy()

                # Step 3: Volcano plot with labeling
                fig, ax = plt.subplots(figsize=(10, 6))

                ax.scatter(results_df["log2FoldChange"], results_df["-log10(padj)"], s=10, alpha=0.3, color="lightgray", label="All genes")
                ax.scatter(filtered["log2FoldChange"], filtered["-log10(padj)"], s=10, alpha=0.7, color="red", label="Significant")

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
                st.pyplot(fig)

                # Save plot
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format="png", dpi=300, bbox_inches='tight')
                img_buf.seek(0)
                st.download_button("📤 Download volcano plot (PNG)", data=img_buf, file_name="volcano_plot.png", mime="image/png")

                

                # Show GO enrichment section only if significant genes exist
                if len(filtered) > 0:
                    st.subheader("🧬 GO Enrichment (g:Profiler)")

                    if st.button("Run GO enrichment"):
                        try:
                            # Extract gene list
                            sig_genes = filtered["gene"].dropna().unique().tolist()

                            # Run enrichment
                            go_results = run_go_enrichment(sig_genes)

                            # Rename columns if necessary for compatibility
                            if "name" in go_results.columns and "term_name" not in go_results.columns:
                                go_results = go_results.rename(columns={"name": "term_name"})

                            # Show top GO results if present
                            expected_cols = ["source", "term_name", "p_value", "intersection_size"]
                            available_cols = [col for col in expected_cols if col in go_results.columns]

                            if go_results.empty or len(available_cols) == 0:
                                st.warning("No GO terms enriched or expected columns missing.")
                            else:
                                st.success(f"🧠 {len(go_results)} GO terms enriched")
                                st.dataframe(go_results[available_cols].head(20))

                                # Download button
                                csv = go_results.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    label="📥 Download GO enrichment results (CSV)",
                                    data=csv,
                                    file_name="go_enrichment.csv",
                                    mime="text/csv"
                                )

                        except Exception as e:
                            st.error(f"GO enrichment failed: {e}")


                # Significant genes table and download
                st.success(f"🧬 Significant genes: {len(filtered)}")
                st.dataframe(filtered[["gene", "log2FoldChange", "padj", "lfcSE"]].sort_values("padj").head(20))

                csv = filtered.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download significant genes (CSV)", data=csv, file_name="significant_genes.csv", mime='text/csv')







            

