import streamlit as st

# Default pipeline step flags to reset when a new file is loaded or workflow restarted
DEFAULT_STEPS = [
    "qc_done",
    "filtered",
    "normalized",
    "reduced",
    "clustered",
    "de_analysis_done",
    "go_enriched",
    "pathway_enriched",
    "cell_cycle_done",
    "marker_genes_done",
    "trajectory_done",
    "networks_done",
    "ml_applied",
    "fine_tuned"
]

STATE_ICONS = {
    "done": "✅",
    "pending": "⏳",
    "skipped": "➖",
    "error": "❌"
}


def status(label: str, state: str = "done") -> str:
    """
    Return a status string with icon and label for UI expanders.
    """
    icon = STATE_ICONS.get(state, "❓")
    return f"{icon} {label}"


def log_shape(stage: str, adata) -> None:
    """
    Log the current shape of the AnnData object (cells, genes).
    """
    n_cells, n_genes = adata.n_obs, adata.n_vars
    st.info(f"📊 After **{stage}** → Cells: `{n_cells}`, Genes: `{n_genes}`")


def reset_steps(steps: list[str] = None) -> None:
    """
    Reset pipeline step flags in session_state. Clears completion flags.
    """
    to_reset = steps if steps is not None else DEFAULT_STEPS
    for flag in to_reset:
        st.session_state.pop(flag, None)
