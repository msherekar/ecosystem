import streamlit as st
import scanpy as sc
import pandas as pd
import numpy as np
import scipy.sparse as sp

def _status(label, state="done"):
    icon = {"done": "✅", "pending": "⏳", "skipped": "➖", "error": "❌"}.get(state, "❓")
    return f"{icon} {label}"

def log_shape(stage, adata):
    n_cells, n_genes = adata.n_obs, adata.n_vars
    st.info(f"📊 After **{stage}** → Cells: `{n_cells}`, Genes: `{n_genes}`")

def show_scrnaseq_inputs():
    with st.expander(_status("1. Input Summary")):
        adata = st.session_state.get("adata")
        if adata is not None:
            st.success(f"Cells: {adata.n_obs}, Genes: {adata.n_vars}")
            st.dataframe(adata.obs.head())
        else:
            st.warning("No AnnData object found.")

def do_qc():
    with st.expander(_status("2. Quality Control")):
        if st.checkbox("▶️ Run QC", key="run_qc") and not st.session_state.get("qc_done"):
            adata = st.session_state["adata"]
            adata.var["mt"] = adata.var_names.str.startswith("MT-")
            sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
            st.session_state["adata"] = adata
            st.session_state["qc_done"] = True
            log_shape("QC", adata)
        elif st.session_state.get("qc_done"):
            st.info("✅ QC already completed.")

        if st.button("♻️ Reset QC"):
            st.session_state["qc_done"] = False

def do_filtering():
    with st.expander(_status("3. Filtering")):
        if st.checkbox("▶️ Run Filtering", key="run_filtering") and not st.session_state.get("filtered"):
            adata = st.session_state["adata"]
            sc.pp.filter_cells(adata, min_genes=200)
            sc.pp.filter_genes(adata, min_cells=3)
            st.session_state["adata"] = adata
            st.session_state["filtered"] = True
            log_shape("Filtering", adata)
        elif st.session_state.get("filtered"):
            st.info("✅ Filtering already applied.")

        if st.button("♻️ Reset Filtering"):
            st.session_state["filtered"] = False

def clean_invalid_values(adata):
    """Sanitize adata.X by replacing inf/nan values."""
    if sp.issparse(adata.X):
        # Convert to dense temporarily for cleaning
        X_dense = adata.X.toarray()
        has_sparse = True
    else:
        X_dense = adata.X
        has_sparse = False

    n_inf = np.isinf(X_dense).sum()
    n_nan = np.isnan(X_dense).sum()

    if n_inf > 0 or n_nan > 0:
        st.warning(f"⚠️ Found {n_inf} inf and {n_nan} NaN values. Replacing with 0.")
        X_dense[np.isinf(X_dense)] = 0
        X_dense[np.isnan(X_dense)] = 0

        if has_sparse:
            adata.X = sp.csr_matrix(X_dense)
        else:
            adata.X = X_dense

    return adata

def do_normalization():
    with st.expander(_status("4. Normalization & Log1p")):
        if st.checkbox("▶️ Run Normalization", key="run_normalization") and not st.session_state.get("normalized"):
            adata = st.session_state["adata"]
            sc.pp.normalize_total(adata, target_sum=1e4)
            sc.pp.log1p(adata)
            adata = clean_invalid_values(adata)
            st.session_state["adata"] = adata
            st.session_state["normalized"] = True
            log_shape("Normalization", adata)
        elif st.session_state.get("normalized"):
            st.info("✅ Normalization already applied.")

        if st.button("♻️ Reset Normalization"):
            st.session_state["normalized"] = False

