"""
scRNA-seq Pipeline Configuration
Defines the pipeline steps, their order, and metadata.
"""

from src.modules.scrna_seq.inputs import show_scrnaseq_inputs
from src.modules.scrna_seq.qc import do_qc
from src.modules.scrna_seq.filtering import do_filtering
from src.modules.scrna_seq.normalization import do_normalization
from src.modules.scrna_seq.reduction import perform_dimensionality_reduction
from src.modules.scrna_seq.clustering import perform_clustering
from src.modules.scrna_seq.visualization import create_visualization
from src.modules.scrna_seq.dea import run_differential_expression
from src.modules.scrna_seq.export import export_outputs
from src.modules.scrna_seq.enrichment import run_go_enrichment, run_pathway_enrichment
from src.modules.scrna_seq.analysis import run_cell_cycle_analysis
from src.modules.scrna_seq.identification import run_marker_gene_identification
from src.modules.scrna_seq.analysis import run_trajectory_analysis
from src.modules.scrna_seq.networks import run_single_cell_networks
from src.modules.scrna_seq.ml import apply_ML
from src.modules.scrna_seq.tuning import perform_fine_tuning

# Pipeline step configuration
SCRNA_STEP_ORDER = [
    {
        "key": "input_summary",
        "function": show_scrnaseq_inputs,
        "title": "📊 Data Summary",
        "done_flag": "input_summary_done",
        "description": "Load and summarize scRNA-seq data",
        "automated": False  # Skip in automated pipeline
    },
    {
        "key": "qc",
        "function": do_qc,
        "title": "🧼 Quality Control",
        "done_flag": "qc_done",
        "description": "Calculate QC metrics and identify outliers",
        "automated": True
    },
    {
        "key": "filtering",
        "function": do_filtering,
        "title": "🧹 Filtering",
        "done_flag": "filtering_done",
        "description": "Filter cells and genes based on QC metrics",
        "automated": True
    },
    {
        "key": "normalization",
        "function": do_normalization,
        "title": "⚖️ Normalization",
        "done_flag": "normalization_done",
        "description": "Normalize and log-transform expression data",
        "automated": True
    },
    {
        "key": "dimred",
        "function": perform_dimensionality_reduction,
        "title": "🔬 Dimensionality Reduction",
        "done_flag": "dimred_done",
        "description": "Identify HVGs and perform PCA",
        "automated": True
    },
    {
        "key": "clustering",
        "function": perform_clustering,
        "title": "🔗 Clustering",
        "done_flag": "clustering_done",
        "description": "Cluster cells and compute UMAP",
        "automated": True
    },
    {
        "key": "viz",
        "function": create_visualization,
        "title": "🧬 Visualization",
        "done_flag": "viz_done",
        "description": "Create interactive visualizations",
        "automated": True
    },
    {
        "key": "dea",
        "function": lambda: (run_differential_expression(), export_outputs()),
        "title": "🆚 Differential Expression",
        "done_flag": "dea_done",
        "description": "Find marker genes for each cluster",
        "automated": True
    },
    {
        "key": "enrichment",
        "function": lambda: (run_go_enrichment(), run_pathway_enrichment()),
        "title": "🔬 Enrichment",
        "done_flag": "enrichment_done",
        "description": "Perform GO and pathway enrichment analysis",
        "automated": True
    },
    {
        "key": "markers",
        "function": lambda: (run_cell_cycle_analysis(), run_marker_gene_identification()),
        "title": "⏳ Marker Genes & Cell Cycle",
        "done_flag": "markers_done",
        "description": "Analyze cell cycle and identify markers",
        "automated": False  # Advanced analysis
    },
    {
        "key": "trajectory",
        "function": run_trajectory_analysis,
        "title": "🧭 Trajectory",
        "done_flag": "trajectory_done",
        "description": "Perform trajectory analysis",
        "automated": False  # Advanced analysis
    },
    {
        "key": "ml",
        "function": lambda: (run_single_cell_networks(), apply_ML(), perform_fine_tuning()),
        "title": "🌐 ML & Networks",
        "done_flag": "ml_done",
        "description": "Apply machine learning and network analysis",
        "automated": False  # Advanced analysis
    },
]

def get_step_by_key(step_key):
    """Get step configuration by key."""
    for step in SCRNA_STEP_ORDER:
        if step["key"] == step_key:
            return step
    return None

def get_automated_steps():
    """Get only the steps that should be included in automated pipeline."""
    return [step for step in SCRNA_STEP_ORDER if step.get("automated", False)]

def get_next_step(current_step_key):
    """Get the next step in the pipeline."""
    for i, step in enumerate(SCRNA_STEP_ORDER):
        if step["key"] == current_step_key and i + 1 < len(SCRNA_STEP_ORDER):
            return SCRNA_STEP_ORDER[i + 1]
    return None 