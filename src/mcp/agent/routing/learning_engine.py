"""
Continuous Learning Engine for Context Analysis

This module implements online learning capabilities to improve
context analysis based on user feedback and interactions.
"""

import numpy as np
from sklearn.linear_model import SGDClassifier, SGDRegressor
from datetime import datetime
from typing import Dict, List, Any
import logging
from .biological_context import BiologicalContext


class ContinuousLearningEngine:
    """Learns from user interactions to improve context analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger("continuous_learning")
        self.interaction_buffer = []
        self.model_update_threshold = 100
        self.learning_rate = 0.01
        
        # Online learning models
        self.domain_classifier_online = SGDClassifier(
            loss='log_loss', learning_rate='adaptive', random_state=42
        )
        self.tool_recommender_online = SGDRegressor(
            learning_rate='adaptive', random_state=42
        )
        
        # Learning metrics
        self.learning_metrics = {
            'total_interactions': 0,
            'successful_predictions': 0,
            'model_updates': 0,
            'average_satisfaction': 0.0
        }
    
    async def record_interaction(
        self, 
        query: str,
        predicted_context: BiologicalContext,
        user_actions: List[str],
        outcome_success: bool,
        time_to_completion: float
    ):
        """Record user interaction for learning."""
        
        interaction = {
            'timestamp': datetime.now(),
            'query': query,
            'predicted_context': predicted_context,
            'user_actions': user_actions,
            'success': outcome_success,
            'completion_time': time_to_completion,
            'query_features': self._extract_query_features(query)
        }
        
        self.interaction_buffer.append(interaction)
        self.learning_metrics['total_interactions'] += 1
        
        if outcome_success:
            self.learning_metrics['successful_predictions'] += 1
        
        # Trigger learning if buffer is full
        if len(self.interaction_buffer) >= self.model_update_threshold:
            await self._update_models()
    
    async def _update_models(self):
        """Update models with recent interactions."""
        
        if not self.interaction_buffer:
            return
        
        # Prepare training data
        X_domain, y_domain = self._prepare_domain_training_data()
        X_tools, y_tools = self._prepare_tool_training_data()
        
        # Update domain classifier
        if len(X_domain) > 0 and len(set(y_domain)) > 1:
            try:
                if not hasattr(self.domain_classifier_online, 'classes_'):
                    self.domain_classifier_online.fit(X_domain, y_domain)
                else:
                    self.domain_classifier_online.partial_fit(X_domain, y_domain)
                self.logger.info("Updated domain classifier")
            except Exception as e:
                self.logger.warning(f"Failed to update domain classifier: {e}")
        
        # Update tool recommender
        if len(X_tools) > 0:
            try:
                if not hasattr(self.tool_recommender_online, 'coef_'):
                    self.tool_recommender_online.fit(X_tools, y_tools)
                else:
                    self.tool_recommender_online.partial_fit(X_tools, y_tools)
                self.logger.info("Updated tool recommender")
            except Exception as e:
                self.logger.warning(f"Failed to update tool recommender: {e}")
        
        # Update metrics
        self.learning_metrics['model_updates'] += 1
        success_rate = (self.learning_metrics['successful_predictions'] / 
                       max(self.learning_metrics['total_interactions'], 1))
        self.learning_metrics['average_satisfaction'] = success_rate
        
        # Clear buffer
        self.interaction_buffer = []
        
        self.logger.info("Models updated with recent interactions")
    
    def _prepare_domain_training_data(self) -> tuple:
        """Prepare training data for domain classification."""
        X, y = [], []
        
        for interaction in self.interaction_buffer:
            if interaction['success']:
                features = interaction['query_features']
                domain = interaction['predicted_context'].primary_domain
                
                X.append(features)
                y.append(domain)
        
        return np.array(X) if X else np.array([]), y
    
    def _prepare_tool_training_data(self) -> tuple:
        """Prepare training data for tool recommendation."""
        X, y = [], []
        
        for interaction in self.interaction_buffer:
            if interaction['success']:
                features = interaction['query_features']
                for action in interaction['user_actions']:
                    if self._is_tool_action(action):
                        X.append(features)
                        y.append(1.0)
        
        return np.array(X) if X else np.array([]), y
    
    def _extract_query_features(self, query: str) -> List[float]:
        """Extract numerical features from query for ML models."""
        features = []
        
        # Basic text features
        features.append(len(query))
        features.append(len(query.split()))
        features.append(query.count('?'))
        features.append(query.count(','))
        
        # Domain-specific keywords
        domain_keywords = {
            'rnaseq': ['rna', 'expression', 'transcript', 'gene'],
            'scrna': ['single', 'cell', 'scrna', 'clustering'],
            'proteomics': ['protein', 'mass', 'spec', 'proteome'],
            'genomics': ['genome', 'variant', 'snp', 'mutation']
        }
        
        for domain, keywords in domain_keywords.items():
            keyword_count = sum(1 for kw in keywords if kw in query.lower())
            features.append(keyword_count)
        
        # Analysis type keywords
        analysis_keywords = [
            'differential', 'pathway', 'cluster', 'visualize', 
            'normalize', 'filter', 'quality'
        ]
        
        analysis_mentions = sum(1 for kw in analysis_keywords if kw in query.lower())
        features.append(analysis_mentions)
        
        return features
    
    def _is_tool_action(self, action: str) -> bool:
        """Check if action represents using a specific tool."""
        tool_indicators = ['run', 'execute', 'use', 'apply', 'perform']
        return any(indicator in action.lower() for indicator in tool_indicators)
    
    def get_adaptation_insights(self) -> Dict[str, Any]:
        """Get insights about model adaptation patterns."""
        
        if not self.interaction_buffer:
            return self.learning_metrics.copy()
        
        recent_interactions = self.interaction_buffer[-50:]
        
        success_rate = sum(i['success'] for i in recent_interactions) / len(recent_interactions)
        avg_completion_time = np.mean([i['completion_time'] for i in recent_interactions])
        
        insights = self.learning_metrics.copy()
        insights.update({
            'recent_success_rate': success_rate,
            'avg_completion_time': avg_completion_time,
            'buffer_size': len(self.interaction_buffer)
        })
        
        return insights


def main():
    """Test function for the learning engine module."""
    print("Testing ContinuousLearningEngine...")
    
    engine = ContinuousLearningEngine()
    
    # Test feature extraction
    test_query = "How do I perform differential expression analysis on my RNA-seq data?"
    features = engine._extract_query_features(test_query)
    print(f"Query: {test_query}")
    print(f"Extracted features: {features}")
    
    # Test learning metrics
    insights = engine.get_adaptation_insights()
    print(f"Learning insights: {insights}")


if __name__ == "__main__":
    main() 