"""
Interactive Plotly plots for Differential Expression Analysis (DEA)
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import scanpy as sc


def plot_dea_volcano_plotly(anndata, cluster_id, n_markers=10):
    """
    Interactive volcano plot using Plotly
    """
    try:
        # Extract data for selected cluster
        names = anndata.uns['rank_genes_groups']['names'][cluster_id]
        
        # Get p-values and log fold changes
        if 'pvals_adj' in anndata.uns['rank_genes_groups']:
            pvals = anndata.uns['rank_genes_groups']['pvals_adj'][cluster_id]
        else:
            pvals = anndata.uns['rank_genes_groups']['pvals'][cluster_id]
            
        if 'logfoldchanges' in anndata.uns['rank_genes_groups']:
            logfc = anndata.uns['rank_genes_groups']['logfoldchanges'][cluster_id]
        else:
            logfc = anndata.uns['rank_genes_groups']['scores'][cluster_id]
        
        # Convert to arrays and handle NaN values
        names = np.array(names)
        pvals = np.array(pvals, dtype=float)
        logfc = np.array(logfc, dtype=float)
        
        # Check if log fold changes are mostly NaN and calculate manually if needed
        nan_count = np.sum(np.isnan(logfc))
        if nan_count > len(logfc) * 0.5:  # If more than 50% are NaN
            st.info("Log fold changes contain many NaN values. Calculating manually...")
            
            # Calculate log fold changes manually
            cluster_mask = anndata.obs['leiden'] == cluster_id
            other_mask = anndata.obs['leiden'] != cluster_id
            
            logfc_manual = []
            for gene_name in names:
                if gene_name in anndata.var_names:
                    gene_idx = list(anndata.var_names).index(gene_name)
                    
                    # Get expression for this gene
                    cluster_expr = anndata.X[cluster_mask, gene_idx]
                    other_expr = anndata.X[other_mask, gene_idx]
                    
                    if hasattr(cluster_expr, 'toarray'):
                        cluster_expr = cluster_expr.toarray().flatten()
                        other_expr = other_expr.toarray().flatten()
                    
                    # Calculate mean expression (add small pseudocount to avoid log(0))
                    cluster_mean = np.mean(cluster_expr) + 1e-9
                    other_mean = np.mean(other_expr) + 1e-9
                    
                    # Calculate log2 fold change
                    log2fc = np.log2(cluster_mean / other_mean)
                    logfc_manual.append(log2fc)
                else:
                    logfc_manual.append(0.0)
            
            logfc = np.array(logfc_manual)
            st.success("✅ Log fold changes calculated successfully!")
        
        # Filter valid data
        valid_mask = ~(np.isnan(pvals) | np.isnan(logfc) | np.isinf(pvals) | np.isinf(logfc))
        
        if not np.any(valid_mask):
            st.warning("⚠️ No valid data for volcano plot")
            return None
            
        names_valid = names[valid_mask]
        pvals_valid = pvals[valid_mask]
        logfc_valid = logfc[valid_mask]
        
        # Handle zero p-values
        pvals_valid = np.where(pvals_valid <= 0, 1e-300, pvals_valid)
        
        # Calculate -log10(p-values)
        neg_log_pvals = -np.log10(pvals_valid)
        
        # Create DataFrame for plotting
        df = pd.DataFrame({
            'gene': names_valid,
            'log_fc': logfc_valid,
            'neg_log_pval': neg_log_pvals,
            'pval': pvals_valid
        })
        
        # Determine significance and effect size
        df['significant'] = (df['pval'] < 0.05) & (np.abs(df['log_fc']) > 0.5)
        df['category'] = 'Not Significant'
        df.loc[(df['pval'] < 0.05) & (df['log_fc'] > 0.5), 'category'] = 'Upregulated'
        df.loc[(df['pval'] < 0.05) & (df['log_fc'] < -0.5), 'category'] = 'Downregulated'
        df.loc[(df['pval'] < 0.05) & (np.abs(df['log_fc']) <= 0.5), 'category'] = 'Significant'
        
        # Get top markers for labeling
        top_indices = np.argsort(pvals_valid)[:n_markers]
        df['is_top'] = False
        df.iloc[top_indices, df.columns.get_loc('is_top')] = True
        
        # Create interactive volcano plot
        fig = px.scatter(
            df,
            x='log_fc',
            y='neg_log_pval',
            color='category',
            hover_data={
                'gene': True,
                'pval': ':.2e',
                'log_fc': ':.3f',
                'neg_log_pval': ':.2f'
            },
            color_discrete_map={
                'Upregulated': '#FF6B6B',
                'Downregulated': '#4ECDC4', 
                'Significant': '#45B7D1',
                'Not Significant': '#95A5A6'
            },
            title=f'🌋 Interactive Volcano Plot - Cluster {cluster_id}',
            labels={
                'log_fc': 'Log2 Fold Change',
                'neg_log_pval': '-Log10(P-value)',
                'gene': 'Gene'
            }
        )
        
        # Add significance threshold lines
        fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="gray", 
                     annotation_text="p=0.05", annotation_position="right")
        fig.add_vline(x=0.5, line_dash="dash", line_color="gray")
        fig.add_vline(x=-0.5, line_dash="dash", line_color="gray")
        
        # Add gene labels for top markers
        top_genes = df[df['is_top']]
        for _, gene_data in top_genes.iterrows():
            fig.add_annotation(
                x=gene_data['log_fc'],
                y=gene_data['neg_log_pval'],
                text=gene_data['gene'],
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1,
                arrowcolor="black",
                font=dict(size=10)
            )
        
        fig.update_layout(
            width=800,
            height=600,
            showlegend=True,
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Volcano plot failed: {e}")
        return None


def plot_dea_heatmap_plotly(anndata, n_genes=5):
    """
    Interactive heatmap of top marker genes using Plotly
    """
    try:
        # Get top genes for each cluster
        groups = anndata.uns['rank_genes_groups']['names'].dtype.names
        top_genes = []
        
        for group in groups:
            genes = anndata.uns['rank_genes_groups']['names'][group][:n_genes]
            top_genes.extend(genes)
        
        # Remove duplicates while preserving order
        unique_genes = []
        seen = set()
        for gene in top_genes:
            if gene not in seen:
                unique_genes.append(gene)
                seen.add(gene)
        
        # Get expression data for these genes
        gene_indices = [i for i, gene in enumerate(anndata.var_names) if gene in unique_genes]
        if not gene_indices:
            st.warning("⚠️ No marker genes found in expression data")
            return None
            
        # Calculate mean expression per cluster
        cluster_means = []
        cluster_labels = []
        
        for group in groups:
            cluster_mask = anndata.obs['leiden'] == group
            if np.any(cluster_mask):
                cluster_expr = anndata.X[cluster_mask, :][:, gene_indices]
                if hasattr(cluster_expr, 'toarray'):
                    cluster_expr = cluster_expr.toarray()
                mean_expr = np.mean(cluster_expr, axis=0)
                cluster_means.append(mean_expr)
                cluster_labels.append(f'Cluster {group}')
        
        if not cluster_means:
            st.warning("⚠️ No cluster data found")
            return None
            
        # Create heatmap data
        heatmap_data = np.array(cluster_means)
        gene_names = [anndata.var_names[i] for i in gene_indices]
        
        # Create interactive heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=gene_names,
            y=cluster_labels,
            colorscale='RdBu_r',
            hoverongaps=False,
            hovertemplate='Cluster: %{y}<br>Gene: %{x}<br>Expression: %{z:.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='🔥 Interactive Heatmap - Top Marker Genes',
            xaxis_title='Genes',
            yaxis_title='Clusters',
            width=max(600, len(gene_names) * 40),
            height=max(400, len(cluster_labels) * 50)
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Heatmap failed: {e}")
        return None


def plot_dea_dotplot_plotly(anndata, n_genes=5):
    """
    Interactive dot plot showing marker gene expression using Plotly
    """
    try:
        # Get data similar to heatmap but create dot plot
        groups = anndata.uns['rank_genes_groups']['names'].dtype.names
        
        plot_data = []
        for group in groups:
            genes = anndata.uns['rank_genes_groups']['names'][group][:n_genes]
            scores = anndata.uns['rank_genes_groups']['scores'][group][:n_genes] if 'scores' in anndata.uns['rank_genes_groups'] else [1] * n_genes
            pvals = anndata.uns['rank_genes_groups']['pvals_adj'][group][:n_genes] if 'pvals_adj' in anndata.uns['rank_genes_groups'] else [0.01] * n_genes
            
            for gene, score, pval in zip(genes, scores, pvals):
                # Calculate expression percentage and mean expression
                cluster_mask = anndata.obs['leiden'] == group
                if gene in anndata.var_names and np.any(cluster_mask):
                    gene_idx = list(anndata.var_names).index(gene)
                    expr_data = anndata.X[cluster_mask, gene_idx]
                    if hasattr(expr_data, 'toarray'):
                        expr_data = expr_data.toarray().flatten()
                    
                    pct_expressed = np.mean(expr_data > 0) * 100
                    mean_expr = np.mean(expr_data)
                    
                    plot_data.append({
                        'cluster': f'Cluster {group}',
                        'gene': gene,
                        'mean_expression': mean_expr,
                        'pct_expressed': pct_expressed,
                        'score': score,
                        'pval': pval,
                        'neg_log_pval': -np.log10(max(pval, 1e-300))
                    })
        
        if not plot_data:
            st.warning("⚠️ No data for dot plot")
            return None
            
        df = pd.DataFrame(plot_data)
        
        # Create interactive dot plot
        fig = px.scatter(
            df,
            x='gene',
            y='cluster',
            size='pct_expressed',
            color='mean_expression',
            hover_data={
                'gene': True,
                'cluster': True,
                'mean_expression': ':.3f',
                'pct_expressed': ':.1f',
                'pval': ':.2e'
            },
            color_continuous_scale='Reds',
            title='🎯 Interactive Dot Plot - Marker Gene Expression',
            labels={
                'gene': 'Gene',
                'cluster': 'Cluster',
                'mean_expression': 'Mean Expression',
                'pct_expressed': '% Expressed'
            }
        )
        
        fig.update_layout(
            width=max(800, len(df['gene'].unique()) * 60),
            height=max(500, len(df['cluster'].unique()) * 80),
            xaxis={'tickangle': 45}
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Dot plot failed: {e}")
        return None


def plot_dea_summary_plotly(anndata):
    """
    Summary plot showing number of significant genes per cluster
    """
    try:
        groups = anndata.uns['rank_genes_groups']['names'].dtype.names
        
        summary_data = []
        for group in groups:
            if 'pvals_adj' in anndata.uns['rank_genes_groups']:
                pvals = anndata.uns['rank_genes_groups']['pvals_adj'][group]
            else:
                pvals = anndata.uns['rank_genes_groups']['pvals'][group]
                
            n_significant = np.sum(np.array(pvals) < 0.05)
            n_highly_significant = np.sum(np.array(pvals) < 0.01)
            
            summary_data.append({
                'cluster': f'Cluster {group}',
                'p < 0.05': n_significant,
                'p < 0.01': n_highly_significant
            })
        
        df = pd.DataFrame(summary_data)
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='p < 0.05',
            x=df['cluster'],
            y=df['p < 0.05'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='p < 0.01',
            x=df['cluster'],
            y=df['p < 0.01'],
            marker_color='darkblue'
        ))
        
        fig.update_layout(
            title='📊 Number of Significant Marker Genes per Cluster',
            xaxis_title='Cluster',
            yaxis_title='Number of Genes',
            barmode='group',
            width=600,
            height=400
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Summary plot failed: {e}")
        return None