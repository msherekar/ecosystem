"""
Multi-Modal Context Integrator

This module integrates multiple data modalities for enhanced
biological context understanding.
"""

from typing import Dict, List, Any
from .file_analyzer import DataFileAnalyzer
from .temporal_analyzer import TemporalPatternAnalyzer


class MultiModalContextIntegrator:
    """Integrates multiple data modalities for enhanced context understanding."""
    
    def __init__(self):
        self.modality_analyzers = {
            'text': TextModalityAnalyzer(),
            'data_files': DataFileAnalyzer(),
            'session_state': SessionStateAnalyzer(),
            'user_behavior': UserBehaviorAnalyzer(),
            'temporal': TemporalPatternAnalyzer()
        }
        self.fusion_weights = {
            'text': 0.4,
            'data_files': 0.3,
            'session_state': 0.1,
            'user_behavior': 0.1,
            'temporal': 0.1
        }
    
    async def integrate_context(
        self,
        text_input: str,
        uploaded_files: List[Any] = None,
        session_data: Dict = None,
        user_history: List[Dict] = None,
        temporal_context: Dict = None
    ) -> Dict[str, Any]:
        """Integrate multiple modalities for comprehensive context."""
        
        modal_contexts = {}
        
        # Analyze each modality
        if text_input:
            modal_contexts['text'] = await self.modality_analyzers['text'].analyze(text_input)
        
        if uploaded_files:
            modal_contexts['data_files'] = await self.modality_analyzers['data_files'].analyze(uploaded_files)
        
        if session_data:
            modal_contexts['session_state'] = await self.modality_analyzers['session_state'].analyze(session_data)
        
        if user_history:
            modal_contexts['user_behavior'] = await self.modality_analyzers['user_behavior'].analyze(user_history)
        
        if temporal_context:
            modal_contexts['temporal'] = await self.modality_analyzers['temporal'].analyze(temporal_context)
        
        # Fuse modalities
        integrated_context = await self._fuse_modalities(modal_contexts)
        
        # Add cross-modal validation
        integrated_context['validation_score'] = self._cross_validate_modalities(modal_contexts)
        
        return integrated_context
    
    async def _fuse_modalities(self, modal_contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Fuse information from multiple modalities."""
        
        fused_context = {
            'confidence_score': 0.0,
            'primary_indicators': [],
            'supporting_evidence': {},
            'consistency_score': 0.0
        }
        
        # Weighted fusion of confidence scores
        total_weight = 0
        weighted_confidence = 0
        
        for modality, context in modal_contexts.items():
            if modality in self.fusion_weights:
                weight = self.fusion_weights[modality]
                confidence = self._extract_confidence(context)
                
                weighted_confidence += weight * confidence
                total_weight += weight
        
        if total_weight > 0:
            fused_context['confidence_score'] = weighted_confidence / total_weight
        
        # Extract primary indicators from each modality
        for modality, context in modal_contexts.items():
            indicators = self._extract_primary_indicators(modality, context)
            fused_context['primary_indicators'].extend(indicators)
        
        # Store supporting evidence
        fused_context['supporting_evidence'] = modal_contexts
        
        # Calculate consistency across modalities
        fused_context['consistency_score'] = self._calculate_consistency(modal_contexts)
        
        return fused_context
    
    def _extract_confidence(self, context: Any) -> float:
        """Extract confidence score from modal context."""
        if isinstance(context, dict):
            if 'confidence' in context:
                return context['confidence']
            elif 'accuracy' in context:
                return context['accuracy']
            elif 'score' in context:
                return context['score']
        
        return 0.5  # Default confidence
    
    def _extract_primary_indicators(self, modality: str, context: Any) -> List[str]:
        """Extract primary indicators from modal context."""
        indicators = []
        
        if modality == 'text' and isinstance(context, dict):
            indicators.extend(context.get('keywords', []))
            indicators.extend(context.get('entities', []))
        
        elif modality == 'data_files' and isinstance(context, dict):
            indicators.extend(context.get('file_types', []))
            indicators.extend(context.get('experiment_types', []))
        
        elif modality == 'temporal' and isinstance(context, dict):
            indicators.append(context.get('workflow_pattern', 'unknown'))
            indicators.append(context.get('session_stage', 'unknown'))
        
        return [ind for ind in indicators if ind and ind != 'unknown']
    
    def _calculate_consistency(self, modal_contexts: Dict[str, Any]) -> float:
        """Calculate consistency score across modalities."""
        if len(modal_contexts) < 2:
            return 1.0
        
        # Simple consistency check based on common indicators
        all_indicators = []
        for modality, context in modal_contexts.items():
            indicators = self._extract_primary_indicators(modality, context)
            all_indicators.extend(indicators)
        
        if not all_indicators:
            return 0.5
        
        # Calculate overlap between modalities
        unique_indicators = set(all_indicators)
        overlap_score = len(all_indicators) / len(unique_indicators) if unique_indicators else 0
        
        # Normalize to 0-1 range
        return min(overlap_score, 1.0)
    
    def _cross_validate_modalities(self, modal_contexts: Dict[str, Any]) -> float:
        """Cross-validate information across modalities."""
        
        validation_scores = []
        
        # Check text-file consistency
        if 'text' in modal_contexts and 'data_files' in modal_contexts:
            text_score = self._validate_text_file_consistency(
                modal_contexts['text'], modal_contexts['data_files']
            )
            validation_scores.append(text_score)
        
        # Check temporal-behavior consistency
        if 'temporal' in modal_contexts and 'user_behavior' in modal_contexts:
            temporal_score = self._validate_temporal_behavior_consistency(
                modal_contexts['temporal'], modal_contexts['user_behavior']
            )
            validation_scores.append(temporal_score)
        
        return sum(validation_scores) / len(validation_scores) if validation_scores else 0.5
    
    def _validate_text_file_consistency(self, text_context, file_context) -> float:
        """Validate consistency between text and file analysis."""
        
        # Simple validation: check if mentioned data types match file types
        text_mentions = set()
        if isinstance(text_context, dict):
            text_mentions.update(text_context.get('data_types', []))
            text_mentions.update(text_context.get('keywords', []))
        
        file_types = set()
        if isinstance(file_context, dict):
            file_types.update(file_context.get('file_types', []))
            file_types.update(file_context.get('experiment_types', []))
        
        if not text_mentions or not file_types:
            return 0.5
        
        # Calculate overlap
        overlap = len(text_mentions & file_types)
        total = len(text_mentions | file_types)
        
        return overlap / total if total > 0 else 0.5
    
    def _validate_temporal_behavior_consistency(self, temporal_context, behavior_context) -> float:
        """Validate consistency between temporal and behavior analysis."""
        
        # Placeholder for temporal-behavior consistency validation
        # In practice, this would check if behavior patterns match temporal patterns
        
        return 0.7  # Default consistency score


class TextModalityAnalyzer:
    """Analyzes text input for biological context."""
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text input for context clues."""
        
        text_lower = text.lower()
        
        # Extract keywords
        biological_keywords = [
            'gene', 'protein', 'cell', 'rna', 'dna', 'expression',
            'analysis', 'sequencing', 'differential', 'pathway'
        ]
        
        found_keywords = [kw for kw in biological_keywords if kw in text_lower]
        
        # Extract data type mentions
        data_types = []
        data_type_patterns = {
            'rnaseq': ['rna-seq', 'rnaseq', 'rna sequencing'],
            'scrna_seq': ['single cell', 'scrna', 'sc-rna'],
            'proteomics': ['protein', 'proteome', 'mass spec'],
            'genomics': ['genome', 'genomic', 'variant']
        }
        
        for dtype, patterns in data_type_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                data_types.append(dtype)
        
        return {
            'keywords': found_keywords,
            'data_types': data_types,
            'confidence': min(len(found_keywords) / 5.0, 1.0),
            'complexity': len(text.split()) / 50.0  # Normalized by typical query length
        }


class SessionStateAnalyzer:
    """Analyzes session state for context."""
    
    async def analyze(self, session_data: Dict) -> Dict[str, Any]:
        """Analyze session state for context clues."""
        
        return {
            'active_tools': session_data.get('active_tools', []),
            'data_loaded': bool(session_data.get('loaded_data')),
            'analysis_stage': session_data.get('current_stage', 'unknown'),
            'confidence': 0.8 if session_data else 0.2
        }


class UserBehaviorAnalyzer:
    """Analyzes user behavior patterns."""
    
    async def analyze(self, user_history: List[Dict]) -> Dict[str, Any]:
        """Analyze user behavior history."""
        
        if not user_history:
            return {'patterns': [], 'confidence': 0.0}
        
        # Extract behavior patterns
        frequent_actions = {}
        for interaction in user_history:
            actions = interaction.get('actions', [])
            for action in actions:
                frequent_actions[action] = frequent_actions.get(action, 0) + 1
        
        # Get most frequent actions
        sorted_actions = sorted(frequent_actions.items(), key=lambda x: x[1], reverse=True)
        top_actions = [action for action, count in sorted_actions[:5]]
        
        return {
            'frequent_actions': top_actions,
            'total_interactions': len(user_history),
            'confidence': min(len(user_history) / 10.0, 1.0)
        }


def main():
    """Test function for the multimodal integrator module."""
    print("Testing MultiModalContextIntegrator...")
    
    integrator = MultiModalContextIntegrator()
    
    # Test modality analyzers
    print("Available modality analyzers:", list(integrator.modality_analyzers.keys()))
    print("Fusion weights:", integrator.fusion_weights)
    
    # Test text analyzer
    text_analyzer = TextModalityAnalyzer()
    test_text = "I want to perform differential gene expression analysis on my RNA-seq data"
    
    print(f"\nTesting text analysis with: '{test_text}'")
    # In real usage, this would be awaited
    
    # Test session state analyzer
    session_analyzer = SessionStateAnalyzer()
    test_session = {
        'active_tools': ['seurat', 'ggplot2'],
        'loaded_data': 'counts_matrix.csv',
        'current_stage': 'preprocessing'
    }
    print(f"\nTesting session analysis with: {test_session}")
    
    # Test user behavior analyzer
    behavior_analyzer = UserBehaviorAnalyzer()
    test_history = [
        {'actions': ['load_data', 'run_qc']},
        {'actions': ['run_qc', 'filter_genes']},
        {'actions': ['normalize_data', 'run_pca']}
    ]
    print(f"\nTesting behavior analysis with {len(test_history)} interactions")


if __name__ == "__main__":
    main() 