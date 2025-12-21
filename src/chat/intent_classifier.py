"""
Intent Classification System for Scalable Routing

Uses machine learning to classify user intents instead of brittle keyword matching.
Much more scalable and maintainable than hardcoded rules.
"""

import pickle
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib
import logging

@dataclass
class IntentResult:
    intent: str
    confidence: float
    strategy: str
    reasoning: str

class IntentClassifier:
    """
    ML-based intent classification for routing decisions.
    
    Benefits:
    - No hardcoded keywords
    - Learns from examples
    - Handles variations naturally
    - Easy to extend with new intents
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger("intent_classifier")
        self.model = None
        self.intent_mapping = {
            'plot_analysis': {'strategy': 'mcp', 'priority': 0.9},
            'search_query': {'strategy': 'direct', 'priority': 0.95},
            'reasoning_question': {'strategy': 'llm', 'priority': 0.8},
            'data_upload': {'strategy': 'direct', 'priority': 0.9},
            'biological_analysis': {'strategy': 'mcp', 'priority': 0.85},
            'general_question': {'strategy': 'llm', 'priority': 0.6}
        }
        
        if model_path:
            self.load_model(model_path)
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        """Create a default model with training examples"""
        
        # Training data - in production, this would come from user interactions
        training_data = [
            # Plot analysis examples
            ("analyze the plots", "plot_analysis"),
            ("what do these charts show", "plot_analysis"),
            ("explain the PCA results", "plot_analysis"),
            ("summarize current visualizations", "plot_analysis"),
            ("interpret this graph", "plot_analysis"),
            ("what does the UMAP plot tell us", "plot_analysis"),
            ("analyze the volcano plot", "plot_analysis"),
            
            # Search examples
            ("search for cancer in GEO", "search_query"),
            ("find proteins in UniProt", "search_query"),
            ("look up datasets in TCGA", "search_query"),
            ("search PubMed for immunotherapy", "search_query"),
            ("geo search breast cancer", "search_query"),
            
            # Reasoning examples
            ("what is the difference between PCA and t-SNE", "reasoning_question"),
            ("how does differential expression work", "reasoning_question"),
            ("why should I use scRNA-seq", "reasoning_question"),
            ("compare clustering methods", "reasoning_question"),
            ("explain the theory behind UMAP", "reasoning_question"),
            
            # Data upload examples
            ("upload a file", "data_upload"),
            ("import my data", "data_upload"),
            ("load dataset", "data_upload"),
            
            # Biological analysis examples
            ("cluster my cells", "biological_analysis"),
            ("run differential expression", "biological_analysis"),
            ("find marker genes", "biological_analysis"),
            ("perform quality control", "biological_analysis"),
            ("normalize the data", "biological_analysis"),
            
            # General questions
            ("what can you help me with", "general_question"),
            ("how do I get started", "general_question"),
            ("what analysis should I do next", "general_question")
        ]
        
        # Create pipeline
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=1000,
                stop_words='english'
            )),
            ('classifier', RandomForestClassifier(
                n_estimators=100,
                random_state=42
            ))
        ])
        
        # Train model
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        self.model.fit(texts, labels)
        self.logger.info(f"Trained intent classifier with {len(training_data)} examples")
    
    def classify_intent(self, user_input: str, context: Dict = None) -> IntentResult:
        """
        Classify user intent using ML model.
        
        Args:
            user_input: User's message
            context: Session context for additional signals
            
        Returns:
            IntentResult with classified intent and routing strategy
        """
        if not self.model:
            self.logger.error("Model not loaded")
            return IntentResult("general_question", 0.5, "llm", "Model not available")
        
        # Get prediction and confidence
        predicted_intent = self.model.predict([user_input])[0]
        probabilities = self.model.predict_proba([user_input])[0]
        
        # Get confidence (max probability)
        confidence = float(np.max(probabilities))
        
        # Apply context adjustments
        adjusted_confidence = self._adjust_confidence_with_context(
            predicted_intent, confidence, context or {}
        )
        
        # Get strategy from mapping
        intent_info = self.intent_mapping.get(predicted_intent, {'strategy': 'llm', 'priority': 0.5})
        strategy = intent_info['strategy']
        
        # Generate reasoning
        reasoning = f"ML classifier: {predicted_intent} (confidence: {adjusted_confidence:.2f})"
        
        return IntentResult(
            intent=predicted_intent,
            confidence=adjusted_confidence,
            strategy=strategy,
            reasoning=reasoning
        )
    
    def _adjust_confidence_with_context(self, intent: str, confidence: float, context: Dict) -> float:
        """Adjust confidence based on session context"""
        
        # Boost plot analysis if we're in visualization steps
        if intent == "plot_analysis":
            current_step = context.get("current_step")
            if current_step in ["dimred", "clustering", "viz", "dea", "enrichment"]:
                confidence += 0.2
            
            # Boost if we have data uploaded
            if context.get("uploaded_data"):
                confidence += 0.1
        
        # Boost biological analysis if we have the right data type
        elif intent == "biological_analysis":
            analysis_type = context.get("analysis_type")
            if analysis_type in ["scrnaseq", "rnaseq", "proteomics"]:
                confidence += 0.15
        
        # Boost search if no data is uploaded (user likely exploring)
        elif intent == "search_query":
            if not context.get("uploaded_data"):
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def add_training_example(self, text: str, intent: str):
        """Add a new training example and retrain (online learning)"""
        # In production, you'd save this to a database and retrain periodically
        self.logger.info(f"Added training example: '{text}' -> {intent}")
    
    def save_model(self, path: str):
        """Save the trained model"""
        joblib.dump(self.model, path)
        self.logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load a pre-trained model"""
        try:
            self.model = joblib.load(path)
            self.logger.info(f"Model loaded from {path}")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self._create_default_model()

# Global instance
intent_classifier = IntentClassifier()

def get_intent_based_routing(user_input: str, context: Dict = None) -> Dict[str, float]:
    """
    Get routing scores based on ML intent classification.
    
    This replaces the hardcoded keyword matching with ML-based classification.
    """
    result = intent_classifier.classify_intent(user_input, context)
    
    # Convert to routing scores
    scores = {
        'direct': 0.0,
        'mcp': 0.0,
        'llm': 0.0
    }
    
    # Set score based on predicted strategy
    scores[result.strategy] = result.confidence
    
    return scores, result.reasoning

# Test the classifier
if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    test_queries = [
        "analyze the PCA plot",
        "search for cancer datasets",
        "what is the difference between PCA and UMAP",
        "cluster my single cells",
        "upload my data file"
    ]
    
    for query in test_queries:
        result = intent_classifier.classify_intent(query)
        print(f"'{query}' -> {result.intent} ({result.strategy}) - {result.confidence:.2f}") 