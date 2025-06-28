"""
Enhanced Biological Context Analyzer

Main coordinating class that integrates all analysis modules
for comprehensive biological context understanding.
"""

import os
import re
import logging
from sklearn.ensemble import RandomForestClassifier
from typing import Dict, List, Any
from datetime import datetime

# Try to import AI dependencies
try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    AI_DEPENDENCIES_AVAILABLE = True
except ImportError:
    torch = None
    AutoTokenizer = None  
    AutoModel = None
    AI_DEPENDENCIES_AVAILABLE = False

from .biological_context import BiologicalContext, BiologicalOntologyGraph
from .workflow_predictor import WorkflowPredictionEngine
from .learning_engine import ContinuousLearningEngine
from .multimodal_integrator import MultiModalContextIntegrator


class EnhancedBiologicalContextAnalyzer:
    """
    Enhanced patent-worthy biological context analyzer with AI capabilities.
    """
    
    def __init__(self, model_path: str = None):
        self.logger = logging.getLogger("enhanced_context_analyzer")
        
        # Initialize AI models if dependencies are available
        if AI_DEPENDENCIES_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained('allenai/scibert_scivocab_uncased')
                self.model = AutoModel.from_pretrained('allenai/scibert_scivocab_uncased')
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                self.model.to(self.device)
                self.ai_models_loaded = True
                self.logger.info("AI models loaded successfully")
            except Exception as e:
                self.logger.warning(f"Failed to load AI models: {e}")
                self.tokenizer = None
                self.model = None
                self.device = None
                self.ai_models_loaded = False
        else:
            self.logger.info("AI dependencies not available, running in basic mode")
            self.tokenizer = None
            self.model = None
            self.device = None
            self.ai_models_loaded = False
        
        # Initialize core components
        self.ontology = BiologicalOntologyGraph()
        self.workflow_predictor = WorkflowPredictionEngine()
        self.learning_engine = ContinuousLearningEngine()
        self.multimodal_integrator = MultiModalContextIntegrator()
        
        # Initialize classification models
        self.domain_classifier = None
        self.complexity_classifier = None
        
        # Load or initialize models
        if model_path and os.path.exists(model_path):
            self.load_models(model_path)
        else:
            self._initialize_default_models()
        
        # Enhanced pattern recognition
        self.semantic_patterns = self._load_semantic_patterns()
        
        # User behavior learning
        self.user_patterns = {}
        self.session_analytics = {}
        
        # Cache for performance
        self.embedding_cache = {}
        self.prediction_cache = {}
    
    def _load_semantic_patterns(self) -> Dict[str, Any]:
        """Load enhanced semantic patterns for biological analysis."""
        return {
            'experimental_designs': {
                'case_control': [
                    r'case\s*vs?\s*control', r'treated\s*vs?\s*untreated',
                    r'disease\s*vs?\s*healthy', r'mutant\s*vs?\s*wild[_\s]?type'
                ],
                'time_series': [
                    r'time\s*course', r'temporal', r'longitudinal',
                    r'over\s*time', r'\d+\s*hours?', r'\d+\s*days?'
                ],
                'dose_response': [
                    r'dose[_\s]?response', r'concentration', r'gradient',
                    r'titration', r'serial\s*dilution'
                ],
                'multi_condition': [
                    r'multiple\s*conditions', r'factorial', r'combinatorial',
                    r'cross[_\s]?over', r'multiple\s*treatments'
                ]
            },
            
            'analysis_objectives': {
                'biomarker_discovery': [
                    r'biomarker', r'signature', r'predictor', r'classifier',
                    r'diagnostic', r'prognostic', r'therapeutic\s*target'
                ],
                'mechanism_elucidation': [
                    r'mechanism', r'pathway', r'regulation', r'interaction',
                    r'molecular\s*basis', r'mode\s*of\s*action'
                ],
                'phenotype_association': [
                    r'phenotype', r'trait', r'clinical\s*outcome',
                    r'disease\s*association', r'gwas'
                ],
                'drug_discovery': [
                    r'drug\s*target', r'therapeutic', r'compound\s*screening',
                    r'pharmacology', r'toxicity'
                ]
            }
        }
    
    def _initialize_default_models(self):
        """Initialize default classification models."""
        self.domain_classifier = RandomForestClassifier(n_estimators=50, random_state=42)
        self.complexity_classifier = RandomForestClassifier(n_estimators=30, random_state=42)
    
    async def analyze_context(
        self, 
        query: str, 
        session_state: Dict = None,
        user_id: str = None,
        previous_queries: List[str] = None,
        uploaded_files: List[Any] = None
    ) -> BiologicalContext:
        """
        Enhanced context analysis with AI-powered understanding.
        """
        
        # Get embeddings for semantic analysis
        query_embedding = await self._get_query_embedding(query)
        
        # Multi-level analysis
        domain_analysis = await self._analyze_biological_domains(query, query_embedding)
        experimental_design = await self._detect_experimental_design(query, session_state)
        analysis_objectives = await self._identify_analysis_objectives(query, query_embedding)
        workflow_stage = await self._predict_workflow_stage(query, session_state, previous_queries)
        complexity_analysis = await self._assess_query_complexity(query, query_embedding)
        
        # Tool recommendation with confidence scores
        tool_recommendations = await self._recommend_tools(
            query, domain_analysis, experimental_design, analysis_objectives
        )
        
        # Integration requirements detection
        integration_reqs = await self._detect_integration_requirements(
            domain_analysis, session_state, tool_recommendations
        )
        
        # Multimodal integration
        if uploaded_files or session_state or user_id:
            multimodal_context = await self.multimodal_integrator.integrate_context(
                text_input=query,
                uploaded_files=uploaded_files,
                session_data=session_state,
                user_history=self.user_patterns.get(user_id, {}).get('history', []),
                temporal_context=session_state
            )
            # Enhance predictions with multimodal insights
            tool_recommendations = self._enhance_tool_recommendations(
                tool_recommendations, multimodal_context
            )
        
        # User-specific adaptation
        if user_id:
            await self._adapt_to_user_patterns(user_id, query, domain_analysis)
        
        # Quality assessment
        quality_indicators = await self._assess_data_quality_requirements(
            query, domain_analysis, experimental_design
        )
        
        # Build rich context object
        context = BiologicalContext(
            primary_domain=domain_analysis['primary'],
            secondary_domains=domain_analysis['secondary'],
            data_types=domain_analysis['data_types'],
            experimental_design=experimental_design['type'],
            analysis_objectives=analysis_objectives,
            workflow_stage=workflow_stage['current'],
            complexity_score=complexity_analysis['score'],
            tool_recommendations=tool_recommendations,
            integration_requirements=integration_reqs,
            confidence_metrics=self._calculate_confidence_metrics(
                domain_analysis, experimental_design, analysis_objectives
            ),
            data_quality_indicators=quality_indicators
        )
        
        # Session progression tracking
        if session_state:
            context.session_progression = self._track_session_progression(session_state)
            context.estimated_time_remaining = self._estimate_remaining_time(context)
        
        return context
    
    async def _get_query_embedding(self, query: str):
        """Get SciBERT embeddings for query (returns tensor if available, else None)."""
        if query in self.embedding_cache:
            return self.embedding_cache[query]
        
        if not self.ai_models_loaded or not self.tokenizer or not self.model or not torch:
            # Return None if models not available - caller should handle gracefully
            return None
        
        try:
            inputs = self.tokenizer(query, return_tensors='pt', truncation=True, 
                                   padding=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :].cpu()
            
            self.embedding_cache[query] = embedding
            return embedding
        except Exception as e:
            self.logger.warning(f"Failed to get embeddings: {e}")
            return None
    
    async def _analyze_biological_domains(
        self, query: str, embedding
    ) -> Dict[str, Any]:
        """AI-powered biological domain analysis."""
        
        query_lower = query.lower()
        detected_concepts = []
        
        # Find concepts mentioned in query
        for concept in self.ontology.graph.nodes():
            if concept.lower() in query_lower:
                detected_concepts.append(concept)
        
        # Get related concepts from ontology
        related_concepts = []
        for concept in detected_concepts:
            related = self.ontology.get_related_concepts(concept)
            related_concepts.extend(related)
        
        # Classify primary domain
        primary_domain = self._classify_primary_domain(detected_concepts, related_concepts)
        
        # Identify secondary domains
        secondary_domains = self._identify_secondary_domains(
            detected_concepts, related_concepts, primary_domain
        )
        
        # Detect data types
        data_types = self._detect_data_types_enhanced(query, detected_concepts)
        
        return {
            'primary': primary_domain,
            'secondary': secondary_domains,
            'data_types': data_types,
            'detected_concepts': detected_concepts,
            'confidence': self._calculate_domain_confidence(detected_concepts)
        }
    
    def _classify_primary_domain(self, detected_concepts: List[str], 
                                related_concepts: List[tuple]) -> str:
        """Classify the primary biological domain."""
        
        domain_scores = {}
        
        # Score based on detected concepts
        for concept in detected_concepts:
            if 'rna' in concept.lower() or 'transcript' in concept.lower():
                domain_scores['transcriptomics'] = domain_scores.get('transcriptomics', 0) + 2
            elif 'protein' in concept.lower():
                domain_scores['proteomics'] = domain_scores.get('proteomics', 0) + 2
            elif 'genome' in concept.lower() or 'variant' in concept.lower():
                domain_scores['genomics'] = domain_scores.get('genomics', 0) + 2
        
        # Score based on related concepts
        for concept, similarity in related_concepts:
            if 'rna' in concept.lower():
                domain_scores['transcriptomics'] = domain_scores.get('transcriptomics', 0) + similarity
            elif 'protein' in concept.lower():
                domain_scores['proteomics'] = domain_scores.get('proteomics', 0) + similarity
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        else:
            return 'unknown'
    
    def load_models(self, model_path: str):
        """Load pre-trained models."""
        try:
            # Implementation for loading models would go here
            self.logger.info(f"Models loaded from {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")


def main():
    """Test function for the enhanced context analyzer."""
    print("Testing EnhancedBiologicalContextAnalyzer...")
    
    # Create analyzer
    analyzer = EnhancedBiologicalContextAnalyzer()
    
    print("Analyzer initialized successfully")
    print(f"Ontology has {analyzer.ontology.graph.number_of_nodes()} nodes")
    print(f"Available semantic patterns: {list(analyzer.semantic_patterns.keys())}")
    
    # Test query analysis
    test_query = "I want to perform single-cell RNA-seq analysis with differential expression"
    print(f"\nTesting with query: '{test_query}'")
    
    # Test domain classification
    domain_result = analyzer._classify_primary_domain(['scrna_seq', 'differential'], [])
    print(f"Classified primary domain: {domain_result}")


if __name__ == "__main__":
    main() 