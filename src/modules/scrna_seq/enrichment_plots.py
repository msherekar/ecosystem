"""
Interactive Plotly plots for Enrichment Analysis
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def plot_go_bar_plotly(go_df, top_n=15):
    """
    Interactive horizontal bar plot for GO terms using Plotly
    """
    try:
        if len(go_df) == 0:
            st.warning("⚠️ No GO terms to plot")
            return None
            
        # Prepare data
        df = go_df.copy()
        
        # Handle different column names from g:Profiler
        pval_col = 'p_value' if 'p_value' in df.columns else 'p_val'
        term_col = 'term_name' if 'term_name' in df.columns else ('name' if 'name' in df.columns else 'description')
        
        if pval_col not in df.columns or term_col not in df.columns:
            st.error("❌ Required columns not found in GO results")
            return None
            
        # Filter and sort
        df = df[df[pval_col] < 0.05].sort_values(pval_col).head(top_n)
        df['-log10(p)'] = -np.log10(df[pval_col])
        
        # Truncate long term names
        df['short_term'] = df[term_col].apply(lambda x: x[:60] + '...' if len(x) > 60 else x)
        
        # Create interactive bar plot
        fig = px.bar(
            df,
            x='-log10(p)',
            y='short_term',
            orientation='h',
            color='-log10(p)',
            color_continuous_scale='Viridis',
            hover_data={
                term_col: True,
                pval_col: ':.2e',
                'intersection_size': True if 'intersection_size' in df.columns else False,
                'source': True if 'source' in df.columns else False
            },
            title=f'🧬 Top {len(df)} Enriched GO Terms',
            labels={
                '-log10(p)': '-Log10(P-value)',
                'short_term': 'GO Term',
                term_col: 'Full Term Name'
            }
        )
        
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            width=900,
            height=max(400, len(df) * 25),
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ GO bar plot failed: {e}")
        return None


def plot_go_bubble_plotly(go_df, top_n=20):
    """
    Interactive bubble plot for GO terms using Plotly
    """
    try:
        if len(go_df) == 0:
            st.warning("⚠️ No GO terms to plot")
            return None
            
        # Prepare data
        df = go_df.copy()
        
        # Handle different column names
        pval_col = 'p_value' if 'p_value' in df.columns else 'p_val'
        term_col = 'term_name' if 'term_name' in df.columns else ('name' if 'name' in df.columns else 'description')
        size_col = 'intersection_size' if 'intersection_size' in df.columns else 'query_size'
        
        if pval_col not in df.columns or term_col not in df.columns:
            st.error("❌ Required columns not found in GO results")
            return None
            
        # Filter and prepare
        df = df[df[pval_col] < 0.05].sort_values(pval_col).head(top_n)
        df['-log10(p)'] = -np.log10(df[pval_col])
        df['short_term'] = df[term_col].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
        
        # Set default size if column doesn't exist
        if size_col not in df.columns:
            df[size_col] = 10
            
        # Create bubble plot
        fig = px.scatter(
            df,
            x='-log10(p)',
            y='short_term',
            size=size_col,
            color='source' if 'source' in df.columns else None,
            hover_data={
                term_col: True,
                pval_col: ':.2e',
                size_col: True,
                'source': True if 'source' in df.columns else False
            },
            title=f'🫧 GO Enrichment Bubble Plot (Size = {size_col.replace("_", " ").title()})',
            labels={
                '-log10(p)': '-Log10(P-value)',
                'short_term': 'GO Term',
                size_col: size_col.replace('_', ' ').title()
            },
            size_max=30
        )
        
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            width=900,
            height=max(500, len(df) * 30),
            showlegend=True if 'source' in df.columns else False
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ GO bubble plot failed: {e}")
        return None


def plot_go_faceted_plotly(go_df, top_n=10):
    """
    Faceted bar plot for different GO categories using Plotly subplots
    """
    try:
        if len(go_df) == 0:
            st.warning("⚠️ No GO terms to plot")
            return None
            
        # Prepare data
        df = go_df.copy()
        
        # Handle different column names
        pval_col = 'p_value' if 'p_value' in df.columns else 'p_val'
        term_col = 'term_name' if 'term_name' in df.columns else ('name' if 'name' in df.columns else 'description')
        
        if 'source' not in df.columns:
            st.warning("⚠️ No source column found for faceting")
            return plot_go_bar_plotly(go_df, top_n)
            
        # Filter for GO categories
        go_categories = ['GO:BP', 'GO:MF', 'GO:CC']
        df = df[df['source'].isin(go_categories)]
        
        if len(df) == 0:
            st.warning("⚠️ No GO categories found")
            return None
            
        # Get top terms per category
        df = df[df[pval_col] < 0.05]
        df_filtered = df.groupby('source').apply(lambda g: g.nsmallest(top_n, pval_col)).reset_index(drop=True)
        df_filtered['-log10(p)'] = -np.log10(df_filtered[pval_col])
        df_filtered['short_term'] = df_filtered[term_col].apply(lambda x: x[:40] + '...' if len(x) > 40 else x)
        
        # Create subplots
        categories = df_filtered['source'].unique()
        n_cats = len(categories)
        
        fig = make_subplots(
            rows=1, cols=n_cats,
            subplot_titles=[cat.replace('GO:', '') for cat in categories],
            shared_yaxes=False,
            horizontal_spacing=0.1
        )
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        for i, cat in enumerate(categories):
            cat_data = df_filtered[df_filtered['source'] == cat].sort_values('-log10(p)', ascending=True)
            
            fig.add_trace(
                go.Bar(
                    x=cat_data['-log10(p)'],
                    y=cat_data['short_term'],
                    orientation='h',
                    name=cat,
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f'<b>{cat}</b><br>' +
                                 'Term: %{y}<br>' +
                                 '-Log10(p): %{x:.2f}<br>' +
                                 '<extra></extra>',
                    showlegend=False
                ),
                row=1, col=i+1
            )
        
        fig.update_layout(
            title='🔬 GO Enrichment by Category',
            width=300 * n_cats,
            height=max(400, top_n * 25)
        )
        
        # Update x-axis labels
        for i in range(n_cats):
            fig.update_xaxes(title_text='-Log10(P-value)', row=1, col=i+1)
        
        return fig
        
    except Exception as e:
        st.error(f"❌ GO faceted plot failed: {e}")
        return None


def plot_pathway_network_plotly(path_df, top_n=15):
    """
    Network-style plot showing pathway relationships using Plotly
    """
    try:
        if len(path_df) == 0:
            st.warning("⚠️ No pathway terms to plot")
            return None
            
        # Prepare data
        df = path_df.copy()
        
        # Handle different column names
        pval_col = 'p_value' if 'p_value' in df.columns else 'p_val'
        term_col = 'term_name' if 'term_name' in df.columns else ('name' if 'name' in df.columns else 'description')
        
        # Filter and prepare
        df = df[df[pval_col] < 0.05].sort_values(pval_col).head(top_n)
        df['-log10(p)'] = -np.log10(df[pval_col])
        df['short_term'] = df[term_col].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
        
        # Create a circular layout for network effect
        n_terms = len(df)
        angles = np.linspace(0, 2*np.pi, n_terms, endpoint=False)
        
        # Calculate positions
        radius = 1
        x_pos = radius * np.cos(angles)
        y_pos = radius * np.sin(angles)
        
        # Create scatter plot with network-like appearance
        fig = go.Figure()
        
        # Add pathway nodes
        fig.add_trace(go.Scatter(
            x=x_pos,
            y=y_pos,
            mode='markers+text',
            marker=dict(
                size=df['-log10(p)'] * 5,  # Size based on significance
                color=df['-log10(p)'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='-Log10(P-value)'),
                line=dict(width=2, color='white')
            ),
            text=df['short_term'],
            textposition='middle center',
            textfont=dict(size=8, color='white'),
            hovertemplate='<b>%{text}</b><br>' +
                         'P-value: %{customdata[0]:.2e}<br>' +
                         'Source: %{customdata[1]}<br>' +
                         '<extra></extra>',
            customdata=np.column_stack((df[pval_col], df['source'] if 'source' in df.columns else ['Unknown'] * len(df))),
            name='Pathways'
        ))
        
        # Add connecting lines for visual effect
        for i in range(n_terms):
            for j in range(i+1, min(i+3, n_terms)):  # Connect to next 2 pathways
                fig.add_trace(go.Scatter(
                    x=[x_pos[i], x_pos[j]],
                    y=[y_pos[i], y_pos[j]],
                    mode='lines',
                    line=dict(color='lightgray', width=1),
                    showlegend=False,
                    hoverinfo='skip'
                ))
        
        fig.update_layout(
            title='🕸️ Pathway Network Visualization',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            width=800,
            height=800,
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Pathway network plot failed: {e}")
        return None


def plot_enrichment_comparison_plotly(go_df, path_df):
    """
    Comparison plot between GO and pathway enrichment
    """
    try:
        # Prepare GO data
        go_data = []
        if len(go_df) > 0:
            pval_col = 'p_value' if 'p_value' in go_df.columns else 'p_val'
            go_sig = go_df[go_df[pval_col] < 0.05] if pval_col in go_df.columns else go_df
            
            if 'source' in go_df.columns:
                go_counts = go_sig['source'].value_counts()
                for source, count in go_counts.items():
                    go_data.append({'category': source, 'count': count, 'type': 'GO Terms'})
        
        # Prepare pathway data
        path_data = []
        if len(path_df) > 0:
            pval_col = 'p_value' if 'p_value' in path_df.columns else 'p_val'
            path_sig = path_df[path_df[pval_col] < 0.05] if pval_col in path_df.columns else path_df
            
            if 'source' in path_df.columns:
                path_counts = path_sig['source'].value_counts()
                for source, count in path_counts.items():
                    path_data.append({'category': source, 'count': count, 'type': 'Pathways'})
        
        # Combine data
        all_data = go_data + path_data
        
        if not all_data:
            st.warning("⚠️ No enrichment data to compare")
            return None
            
        df = pd.DataFrame(all_data)
        
        # Create grouped bar chart
        fig = px.bar(
            df,
            x='category',
            y='count',
            color='type',
            title='📊 Enrichment Analysis Comparison',
            labels={
                'category': 'Category',
                'count': 'Number of Significant Terms',
                'type': 'Analysis Type'
            },
            color_discrete_map={
                'GO Terms': '#FF6B6B',
                'Pathways': '#4ECDC4'
            }
        )
        
        fig.update_layout(
            width=700,
            height=400,
            xaxis_tickangle=45
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Enrichment comparison plot failed: {e}")
        return None


def plot_enrichment_sunburst_plotly(go_df, path_df):
    """
    Sunburst plot showing hierarchical view of enrichment results
    """
    try:
        # Prepare data for sunburst
        sunburst_data = []
        
        # Add GO data
        if len(go_df) > 0:
            pval_col = 'p_value' if 'p_value' in go_df.columns else 'p_val'
            term_col = 'term_name' if 'term_name' in go_df.columns else ('name' if 'name' in go_df.columns else 'description')
            
            go_sig = go_df[go_df[pval_col] < 0.05] if pval_col in go_df.columns else go_df
            
            if 'source' in go_sig.columns:
                for _, row in go_sig.head(20).iterrows():  # Limit for readability
                    sunburst_data.append({
                        'ids': f"GO-{row['source']}-{row[term_col][:30]}",
                        'labels': row[term_col][:30] + ('...' if len(row[term_col]) > 30 else ''),
                        'parents': f"GO-{row['source']}",
                        'values': -np.log10(row[pval_col])
                    })
                
                # Add GO category parents
                for source in go_sig['source'].unique():
                    sunburst_data.append({
                        'ids': f"GO-{source}",
                        'labels': source,
                        'parents': 'GO Terms',
                        'values': 0
                    })
        
        # Add pathway data
        if len(path_df) > 0:
            pval_col = 'p_value' if 'p_value' in path_df.columns else 'p_val'
            term_col = 'term_name' if 'term_name' in path_df.columns else ('name' if 'name' in path_df.columns else 'description')
            
            path_sig = path_df[path_df[pval_col] < 0.05] if pval_col in path_df.columns else path_df
            
            if 'source' in path_sig.columns:
                for _, row in path_sig.head(20).iterrows():  # Limit for readability
                    sunburst_data.append({
                        'ids': f"PATH-{row['source']}-{row[term_col][:30]}",
                        'labels': row[term_col][:30] + ('...' if len(row[term_col]) > 30 else ''),
                        'parents': f"PATH-{row['source']}",
                        'values': -np.log10(row[pval_col])
                    })
                
                # Add pathway category parents
                for source in path_sig['source'].unique():
                    sunburst_data.append({
                        'ids': f"PATH-{source}",
                        'labels': source,
                        'parents': 'Pathways',
                        'values': 0
                    })
        
        # Add root categories
        sunburst_data.extend([
            {'ids': 'GO Terms', 'labels': 'GO Terms', 'parents': '', 'values': 0},
            {'ids': 'Pathways', 'labels': 'Pathways', 'parents': '', 'values': 0}
        ])
        
        if not sunburst_data:
            st.warning("⚠️ No data for sunburst plot")
            return None
            
        df = pd.DataFrame(sunburst_data)
        
        # Create sunburst plot
        fig = go.Figure(go.Sunburst(
            ids=df['ids'],
            labels=df['labels'],
            parents=df['parents'],
            values=df['values'],
            branchvalues="total",
            hovertemplate='<b>%{label}</b><br>Value: %{value:.2f}<extra></extra>',
            maxdepth=3
        ))
        
        fig.update_layout(
            title='☀️ Enrichment Analysis Sunburst',
            width=600,
            height=600
        )
        
        return fig
        
    except Exception as e:
        st.error(f"❌ Sunburst plot failed: {e}")
        return None