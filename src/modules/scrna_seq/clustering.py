import streamlit as st
import scanpy as sc
import numpy as np
import scipy.sparse as sp
from src.modules.scrna_seq.tracking import _status, log_shape
from src.modules.scrna_seq.clean import clean_invalid_values    


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