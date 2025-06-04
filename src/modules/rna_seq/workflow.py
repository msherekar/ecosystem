import streamlit as st
from src.modules.rna_seq.preprocessing import validate_and_clean_counts
from src.modules.rna_seq.pydeseq import run_pydeseq2
from src.modules.rna_seq.filters import get_filter_settings
from src.modules.rna_seq.volcano import volcano_plot
from src.modules.rna_seq.download import download_csv, download_png
from src.modules.rna_seq.go import gprofiler_enrichment
from src.modules.rna_seq.go_plots import plot_go_bar, plot_go_bubble, plot_go_faceted, plot_go_plotly

def do_preprocessing():
    if "rnaseq_counts_df" not in st.session_state:
        st.info("⬆️ Please upload a counts file before preprocessing.")
        return  # Don't run until counts file is uploaded
    df = st.session_state["rnaseq_counts_df"]
    if st.button("Run Preprocessing", key="workflow_preprocessing_button"):
        cleaned_df = validate_and_clean_counts(df)
        st.session_state["rnaseq_counts_cleaned"] = cleaned_df
        st.write("✅ Cleaned Counts (top rows):")
        st.dataframe(cleaned_df.head())

def run_deseq2():
    if "rnaseq_counts_cleaned" not in st.session_state:
        st.info("ℹ️ Please run preprocessing first.")
        return
    if "rnaseq_metadata_df" not in st.session_state:
        st.info("ℹ️ Please upload a metadata file before running DESeq2.")
        return

    st.subheader("Differential Expression (PyDESeq2)")

    if st.button("Run PyDESeq2", key="deseq2_button"):
        try:
            results_df = run_pydeseq2(
                st.session_state["rnaseq_counts_cleaned"],
                st.session_state["rnaseq_metadata_df"]
            )
            st.session_state["deseq_results"] = results_df
            st.success("✅ Differential expression analysis complete.")
        except Exception as e:
            st.error(f"Error during DE analysis: {e}")


def make_volcano_plot():
    if "deseq_results" not in st.session_state:
        st.info("ℹ️ Run DESeq2 to generate volcano plot.")
        return

    st.subheader("Volcano Plot and Filtering")

    results_df = st.session_state["deseq_results"]
    padj_thresh, lfc_thresh, lfc_se_thresh, top_n_genes = get_filter_settings()

    fig, filtered = volcano_plot(results_df, padj_thresh, lfc_thresh, lfc_se_thresh, top_n_genes)
    st.pyplot(fig)

    download_png(fig)
    download_csv(filtered, "significant_genes.csv")

    st.session_state["filtered_genes"] = filtered


def run_go_enrichment():
    if "filtered_genes" not in st.session_state:
        st.info("ℹ️ Please run the volcano plot to identify significant genes.")
        return

    filtered = st.session_state["filtered_genes"]
    if len(filtered) == 0:
        st.warning("No significant genes to enrich.")
        return

    if st.button("🧬 Run GO enrichment (g:Profiler)", key="go_enrichment_button"):
        try:
            sig_genes = filtered["gene"].dropna().unique().tolist()
            go_results = gprofiler_enrichment(sig_genes)

            if "name" in go_results.columns and "term_name" not in go_results.columns:
                go_results = go_results.rename(columns={"name": "term_name"})

            show_cols = [col for col in ["source", "term_name", "p_value", "intersection_size"] if col in go_results.columns]
            if not go_results.empty:
                st.success(f"🧠 {len(go_results)} GO terms enriched")
                st.dataframe(go_results[show_cols].head(20))
                download_csv(go_results, "go_enrichment.csv")
                
                # Store GO results in session state for agent analysis
                st.session_state["go_results"] = go_results
            
                # --- Sort options ---
                sort_options = {
                    "Significance (p-value)": "p_value",
                    "Intersection Size": "intersection_size",
                    "GO Term Size": "term_size" if "term_size" in go_results.columns else "intersection_size"}

                sort_choice = st.selectbox("Sort GO terms by:", list(sort_options.keys()), index=0)
                sort_column = sort_options[sort_choice]

                # --- Apply sorting and slicing ---
                go_sorted = go_results.sort_values(sort_column).copy()
                top_n = st.slider("Top N GO terms to visualize", 5, 50, 15, 1)
                go_top = go_sorted.head(top_n)

                
                # Let user filter GO sources
                available_sources = sorted(go_results["source"].unique())
                selected_sources = st.multiselect(
                    "Select GO categories to display",
                    options=available_sources,
                    default=["GO:BP", "GO:MF", "GO:CC"])

                filtered_go = go_results[go_results["source"].isin(selected_sources)]


                # ✅ GO plot from separate module
                # Basic Bar Plot
                fig_bar = plot_go_bar(go_top)
                st.subheader("📊 Bar Plot")
                st.pyplot(fig_bar)
                download_png(fig_bar, "go_barplot.png")

                # Bubble Plot
                fig_bubble = plot_go_bubble(go_top)
                st.subheader("🫧 Bubble Plot")
                st.pyplot(fig_bubble)
                download_png(fig_bubble, "go_bubbleplot.png")

                # Faceted GO Category Plot
                fig_facet = plot_go_faceted(go_top)
                st.subheader("🧠 Faceted Plot by GO Category")
                st.pyplot(fig_facet)
                download_png(fig_facet, "go_facetedplot.png")

                # Interactive Plotly
                st.subheader("⚡ Interactive Plot")
                fig_interactive = plot_go_plotly(go_top)
                st.plotly_chart(fig_interactive, use_container_width=True, key="go_interactive_plot")

            else:
                st.warning("No GO terms enriched at default thresholds.")
        except Exception as e:
            st.error(f"GO enrichment failed: {e}")

def run_rnaseq_pipeline():
    do_preprocessing()
    run_deseq2()
    make_volcano_plot()
    run_go_enrichment()