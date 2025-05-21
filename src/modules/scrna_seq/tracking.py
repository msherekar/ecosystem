def _status(label, state="done"):
    icon = {"done": "✅", "pending": "⏳", "skipped": "➖", "error": "❌"}.get(state, "❓")
    return f"{icon} {label}"

def log_shape(stage, adata):
    n_cells, n_genes = adata.n_obs, adata.n_vars
    st.info(f"📊 After **{stage}** → Cells: `{n_cells}`, Genes: `{n_genes}`")