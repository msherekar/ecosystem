"""
Semantic Similarity Router - Uses embeddings for intent matching

This approach is highly scalable because:
1. No hardcoded keywords needed
2. Handles variations and synonyms naturally
3. Easy to add new examples without retraining
4. Works with any language model embeddings
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
import logging
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class RoutingExample:
    text: str
    strategy: str
    intent: str
    priority: float
    embedding: Optional[np.ndarray] = None

@dataclass
class SemanticResult:
    strategy: str
    confidence: float
    intent: str
    reasoning: str
    similar_examples: List[str]

class SemanticRouter:
    """
    Semantic similarity-based routing using embeddings.
    
    Benefits:
    - Handles natural language variations
    - No brittle keyword matching
    - Easy to extend with new examples
    - Learns semantic relationships
    """
    
    def __init__(self, examples_file: Optional[str] = None):
        self.logger = logging.getLogger("semantic_router")
        self.examples: List[RoutingExample] = []
        self.embeddings_cache = {}
        
        if examples_file:
            self.load_examples(examples_file)
        else:
            self._create_default_examples()
    
    def _create_default_examples(self):
        """Create default routing examples"""
        
        examples_data = [
            # Plot Analysis Examples
            ("analyze the plots", "mcp", "plot_analysis", 0.9),
            ("what do the charts show", "mcp", "plot_analysis", 0.9),
            ("explain the PCA results", "mcp", "plot_analysis", 0.9),
            ("summarize current visualizations", "mcp", "plot_analysis", 0.9),
            ("interpret this graph", "mcp", "plot_analysis", 0.9),
            ("tell me about the figures", "mcp", "plot_analysis", 0.9),
            ("what does this plot mean", "mcp", "plot_analysis", 0.9),
            ("analyze the UMAP", "mcp", "plot_analysis", 0.9),
            ("explain the volcano plot", "mcp", "plot_analysis", 0.9),
            ("summarize the visualization", "mcp", "plot_analysis", 0.9),
            ("what are the main findings in this chart", "mcp", "plot_analysis", 0.9),
            
            # Search Examples
            ("search for cancer in GEO", "direct", "search_query", 0.95),
            ("find datasets about cancer", "direct", "search_query", 0.95),
            ("look up proteins in UniProt", "direct", "search_query", 0.95),
            ("search PubMed for papers", "direct", "search_query", 0.95),
            ("find genes in the database", "direct", "search_query", 0.95),
            ("lookup information about", "direct", "search_query", 0.95),
            ("search the literature for", "direct", "search_query", 0.95),
            ("find datasets related to", "direct", "search_query", 0.95),
            
            # Reasoning Examples
            ("what is the difference between PCA and t-SNE", "llm", "reasoning", 0.8),
            ("how does differential expression work", "llm", "reasoning", 0.8),
            ("why should I use this method", "llm", "reasoning", 0.8),
            ("compare these algorithms", "llm", "reasoning", 0.8),
            ("explain the theory behind", "llm", "reasoning", 0.8),
            ("what are the pros and cons", "llm", "reasoning", 0.8),
            ("help me understand the concept", "llm", "reasoning", 0.8),
            ("which method is better", "llm", "reasoning", 0.8),
            
            # Biological Analysis Examples
            ("cluster my cells", "mcp", "bio_analysis", 0.85),
            ("run differential expression", "mcp", "bio_analysis", 0.85),
            ("find marker genes", "mcp", "bio_analysis", 0.85),
            ("perform quality control", "mcp", "bio_analysis", 0.85),
            ("normalize the data", "mcp", "bio_analysis", 0.85),
            ("run the analysis pipeline", "mcp", "bio_analysis", 0.85),
            ("process my single cell data", "mcp", "bio_analysis", 0.85),
            
            # File Operations
            ("upload a file", "direct", "file_operation", 0.9),
            ("import my data", "direct", "file_operation", 0.9),
            ("load the dataset", "direct", "file_operation", 0.9),
            ("create a new project", "direct", "project_management", 0.9),
        ]
        
        for text, strategy, intent, priority in examples_data:
            self.examples.append(RoutingExample(
                text=text,
                strategy=strategy,
                intent=intent,
                priority=priority
            ))
        
        self.logger.info(f"Created {len(self.examples)} default routing examples")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for text. This is a placeholder - in production you'd use:
        - OpenAI embeddings API
        - Sentence transformers
        - Local embedding models
        """
        
        # Cache embeddings to avoid recomputation
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        # Simple TF-IDF based embedding (replace with real embeddings)
        # In production, use something like:
        # embedding = openai.embeddings.create(input=text, model="text-embedding-ada-002")
        
        # For demo purposes, create a simple word-based embedding
        words = text.lower().split()
        
        # Create vocabulary from all examples
        vocab = set()
        for example in self.examples:
            vocab.update(example.text.lower().split())
        vocab = sorted(list(vocab))
        
        # Create simple bag-of-words embedding
        embedding = np.zeros(len(vocab))
        for i, word in enumerate(vocab):
            if word in words:
                embedding[i] = 1.0
        
        # Normalize
        if np.linalg.norm(embedding) > 0:
            embedding = embedding / np.linalg.norm(embedding)
        
        self.embeddings_cache[text] = embedding
        return embedding
    
    def find_most_similar(self, user_input: str, top_k: int = 5) -> List[Tuple[RoutingExample, float]]:
        """Find most similar examples to user input"""
        
        input_embedding = self._get_embedding(user_input)
        similarities = []
        
        for example in self.examples:
            if example.embedding is None:
                example.embedding = self._get_embedding(example.text)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(
                input_embedding.reshape(1, -1),
                example.embedding.reshape(1, -1)
            )[0][0]
            
            similarities.append((example, similarity))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def route_request(self, user_input: str, context: Dict = None) -> SemanticResult:
        """
        Route request based on semantic similarity to examples.
        
        Args:
            user_input: User's message
            context: Session context
            
        Returns:
            SemanticResult with routing decision
        """
        
        # Find similar examples
        similar_examples = self.find_most_similar(user_input, top_k=5)
        
        if not similar_examples:
            return SemanticResult(
                strategy="llm",
                confidence=0.5,
                intent="general",
                reasoning="No similar examples found",
                similar_examples=[]
            )
        
        # Weight votes by similarity and priority
        strategy_votes = {}
        intent_votes = {}
        
        total_weight = 0
        for example, similarity in similar_examples:
            weight = similarity * example.priority
            total_weight += weight
            
            # Vote for strategy
            if example.strategy not in strategy_votes:
                strategy_votes[example.strategy] = 0
            strategy_votes[example.strategy] += weight
            
            # Vote for intent
            if example.intent not in intent_votes:
                intent_votes[example.intent] = 0
            intent_votes[example.intent] += weight
        
        # Normalize votes
        if total_weight > 0:
            strategy_votes = {k: v/total_weight for k, v in strategy_votes.items()}
            intent_votes = {k: v/total_weight for k, v in intent_votes.items()}
        
        # Get top strategy and intent
        best_strategy = max(strategy_votes.items(), key=lambda x: x[1])
        best_intent = max(intent_votes.items(), key=lambda x: x[1])
        
        # Apply context adjustments
        confidence = best_strategy[1]
        confidence = self._adjust_confidence_with_context(
            best_strategy[0], best_intent[0], confidence, context or {}
        )
        
        # Generate reasoning
        top_examples = [ex.text for ex, _ in similar_examples[:3]]
        reasoning = f"Similar to: {', '.join(top_examples[:2])}"
        
        return SemanticResult(
            strategy=best_strategy[0],
            confidence=confidence,
            intent=best_intent[0],
            reasoning=reasoning,
            similar_examples=top_examples
        )
    
    def _adjust_confidence_with_context(self, strategy: str, intent: str, confidence: float, context: Dict) -> float:
        """Adjust confidence based on context"""
        
        # Boost plot analysis in visualization contexts
        if intent == "plot_analysis":
            if context.get("current_step") in ["dimred", "clustering", "viz"]:
                confidence += 0.15
            if context.get("analysis_type") == "scrnaseq":
                confidence += 0.1
        
        # Boost bio analysis if we have data
        elif intent == "bio_analysis":
            if context.get("uploaded_data"):
                confidence += 0.1
            if context.get("analysis_type") in ["scrnaseq", "rnaseq"]:
                confidence += 0.15
        
        return min(confidence, 1.0)
    
    def add_example(self, text: str, strategy: str, intent: str, priority: float = 0.8):
        """Add a new routing example"""
        example = RoutingExample(
            text=text,
            strategy=strategy,
            intent=intent,
            priority=priority
        )
        self.examples.append(example)
        self.logger.info(f"Added routing example: '{text}' -> {strategy}")
    
    def save_examples(self, filepath: str):
        """Save examples to file"""
        data = []
        for example in self.examples:
            data.append({
                'text': example.text,
                'strategy': example.strategy,
                'intent': example.intent,
                'priority': example.priority
            })
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Saved {len(data)} examples to {filepath}")
    
    def load_examples(self, filepath: str):
        """Load examples from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.examples = []
            for item in data:
                self.examples.append(RoutingExample(
                    text=item['text'],
                    strategy=item['strategy'],
                    intent=item['intent'],
                    priority=item['priority']
                ))
            
            self.logger.info(f"Loaded {len(self.examples)} examples from {filepath}")
        
        except Exception as e:
            self.logger.error(f"Failed to load examples: {e}")
            self._create_default_examples()

# Global instance
semantic_router = SemanticRouter()

# Test the router
if __name__ == "__main__":
    test_queries = [
        "analyze the PCA plot",
        "search for cancer datasets", 
        "what is the difference between PCA and UMAP",
        "cluster my single cells",
        "tell me about this visualization",
        "find genes related to cancer",
        "explain how clustering works"
    ]
    
    for query in test_queries:
        result = semantic_router.route_request(query)
        print(f"'{query}'")
        print(f"  -> {result.strategy} ({result.intent}) - {result.confidence:.2f}")
        print(f"  -> Similar: {result.similar_examples[:2]}")
        print() 