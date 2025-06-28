"""
Biological Context Analyzer
Extracts biological domain context from user queries and session state.
"""

from typing import Dict, List, Any, Set
import streamlit as st
import logging


class BiologicalContextAnalyzer:
    """
    PATENT-WORTHY: Biological domain-specific context analysis
    
    Analyzes user query and session state to predict required tool categories
    using domain-specific biological knowledge patterns.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("context_analyzer")
        
        # Domain classification patterns
        self.domain_patterns = {
            "scrnaseq": {
                "keywords": ["scrna", "single cell", "cell type", "cluster", "umap", "tsne"],
                "priority_tools": ["clustering", "cell_annotation", "dimensionality_reduction"],
                "workflow_stages": ["qc", "filtering", "normalization", "clustering", "visualization"]
            },
            "rnaseq": {
                "keywords": ["rna-seq", "rnaseq", "differential", "deseq", "bulk rna"],
                "priority_tools": ["differential_expression", "pathway_analysis", "volcano_plot"],
                "workflow_stages": ["preprocessing", "differential_analysis", "enrichment"]
            },
            "proteomics": {
                "keywords": ["protein", "proteome", "mass spec", "peptide"],
                "priority_tools": ["protein_quantification", "pathway_mapping"],
                "workflow_stages": ["protein_id", "quantification", "pathway_analysis"]
            },
            "genomics": {
                "keywords": ["genome", "variant", "snp", "mutation", "annotation"],
                "priority_tools": ["variant_calling", "annotation", "population_analysis"],
                "workflow_stages": ["alignment", "variant_calling", "annotation"]
            }
        }
        
        # Analysis intent patterns
        self.intent_patterns = {
            "clustering": ["cluster", "group", "classify", "cell type"],
            "differential_analysis": ["differential", "compare", "vs", "between"],
            "pathway_analysis": ["pathway", "enrichment", "go", "functional"],
            "visualization": ["plot", "visualize", "chart", "graph", "show"],
            "quality_control": ["qc", "quality", "filter", "clean"],
            "exploration": ["explore", "overview", "summary", "describe"]
        }
        
        # Workflow stage indicators
        self.workflow_indicators = {
            "data_upload": ["upload", "load", "import", "file", "data"],
            "preprocessing": ["filter", "normalize", "clean", "qc", "quality"],
            "analysis": ["analyze", "cluster", "differential", "pathway"],
            "visualization": ["plot", "chart", "graph", "heatmap", "visualize"],
            "interpretation": ["interpret", "meaning", "significance", "biological"]
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            "simple": ["what", "show", "display", "list"],
            "medium": ["analyze", "compare", "cluster", "plot"],
            "complex": ["integrate", "multi-omics", "pathway", "network", "comprehensive"]
        }
    
    async def analyze_context(self, query: str, session_state: Dict = None) -> Dict[str, Any]:
        """
        Analyze biological context from query and session state.
        
        Args:
            query: User's query string
            session_state: Current session state dict
            
        Returns:
            Context analysis results
        """
        
        if session_state is None:
            session_state = getattr(st, 'session_state', {})
        
        context = {
            "data_types": self._detect_data_types(query, session_state),
            "analysis_intent": self._classify_analysis_intent(query),
            "workflow_stage": self._determine_workflow_stage(session_state, query),
            "complexity_level": self._assess_complexity(query),
            "required_domains": [],
            "priority_tools": [],
            "confidence": 0.0
        }
        
        # Biological domain classification
        detected_domains = self._classify_biological_domains(query)
        context["required_domains"] = detected_domains
        
        # Collect priority tools from detected domains
        for domain in detected_domains:
            if domain in self.domain_patterns:
                context["priority_tools"].extend(
                    self.domain_patterns[domain]["priority_tools"]
                )
        
        # Remove duplicates
        context["priority_tools"] = list(set(context["priority_tools"]))
        
        # Multi-omics detection
        if len(detected_domains) > 1:
            context["analysis_type"] = "multi_omics"
            context["integration_needed"] = True
        else:
            context["analysis_type"] = "single_omics"
            context["integration_needed"] = False
        
        # Calculate confidence
        context["confidence"] = self._calculate_confidence(context, query, session_state)
        
        self.logger.info(f"Context analyzed: {len(detected_domains)} domains, {context['analysis_intent']} intent")
        
        return context
    
    def _detect_data_types(self, query: str, session_state: Dict) -> List[str]:
        """Detect data types from query and session state"""
        data_types = []
        
        # Check session state for uploaded data
        if "anndata" in session_state:
            data_types.append("single_cell")
        if "deseq_results" in session_state:
            data_types.append("bulk_rna")
        if "proteomics_data" in session_state:
            data_types.append("proteomics")
        if "genomics_data" in session_state:
            data_types.append("genomics")
            
        # Check query text for data type mentions
        query_lower = query.lower()
        if any(term in query_lower for term in ['fastq', 'bam', 'counts', 'expression']):
            data_types.append("sequencing")
        if any(term in query_lower for term in ['mass spec', 'protein', 'peptide']):
            data_types.append("proteomics")
        if any(term in query_lower for term in ['variant', 'snp', 'genome']):
            data_types.append("genomics")
            
        return list(set(data_types))
    
    def _classify_biological_domains(self, query: str) -> List[str]:
        """Classify biological domains mentioned in the query"""
        detected_domains = []
        query_lower = query.lower()
        
        for domain, patterns in self.domain_patterns.items():
            if any(keyword in query_lower for keyword in patterns["keywords"]):
                detected_domains.append(domain)
        
        return detected_domains
    
    def _classify_analysis_intent(self, query: str) -> str:
        """Classify the analysis intent from query"""
        query_lower = query.lower()
        
        # Check each intent pattern
        for intent, keywords in self.intent_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        # Default intent
        return "exploration"
    
    def _determine_workflow_stage(self, session_state: Dict, query: str = "") -> str:
        """Determine current workflow stage from session state and query"""
        
        # Check session state first
        if not any(key.endswith('_data') for key in session_state.keys()):
            return "data_upload"
        elif session_state.get("qc_done") and not session_state.get("analysis_done"):
            return "analysis"
        elif session_state.get("analysis_done") and not session_state.get("visualization_done"):
            return "visualization"
        elif session_state.get("visualization_done"):
            return "interpretation"
        
        # Check query for workflow stage indicators
        query_lower = query.lower()
        for stage, indicators in self.workflow_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return stage
        
        # Default to preprocessing if data exists
        if session_state:
            return "preprocessing"
        else:
            return "data_upload"
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity level"""
        query_lower = query.lower()
        
        # Check complexity indicators
        for level, indicators in self.complexity_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return level
        
        # Default complexity
        return "medium"
    
    def _calculate_confidence(self, context: Dict, query: str, session_state: Dict) -> float:
        """Calculate confidence in the context analysis"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for domain matches
        if context["required_domains"]:
            confidence += 0.2 * len(context["required_domains"])
        
        # Boost confidence for clear intent
        if context["analysis_intent"] != "exploration":
            confidence += 0.2
        
        # Boost confidence for session state consistency
        if session_state and context["workflow_stage"] != "data_upload":
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """Get detailed information about a specific domain"""
        return self.domain_patterns.get(domain, {})
    
    def get_supported_domains(self) -> List[str]:
        """Get list of all supported biological domains"""
        return list(self.domain_patterns.keys())
    
    def add_domain_pattern(self, domain: str, keywords: List[str], 
                          priority_tools: List[str], workflow_stages: List[str]):
        """Add a new domain pattern (for extensibility)"""
        self.domain_patterns[domain] = {
            "keywords": keywords,
            "priority_tools": priority_tools,
            "workflow_stages": workflow_stages
        }
        self.logger.info(f"Added new domain pattern: {domain}")
    
    def update_intent_patterns(self, intent: str, keywords: List[str]):
        """Update or add intent patterns"""
        self.intent_patterns[intent] = keywords
        self.logger.info(f"Updated intent pattern: {intent}")


if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    """Test the context analyzer individually"""
    import asyncio
    import sys
    
    async def run_static_tests():
        """Run the original static test suite"""
        print("🧪 Testing BiologicalContextAnalyzer...")
        
        # Create analyzer
        analyzer = BiologicalContextAnalyzer()
        
        # Test supported domains
        domains = analyzer.get_supported_domains()
        print(f"✅ Supported domains: {domains}")
        
        # Test domain info
        scrna_info = analyzer.get_domain_info("scrnaseq")
        print(f"✅ scRNA-seq info: {len(scrna_info['keywords'])} keywords, {len(scrna_info['priority_tools'])} tools")
        
        # Test different query types
        test_queries = [
            {
                "query": "I want to cluster my scRNA-seq data",
                "session": {"anndata": "mock_data"},
                "expected_domains": ["scrnaseq"],
                "expected_intent": "clustering"
            },
            {
                "query": "perform differential expression analysis on RNA-seq",
                "session": {"deseq_results": "mock_results"},
                "expected_domains": ["rnaseq"],
                "expected_intent": "differential_analysis"
            },
            {
                "query": "analyze protein mass spec data",
                "session": {"proteomics_data": "mock_data"},
                "expected_domains": ["proteomics"],
                "expected_intent": "exploration"
            },
            {
                "query": "comprehensive multi-omics pathway analysis",
                "session": {"anndata": "data1", "proteomics_data": "data2"},
                "expected_domains": ["proteomics"],  # Only proteomics keyword present
                "expected_intent": "pathway_analysis"
            },
            {
                "query": "show me a volcano plot",
                "session": {},
                "expected_domains": [],
                "expected_intent": "visualization"
            }
        ]
        
        print("\n🔍 Testing context analysis:")
        for i, test_case in enumerate(test_queries, 1):
            context = await analyzer.analyze_context(
                query=test_case["query"],
                session_state=test_case["session"]
            )
            
            print(f"\n   Test {i}: '{test_case['query'][:40]}...'")
            print(f"     Detected domains: {context['required_domains']}")
            print(f"     Analysis intent: {context['analysis_intent']}")
            print(f"     Workflow stage: {context['workflow_stage']}")
            print(f"     Complexity: {context['complexity_level']}")
            print(f"     Priority tools: {context['priority_tools'][:3]}...")  # Show first 3
            print(f"     Confidence: {context['confidence']:.2f}")
            print(f"     Multi-omics: {context.get('integration_needed', False)}")
        
        # Test extensibility
        print("\n🔧 Testing extensibility:")
        
        # Add new domain
        analyzer.add_domain_pattern(
            domain="metabolomics",
            keywords=["metabolite", "metabolomics", "mass spec", "nmr"],
            priority_tools=["metabolite_analysis", "pathway_mapping"],
            workflow_stages=["preprocessing", "identification", "pathway_analysis"]
        )
        
        # Test new domain
        context = await analyzer.analyze_context(
            query="analyze metabolite data",
            session_state={}
        )
        print(f"✅ New domain test: {context['required_domains']}")
        
        # Update intent patterns
        analyzer.update_intent_patterns(
            intent="biomarker_discovery",
            keywords=["biomarker", "signature", "discovery", "predictive"]
        )
        
        context = await analyzer.analyze_context(
            query="find biomarker signatures",
            session_state={}
        )
        print(f"✅ New intent test: {context['analysis_intent']}")
        
        # Test workflow stage detection
        print("\n📊 Testing workflow stage detection:")
        
        workflow_tests = [
            ({"anndata": "data"}, "preprocessing"),
            ({"qc_done": True}, "analysis"),
            ({"analysis_done": True}, "visualization"),
            ({"visualization_done": True}, "interpretation"),
            ({}, "data_upload")
        ]
        
        for session, expected_stage in workflow_tests:
            context = await analyzer.analyze_context(
                query="test query",
                session_state=session
            )
            actual_stage = context['workflow_stage']
            print(f"   Session {session} → {actual_stage} (expected: {expected_stage})")
        
        # Test complexity assessment
        print("\n🎯 Testing complexity assessment:")
        
        complexity_tests = [
            ("what is RNA-seq?", "simple"),
            ("analyze my data", "medium"),
            ("comprehensive multi-omics integration", "complex")
        ]
        
        for query, expected_complexity in complexity_tests:
            context = await analyzer.analyze_context(query, {})
            actual_complexity = context['complexity_level']
            print(f"   '{query}' → {actual_complexity} (expected: {expected_complexity})")
        
        print("\n🎉 Static context analyzer tests completed!")
        return analyzer
    
    async def run_dynamic_tests(analyzer):
        """Run interactive dynamic testing"""
        print("\n" + "="*60)
        print("🚀 DYNAMIC CONTEXT ANALYZER TESTING")
        print("="*60)
        print("Type biological queries to see context predictions!")
        print("Commands:")
        print("  'quit' or 'exit' - Exit dynamic testing")
        print("  'help' - Show example queries")
        print("  'session:key=value' - Set session state (e.g., session:anndata=data)")
        print("  'clear' - Clear session state")
        print("-" * 60)
        
        # Initialize session state for dynamic testing
        dynamic_session = {}
        
        while True:
            try:
                # Get user input
                query = input("\n💬 Enter your query: ").strip()
                
                # Handle special commands
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Exiting dynamic testing...")
                    break
                
                elif query.lower() == 'help':
                    print("\n📚 Example queries to try:")
                    examples = [
                        "I want to cluster my single cell RNA-seq data",
                        "perform differential expression analysis",
                        "analyze protein mass spectrometry data",
                        "create a volcano plot for my RNA-seq results",
                        "find pathway enrichment in my proteomics data",
                        "quality control of my scRNA-seq dataset",
                        "compare gene expression between conditions",
                        "visualize my clustering results with UMAP",
                        "identify cell types in my single cell data",
                        "comprehensive multi-omics integration analysis"
                    ]
                    for i, example in enumerate(examples, 1):
                        print(f"   {i:2}. {example}")
                    continue
                
                elif query.lower() == 'clear':
                    dynamic_session.clear()
                    print("🧹 Session state cleared!")
                    continue
                
                elif query.startswith('session:'):
                    # Parse session state command
                    try:
                        session_part = query[8:]  # Remove 'session:'
                        if '=' in session_part:
                            key, value = session_part.split('=', 1)
                            dynamic_session[key.strip()] = value.strip()
                            print(f"✅ Set session['{key.strip()}'] = '{value.strip()}'")
                        else:
                            print("❌ Invalid session format. Use: session:key=value")
                    except Exception as e:
                        print(f"❌ Error setting session: {e}")
                    continue
                
                elif not query:
                    continue
                
                # Analyze the query
                print(f"\n🔍 Analyzing: '{query}'")
                print(f"📊 Session state: {dynamic_session if dynamic_session else 'Empty'}")
                
                context = await analyzer.analyze_context(
                    query=query,
                    session_state=dynamic_session
                )
                
                # Display results in a nice format
                print("\n" + "─" * 50)
                print("📋 CONTEXT ANALYSIS RESULTS")
                print("─" * 50)
                
                # Domain analysis
                domains = context['required_domains']
                if domains:
                    print(f"🧬 Biological Domains: {', '.join(domains)}")
                    
                    # Show domain-specific info
                    for domain in domains:
                        domain_info = analyzer.get_domain_info(domain)
                        if domain_info:
                            print(f"   └─ {domain}: {len(domain_info.get('keywords', []))} keywords, "
                                  f"{len(domain_info.get('priority_tools', []))} priority tools")
                else:
                    print("🧬 Biological Domains: None detected")
                
                # Analysis details
                print(f"🎯 Analysis Intent: {context['analysis_intent']}")
                print(f"📈 Workflow Stage: {context['workflow_stage']}")
                print(f"⚡ Complexity Level: {context['complexity_level']}")
                print(f"🔗 Multi-omics: {'Yes' if context.get('integration_needed', False) else 'No'}")
                print(f"📊 Confidence: {context['confidence']:.2%}")
                
                # Data types
                data_types = context.get('data_types', [])
                if data_types:
                    print(f"📁 Data Types: {', '.join(data_types)}")
                
                # Priority tools
                priority_tools = context.get('priority_tools', [])
                if priority_tools:
                    print(f"🛠️  Priority Tools: {', '.join(priority_tools[:5])}")
                    if len(priority_tools) > 5:
                        print(f"   └─ ... and {len(priority_tools) - 5} more")
                
                # Additional context info
                if context.get('analysis_type'):
                    print(f"🔬 Analysis Type: {context['analysis_type']}")
                
                print("─" * 50)
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Exiting dynamic testing...")
                break
            except Exception as e:
                print(f"❌ Error during analysis: {e}")
                print("Please try again with a different query.")
    
    async def main():
        """Main test runner with options"""
        print("🧬 BiologicalContextAnalyzer Test Suite")
        print("=" * 50)
        
        # Check command line arguments
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode == 'dynamic':
                print("🚀 Running DYNAMIC testing only...")
                analyzer = BiologicalContextAnalyzer()
                await run_dynamic_tests(analyzer)
                return
            elif mode == 'static':
                print("🧪 Running STATIC testing only...")
                await run_static_tests()
                return
        
        # Default: Run both
        print("🔄 Running BOTH static and dynamic tests...")
        
        # Run static tests first
        analyzer = await run_static_tests()
        
        # Ask user if they want to continue to dynamic testing
        print("\n" + "="*60)
        try:
            choice = input("🤔 Continue to dynamic testing? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '']:
                await run_dynamic_tests(analyzer)
            else:
                print("👋 Skipping dynamic testing. Done!")
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
    
    # Run the main test function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Testing interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Error running tests: {e}")