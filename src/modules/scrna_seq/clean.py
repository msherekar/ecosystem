import streamlit as st
import scanpy as sc
import numpy as np
import scipy.sparse as sp

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