def perform_dimensionality_reduction():
    with st.expander(_status("5. PCA & Variable Genes")):
        if st.checkbox("▶️ Run PCA", key="run_pca") and not st.session_state.get("pca_done"):
            try:
                adata = st.session_state["adata"]
                
                # IMPORTANT: Clean infinity values BEFORE highly_variable_genes
                st.text("Checking for infinity values in data...")
                
                # Handle sparse or dense matrices
                if sp.issparse(adata.X):
                    # For sparse matrix
                    X_data = adata.X.data
                    inf_count = np.sum(np.isinf(X_data))
                    if inf_count > 0:
                        st.warning(f"Found {inf_count} infinity values in data. Replacing with large finite values.")
                        X_data[np.isinf(X_data)] = np.finfo(X_data.dtype).max * 0.1
                else:
                    # For dense matrix
                    inf_count = np.sum(np.isinf(adata.X))
                    if inf_count > 0:
                        st.warning(f"Found {inf_count} infinity values in data. Replacing with large finite values.")
                        adata.X[np.isinf(adata.X)] = np.finfo(adata.X.dtype).max * 0.1
                
                # Also check for NaN values
                if sp.issparse(adata.X):
                    nan_count = np.sum(np.isnan(adata.X.data))
                    if nan_count > 0:
                        st.warning(f"Found {nan_count} NaN values in data. Replacing with zeros.")
                        adata.X.data[np.isnan(adata.X.data)] = 0
                else:
                    nan_count = np.sum(np.isnan(adata.X))
                    if nan_count > 0:
                        st.warning(f"Found {nan_count} NaN values in data. Replacing with zeros.")
                        adata.X[np.isnan(adata.X)] = 0
                
                # Now run highly_variable_genes with custom parameters
                st.text("Computing highly variable genes...")
                
                try:
                    # First try with default parameters but add flavor='seurat_v3' which is more robust
                    sc.pp.highly_variable_genes(adata, flavor='seurat_v3')
                except Exception as e1:
                    st.warning(f"First attempt failed: {str(e1)}")
                    try:
                        # Second attempt with flavor='seurat' which uses a different algorithm
                        sc.pp.highly_variable_genes(adata, flavor='seurat')
                    except Exception as e2:
                        st.warning(f"Second attempt failed: {str(e2)}")
                        try:
                            # Third attempt with flavor='cell_ranger' which is the most basic algorithm
                            sc.pp.highly_variable_genes(adata, flavor='cell_ranger', n_bins=20)
                        except Exception as e3:
                            st.error(f"All attempts failed. Last error: {str(e3)}")
                            
                            # Manual approach as last resort
                            st.text("Attempting manual variance calculation...")
                            if sp.issparse(adata.X):
                                means = np.array(adata.X.mean(axis=0)).flatten()
                                vars = np.array(adata.X.power(2).mean(axis=0)).flatten() - means**2
                            else:
                                means = np.mean(adata.X, axis=0)
                                vars = np.var(adata.X, axis=0)
                            
                            # Replace inf/nan values
                            means[np.isnan(means) | np.isinf(means)] = 0
                            vars[np.isnan(vars) | np.isinf(vars)] = 0
                            
                            # Create highly_variable column manually
                            dispersion = vars / (means + 0.0001)
                            dispersion[np.isnan(dispersion) | np.isinf(dispersion)] = 0
                            
                            # Select top 2000 genes by dispersion
                            adata.var['highly_variable'] = False
                            top_genes = np.argsort(dispersion)[::-1][:2000]
                            adata.var.iloc[top_genes, adata.var.columns.get_loc('highly_variable')] = True
                            
                            st.info(f"Manually identified {sum(adata.var['highly_variable'])} variable genes")
                
                # Check if we have highly variable genes
                if 'highly_variable' not in adata.var or sum(adata.var['highly_variable']) == 0:
                    st.error("No highly variable genes identified!")
                    return
                
                st.info(f"Found {sum(adata.var['highly_variable'])} highly variable genes")
                
                # Filter to highly variable genes
                adata = adata[:, adata.var.highly_variable]
                
                # Clean again before scaling
                adata = clean_invalid_values(adata)
                
                # Try safer scaling approach
                st.text("Scaling data with clipping to prevent extreme values...")
                try:
                    # Use max_value to prevent extreme outliers
                    sc.pp.scale(adata, max_value=10)
                except Exception as e:
                    st.warning(f"Standard scaling failed: {str(e)}")
                    try:
                        # Alternative scaling approach
                        st.text("Trying alternative scaling...")
                        if sp.issparse(adata.X):
                            adata.X = adata.X.toarray()
                        
                        # Manual scaling with clipping
                        X = adata.X
                        mean = np.mean(X, axis=0)
                        std = np.std(X, axis=0)
                        std[std == 0] = 1  # Avoid division by zero
                        X = (X - mean) / std
                        X[X > 10] = 10  # Clip large values
                        X[X < -10] = -10  # Clip small values
                        X[np.isnan(X) | np.isinf(X)] = 0  # Replace any remaining invalid values
                        adata.X = X
                    except Exception as e2:
                        st.error(f"All scaling attempts failed: {str(e2)}")
                        return
                
                # Run PCA
                st.text("Computing PCA...")
                try:
                    sc.tl.pca(adata)
                except Exception as e:
                    st.warning(f"Standard PCA failed: {str(e)}")
                    try:
                        # Try alternative PCA parameters
                        sc.tl.pca(adata, svd_solver='randomized', n_comps=30)
                    except Exception as e2:
                        st.error(f"All PCA attempts failed: {str(e2)}")
                        return
                
                # Save results
                st.session_state["adata"] = adata
                st.session_state["pca_done"] = True
                log_shape("PCA", adata)
                st.success("✅ PCA completed successfully!")
                
            except Exception as e:
                st.error(f"Error during dimensionality reduction: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
        elif st.session_state.get("pca_done"):
            st.info("✅ PCA already completed.")

        if st.button("♻️ Reset PCA"):
            st.session_state["pca_done"] = False

def perform_clustering():
    with st.expander(_status("6. Clustering with Leiden")):
        if st.checkbox("▶️ Run Clustering", key="run_clustering") and not st.session_state.get("clustered"):
            try:
                adata = st.session_state["adata"]

                # Step 1: Calculate neighbors
                st.text("Computing neighbors...")
                sc.pp.neighbors(adata)

                # Step 2: Run UMAP
                st.text("Computing UMAP projection...")
                sc.tl.umap(adata)

                # Step 3: Run clustering
                st.text("Computing Leiden clustering...")
                sc.tl.leiden(adata)

                # 🧪 DEBUG: show what's actually computed
                st.write("obsm keys after clustering:", list(adata.obsm.keys()))
                st.write("obs columns after clustering:", list(adata.obs.columns))

                # ✅ Validate before saving to session
                if "X_umap" in adata.obsm and "leiden" in adata.obs:
                    st.session_state["adata"] = adata
                    st.session_state["clustered"] = True
                    st.session_state["has_umap"] = True
                    st.session_state["has_leiden"] = True
                    st.success("✅ UMAP and Leiden clustering completed successfully.")
                else:
                    # Save what we have and track what's missing
                    st.session_state["adata"] = adata
                    st.session_state["has_umap"] = "X_umap" in adata.obsm
                    st.session_state["has_leiden"] = "leiden" in adata.obs
                    st.session_state["clustered"] = False
                    st.error("❌ UMAP or Leiden results missing. Clustering incomplete.")

            except Exception as e:
                st.error(f"Error during clustering: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        elif st.session_state.get("clustered"):
            st.info("✅ Clustering already completed.")

        if st.button("♻️ Reset Clustering", key="reset_clustering"):
            st.session_state["clustered"] = False
            st.session_state["has_umap"] = False
            st.session_state["has_leiden"] = False
            st.experimental_rerun()

def create_visualization():
    with st.expander(_status("7. UMAP Visualization")):
        # First show any action buttons that might need to run regardless of other checkboxes
        col1, col2 = st.columns(2)
        
        with col1:
            # Button to run UMAP if missing
            if not st.session_state.get("has_umap", False) and "adata" in st.session_state:
                if st.button("🔄 Run UMAP", key="run_umap_fix"):
                    adata = st.session_state["adata"]
                    # Make sure we have neighbors first
                    try:
                        sc.pp.neighbors(adata)
                        sc.tl.umap(adata)
                        st.session_state["adata"] = adata
                        st.session_state["has_umap"] = True
                        if st.session_state.get("has_leiden", False):
                            st.session_state["clustered"] = True
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error running UMAP: {str(e)}")
        
        with col2:
            # Button to run Leiden if missing
            if not st.session_state.get("has_leiden", False) and "adata" in st.session_state:
                if st.button("🔄 Run Leiden", key="run_leiden_fix"):
                    adata = st.session_state["adata"]
                    try:
                        sc.tl.leiden(adata)
                        st.session_state["adata"] = adata
                        st.session_state["has_leiden"] = True
                        if st.session_state.get("has_umap", False):
                            st.session_state["clustered"] = True
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error running Leiden: {str(e)}")
        
        # Now handle the main visualization
        if st.checkbox("▶️ Show UMAP", key="show_umap"):
            if "adata" not in st.session_state:
                st.warning("⚠️ No AnnData object found in session.")
                return
                
            adata = st.session_state["adata"]
            st.write("✅ adata loaded")
            st.write("🔍 Has UMAP:", st.session_state.get("has_umap", 'X_umap' in adata.obsm))
            st.write("🔍 Has Leiden:", st.session_state.get("has_leiden", 'leiden' in adata.obs))
            
            # Update the state flags based on actual data
            has_umap = 'X_umap' in adata.obsm
            has_leiden = 'leiden' in adata.obs
            st.session_state["has_umap"] = has_umap
            st.session_state["has_leiden"] = has_leiden
            
            if not has_umap or not has_leiden:
                st.warning("⚠️ Clustering is incomplete. Please use the buttons above to complete the process.")
                return
                
            try:
                # If everything is available, create the plot
                fig = sc.pl.umap(adata, color="leiden", return_fig=True, show=False)
                st.pyplot(fig)
                
                # Add option to save the figure
                if st.button("💾 Save UMAP figure", key="save_umap"):
                    fig.savefig("umap_clusters.png", dpi=300, bbox_inches='tight')
                    st.success("Figure saved as 'umap_clusters.png'")
                
            except Exception as e:
                st.error(f"Error visualizing UMAP: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

def run_differential_expression():
    with st.expander(_status("8. Differential Expression")):
        # Check for leiden data availability first
        if "adata" in st.session_state:
            adata = st.session_state["adata"]
            has_leiden = st.session_state.get("has_leiden", 'leiden' in adata.obs)
            
            if not has_leiden:
                st.warning("⚠️ Leiden clustering results not found. Please run clustering first.")
                
                # Offer a quick fix button
                if st.button("🔄 Run Leiden Clustering", key="run_leiden_for_deg"):
                    try:
                        # Check if we need to compute neighbors first
                        if 'neighbors' not in adata.uns:
                            st.info("Computing neighbors first...")
                            sc.pp.neighbors(adata)
                        
                        sc.tl.leiden(adata)
                        st.session_state["adata"] = adata
                        st.session_state["has_leiden"] = True
                        if st.session_state.get("has_umap", False):
                            st.session_state["clustered"] = True
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error running Leiden clustering: {str(e)}")
                return
        
        # Now perform DEG analysis if conditions are met
        if st.checkbox("▶️ Run DEG", key="run_deg") and not st.session_state.get("deg_done"):
            try:
                adata = st.session_state["adata"]
                
                # Double-check leiden exists before proceeding
                if 'leiden' not in adata.obs:
                    st.error("Leiden clustering results not found. Cannot perform differential expression.")
                    return
                
                # Run the differential expression analysis
                st.info("Running differential expression analysis...")
                sc.tl.rank_genes_groups(adata, "leiden", method="t-test")
                
                # Check if the analysis was successful
                if 'rank_genes_groups' not in adata.uns:
                    st.error("Differential expression analysis failed. No results found.")
                    return
                    
                # Plot the results
                fig = sc.pl.rank_genes_groups(adata, sharey=False, return_fig=True, show=False)
                st.pyplot(fig)
                
                # Save state
                st.session_state["adata"] = adata
                st.session_state["deg_done"] = True
                st.success("✅ Differential expression analysis completed successfully.")
                
            except Exception as e:
                st.error(f"Error during differential expression analysis: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
        elif st.session_state.get("deg_done"):
            st.info("✅ DEG already run.")
            
            # Option to show the results again
            if st.button("🔍 Show DEG Results Again", key="show_deg_again"):
                try:
                    adata = st.session_state["adata"]
                    fig = sc.pl.rank_genes_groups(adata, sharey=False, return_fig=True, show=False)
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"Error displaying results: {str(e)}")

        if st.button("♻️ Reset DEG", key="reset_deg"):
            st.session_state["deg_done"] = False
            st.experimental_rerun()

def export_outputs():
    with st.expander(_status("📤 Export Processed Data")):
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

# Placeholder functions (not changed)
def run_go_enrichment(): pass
def run_pathway_enrichment(): pass
def run_cell_cycle_analysis(): pass
def run_marker_gene_identification(): pass
def run_trajectory_analysis(): pass
def run_single_cell_networks(): pass
def apply_ML(): pass
def perform_fine_tuning(): pass

def run_scrnaseq_pipeline():
    if "adata" not in st.session_state:
        st.warning("⚠️ No AnnData object found. Please upload your scRNA-seq file.")
        return

    show_scrnaseq_inputs()
    do_qc()
    do_filtering()
    do_normalization()
    perform_dimensionality_reduction()
    perform_clustering()
    create_visualization()
    run_differential_expression()
    export_outputs()  # ⬅️ New block for exporting .h5ad and .csv
    run_go_enrichment()
    run_pathway_enrichment()
    run_cell_cycle_analysis()
    run_marker_gene_identification()
    run_trajectory_analysis()
    run_single_cell_networks()
    apply_ML()
    perform_fine_tuning()
