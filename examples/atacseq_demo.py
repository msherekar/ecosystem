#!/usr/bin/env python3
"""
ATAC-seq MCP Server Demo

Demonstrates how the improved session tracking system automatically
handles new analysis types with minimal configuration.
"""

import asyncio
import pandas as pd
import numpy as np
import streamlit as st
from src.mcp.servers.atacseq_server import ATACSeqMCPServer


async def demo_atacseq_tracking():
    """Demonstrate automatic variable tracking for ATAC-seq analysis"""
    
    print("🧬 ATAC-seq MCP Server Demo")
    print("=" * 50)
    
    # Initialize the server
    server = ATACSeqMCPServer()
    await server.initialize()
    
    print(f"✅ Server initialized: {server.name} v{server.version}")
    print(f"📊 Tracking {len(server.tracked_variables)} explicit variables")
    print(f"🔍 Using {len(server.variable_patterns)} regex patterns")
    print(f"🤖 Auto-discovery: {server.auto_discover_variables}")
    
    # Simulate some ATAC-seq data being loaded
    print("\n📁 Simulating ATAC-seq data upload...")
    
    # Create mock data that would be stored in session state
    mock_session_state = {
        # Core ATAC-seq data (will be tracked by explicit variables)
        'atacseq_peaks_df': pd.DataFrame({
            'chr': ['chr1', 'chr2', 'chr3'],
            'start': [1000, 2000, 3000],
            'end': [1500, 2500, 3500],
            'peak_score': [10.5, 15.2, 8.7]
        }),
        'atacseq_metadata_df': pd.DataFrame({
            'sample_id': ['sample1', 'sample2', 'sample3'],
            'condition': ['control', 'treatment', 'control']
        }),
        
        # Analysis results (will be tracked by patterns)
        'differential_peaks': pd.DataFrame({
            'peak_id': ['peak1', 'peak2'],
            'log2FoldChange': [2.1, -1.8],
            'padj': [0.01, 0.03]
        }),
        'motif_enrichment_results': pd.DataFrame({
            'motif_id': ['CTCF', 'AP1'],
            'enrichment_score': [5.2, 3.8]
        }),
        
        # QC metrics (will be tracked by patterns)
        'tss_enrichment_scores': 8.5,
        'nucleosome_signal': 0.15,
        
        # Analysis flags (will be auto-discovered)
        'qc_metrics_calculated': True,
        'peaks_called': True,
        
        # Variables that match patterns
        'custom_peaks': pd.DataFrame({'data': [1, 2, 3]}),  # matches .*_peaks$
        'tss_profile': [1, 2, 3, 4, 5],  # matches tss_.*
        'chromvar_deviation_scores': np.random.normal(0, 1, (10, 50)),  # matches chromvar_.*
        
        # Variables that should be auto-discovered
        'large_accessibility_matrix': pd.DataFrame(np.random.randn(1000, 100)),  # Large DataFrame
        'analysis_complete': True,  # Boolean flag
        'results_summary': {'peaks': 50000, 'samples': 20},  # Non-empty dict
        
        # Variables that should be ignored
        '_internal_streamlit_var': 'ignore_me',
        'FormSubmitter:button': 'ignore_me',
        'small_temp_var': [1, 2]  # Small, not important
    }
    
    # Temporarily replace st.session_state for demo
    original_session_state = getattr(st, 'session_state', {})
    st.session_state = type('MockSessionState', (), mock_session_state)()
    st.session_state.keys = lambda: mock_session_state.keys()
    st.session_state.__contains__ = lambda self, key: key in mock_session_state
    st.session_state.__getitem__ = lambda self, key: mock_session_state[key]
    
    try:
        # Get session state summary
        print("\n📋 Getting session state summary...")
        summary = server._get_session_state_summary()
        
        print(f"\n🎯 Tracked {len(summary)} variables:")
        print("-" * 30)
        
        for var_name, var_summary in summary.items():
            print(f"📌 {var_name}:")
            if isinstance(var_summary, dict):
                for key, value in var_summary.items():
                    if key == 'columns' and isinstance(value, list) and len(value) > 3:
                        print(f"   {key}: {value[:3]}... ({len(value)} total)")
                    elif key == 'keys' and isinstance(value, list) and len(value) > 3:
                        print(f"   {key}: {value[:3]}... ({len(value)} total)")
                    else:
                        print(f"   {key}: {value}")
            else:
                print(f"   value: {var_summary}")
            print()
        
        # Show what was captured by each method
        print("\n🔍 Variable Discovery Analysis:")
        print("-" * 35)
        
        # Explicit tracking
        explicit_vars = [v for v in summary.keys() if v in server.tracked_variables]
        print(f"📝 Explicitly tracked: {len(explicit_vars)}")
        for var in explicit_vars[:5]:  # Show first 5
            print(f"   • {var}")
        if len(explicit_vars) > 5:
            print(f"   ... and {len(explicit_vars) - 5} more")
        
        # Pattern matching
        import re
        pattern_vars = []
        for var in summary.keys():
            if var not in server.tracked_variables:
                for pattern in server.variable_patterns:
                    if re.match(pattern, var):
                        pattern_vars.append(var)
                        break
        
        print(f"\n🎯 Pattern matched: {len(pattern_vars)}")
        for var in pattern_vars:
            matching_patterns = [p for p in server.variable_patterns if re.match(p, var)]
            print(f"   • {var} (matches: {matching_patterns[0]})")
        
        # Auto-discovered
        auto_vars = server._auto_discover_important_variables()
        auto_tracked = [v for v in auto_vars if v in summary.keys() and 
                       v not in server.tracked_variables and v not in pattern_vars]
        
        print(f"\n🤖 Auto-discovered: {len(auto_tracked)}")
        for var in auto_tracked:
            var_info = mock_session_state[var]
            if hasattr(var_info, 'shape'):
                print(f"   • {var} (shape: {var_info.shape})")
            elif isinstance(var_info, bool):
                print(f"   • {var} (boolean flag)")
            elif isinstance(var_info, dict):
                print(f"   • {var} (dict with {len(var_info)} keys)")
            else:
                print(f"   • {var} (type: {type(var_info).__name__})")
        
        # Get analysis context
        print("\n🧠 Analysis Context:")
        print("-" * 20)
        context = server.get_analysis_context()
        
        print(f"Server: {context['server']}")
        print(f"Analysis type: {context.get('analysis_type', 'unknown')}")
        print(f"Data available: {context.get('data_uploaded', False)}")
        
        if 'pipeline_status' in context:
            status = context['pipeline_status']
            print(f"Pipeline status: {len(status)} steps completed")
            for step, completed in status.items():
                print(f"   • {step}: {'✅' if completed else '❌'}")
        
        # Get suggested actions
        print("\n💡 Suggested Actions:")
        print("-" * 20)
        suggestions = server.get_suggested_actions()
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
        
        print("\n🎉 Demo completed successfully!")
        print("\n" + "=" * 50)
        print("KEY BENEFITS OF THE NEW SYSTEM:")
        print("✅ Automatic discovery of important variables")
        print("✅ Pattern-based tracking for flexibility") 
        print("✅ Rich variable summaries with metadata")
        print("✅ Zero configuration needed for basic usage")
        print("✅ Extensible for domain-specific needs")
        print("✅ Backward compatible with existing code")
        
    finally:
        # Restore original session state
        if hasattr(st, 'session_state'):
            st.session_state = original_session_state


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_atacseq_tracking()) 