"""
Advanced Message Analysis
AI-powered message analysis for intelligent provider selection.
"""

import re
import asyncio
import time
from typing import Dict, List, Any, Optional, NamedTuple
from enum import Enum
from dataclasses import dataclass
import structlog

# Optional NLP dependencies
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    EXPERT = 4


class QueryCategory(Enum):
    """Query categories for analysis."""
    INFORMATIONAL = "informational"
    ANALYTICAL = "analytical"
    COMPUTATIONAL = "computational"
    INTERPRETIVE = "interpretive"
    TROUBLESHOOTING = "troubleshooting"


class MessageAnalysis(NamedTuple):
    """Complete message analysis result."""
    complexity: QueryComplexity
    category: QueryCategory
    domain_specificity: float  # 0-1 score
    estimated_tokens: int
    requires_external_knowledge: bool
    confidence: float
    keywords: List[str]
    sentiment: str
    urgency: float
    estimated_cost: float


@dataclass
class AnalysisConfig:
    """Configuration for message analysis."""
    enable_nlp: bool = True
    enable_sentiment: bool = True
    enable_domain_detection: bool = True
    complexity_threshold: float = 0.6
    domain_threshold: float = 0.5
    max_keywords: int = 10


class MessageAnalyzer:
    """
    Advanced message analyzer with AI-powered analysis.
    
    Features:
    - Complexity assessment using multiple heuristics
    - Domain-specific keyword detection
    - Sentiment analysis
    - Token estimation for cost calculation
    - Category classification
    - Urgency detection
    """
    
    def __init__(self, config: AnalysisConfig = None):
        self.logger = structlog.get_logger("message_analyzer")
        self.config = config or AnalysisConfig()
        
        # NLP models (lazy loaded)
        self.nlp = None
        self.classifier = None
        self.sentiment_analyzer = None
        
        # Pattern-based analysis
        self.complexity_patterns = {
            QueryComplexity.SIMPLE: [
                r'\b(what is|define|explain simply|show me|list|help)\b',
                r'\b(basic|simple|overview|introduction|tutorial)\b',
                r'\b(how to|quick|easy|straightforward)\b'
            ],
            QueryComplexity.MODERATE: [
                r'\b(compare|analyze|summarize|interpret|understand)\b',
                r'\b(difference|relationship|correlation|trend)\b',
                r'\b(step by step|guide|process|workflow)\b'
            ],
            QueryComplexity.COMPLEX: [
                r'\b(comprehensive|detailed|in-depth|advanced|thorough)\b',
                r'\b(statistical|significance|methodology|algorithm)\b',
                r'\b(optimization|troubleshoot|debug|investigate)\b'
            ],
            QueryComplexity.EXPERT: [
                r'\b(machine learning|deep learning|neural network)\b',
                r'\b(computational biology|bioinformatics|systems biology)\b',
                r'\b(implement|develop|create|design|architect)\b'
            ]
        }
        
        # Domain-specific keywords
        self.domain_keywords = {
            'genomics': ['genome', 'genomic', 'dna', 'sequencing', 'variants', 'gwas', 'snp'],
            'transcriptomics': ['rna-seq', 'scrna-seq', 'expression', 'transcript', 'gene', 'mrna'],
            'proteomics': ['protein', 'proteome', 'mass spec', 'peptide', 'antibody'],
            'systems_biology': ['pathway', 'network', 'interaction', 'regulation', 'signaling'],
            'statistics': ['p-value', 'fdr', 'correlation', 'regression', 'anova', 'chi-square'],
            'machine_learning': ['clustering', 'classification', 'prediction', 'model', 'training'],
            'data_analysis': ['visualization', 'plot', 'graph', 'heatmap', 'pca', 'umap', 'tsne']
        }
        
        # Category patterns
        self.category_patterns = {
            QueryCategory.INFORMATIONAL: [
                r'\b(what|who|when|where|define|explain|describe)\b',
                r'\b(information|details|background|overview)\b'
            ],
            QueryCategory.ANALYTICAL: [
                r'\b(analyze|compare|evaluate|assess|examine)\b',
                r'\b(analysis|comparison|evaluation|assessment)\b'
            ],
            QueryCategory.COMPUTATIONAL: [
                r'\b(calculate|compute|run|execute|process)\b',
                r'\b(algorithm|function|script|code|program)\b'
            ],
            QueryCategory.INTERPRETIVE: [
                r'\b(interpret|understand|meaning|significance)\b',
                r'\b(results|output|findings|implications)\b'
            ],
            QueryCategory.TROUBLESHOOTING: [
                r'\b(error|problem|issue|bug|fix|debug)\b',
                r'\b(troubleshoot|solve|resolve|help)\b'
            ]
        }
        
        # Urgency indicators
        self.urgency_patterns = [
            r'\b(urgent|asap|immediately|quickly|fast)\b',
            r'\b(deadline|due|emergency|critical|priority)\b',
            r'\b(need now|right away|time sensitive)\b'
        ]
    
    async def analyze_message(
        self, 
        message: str, 
        context: Dict[str, Any] = None
    ) -> MessageAnalysis:
        """
        Perform comprehensive message analysis.
        
        Args:
            message: User's input message
            context: Additional context for analysis
            
        Returns:
            Complete message analysis
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # Initialize NLP models if needed
            if self.config.enable_nlp:
                await self._ensure_nlp_models()
            
            # Core analysis components
            complexity = await self._assess_complexity(message, context)
            category = await self._classify_category(message, context)
            domain_specificity = self._calculate_domain_specificity(message)
            estimated_tokens = self._estimate_tokens(message)
            requires_external = self._requires_external_knowledge(message, context)
            keywords = self._extract_keywords(message)
            sentiment = await self._analyze_sentiment(message) if self.config.enable_sentiment else "neutral"
            urgency = self._detect_urgency(message)
            estimated_cost = self._estimate_cost(estimated_tokens, complexity)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(
                message, complexity, category, domain_specificity
            )
            
            analysis_time = time.time() - start_time
            
            self.logger.info(
                "Message analysis completed",
                complexity=complexity.name,
                category=category.value,
                domain_specificity=domain_specificity,
                analysis_time=analysis_time
            )
            
            return MessageAnalysis(
                complexity=complexity,
                category=category,
                domain_specificity=domain_specificity,
                estimated_tokens=estimated_tokens,
                requires_external_knowledge=requires_external,
                confidence=confidence,
                keywords=keywords,
                sentiment=sentiment,
                urgency=urgency,
                estimated_cost=estimated_cost
            )
            
        except Exception as e:
            self.logger.error("Message analysis failed", error=str(e))
            # Return basic analysis as fallback
            return self._create_fallback_analysis(message)
    
    async def _ensure_nlp_models(self):
        """Lazy load NLP models."""
        if not self.config.enable_nlp:
            return
        
        try:
            # Load spaCy model
            if SPACY_AVAILABLE and self.nlp is None:
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except OSError:
                    self.logger.warning("spaCy model not found, using basic analysis")
                    self.nlp = None
            
            # Load classification model
            if TRANSFORMERS_AVAILABLE and self.classifier is None:
                try:
                    self.classifier = pipeline(
                        "text-classification",
                        model="microsoft/DialoGPT-medium",
                        return_all_scores=True
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to load classifier: {e}")
                    self.classifier = None
            
            # Load sentiment analyzer
            if TRANSFORMERS_AVAILABLE and self.sentiment_analyzer is None:
                try:
                    self.sentiment_analyzer = pipeline(
                        "sentiment-analysis",
                        model="cardiffnlp/twitter-roberta-base-sentiment-latest"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to load sentiment analyzer: {e}")
                    self.sentiment_analyzer = None
                    
        except Exception as e:
            self.logger.warning(f"NLP model initialization failed: {e}")
    
    async def _assess_complexity(
        self, 
        message: str, 
        context: Dict[str, Any]
    ) -> QueryComplexity:
        """Assess message complexity using multiple methods."""
        
        # Pattern-based complexity assessment
        pattern_scores = {complexity: 0 for complexity in QueryComplexity}
        message_lower = message.lower()
        
        for complexity, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    pattern_scores[complexity] += 1
        
        # Heuristic-based scoring
        heuristic_score = 1
        
        # Length-based complexity
        word_count = len(message.split())
        if word_count > 50:
            heuristic_score += 1
        if word_count > 100:
            heuristic_score += 1
        
        # Question complexity
        question_count = message.count('?')
        if question_count > 2:
            heuristic_score += 1
        
        # Technical terms
        technical_terms = sum(1 for domain_keywords in self.domain_keywords.values()
                            for keyword in domain_keywords
                            if keyword in message_lower)
        if technical_terms > 5:
            heuristic_score += 1
        
        # Context-based adjustments
        if context.get('has_analysis_results'):
            heuristic_score += 1
        
        # Combine pattern and heuristic scores
        max_pattern_complexity = max(pattern_scores, key=pattern_scores.get)
        final_complexity = max(
            max_pattern_complexity,
            QueryComplexity(min(heuristic_score, 4))
        )
        
        return final_complexity
    
    async def _classify_category(
        self, 
        message: str, 
        context: Dict[str, Any]
    ) -> QueryCategory:
        """Classify message category."""
        
        category_scores = {category: 0 for category in QueryCategory}
        message_lower = message.lower()
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    category_scores[category] += 1
        
        # If no clear pattern match, use heuristics
        if sum(category_scores.values()) == 0:
            if any(word in message_lower for word in ['what', 'who', 'when', 'where']):
                return QueryCategory.INFORMATIONAL
            elif any(word in message_lower for word in ['analyze', 'compare', 'examine']):
                return QueryCategory.ANALYTICAL
            elif any(word in message_lower for word in ['run', 'execute', 'calculate']):
                return QueryCategory.COMPUTATIONAL
            else:
                return QueryCategory.INFORMATIONAL
        
        return max(category_scores, key=category_scores.get)
    
    def _calculate_domain_specificity(self, message: str) -> float:
        """Calculate domain specificity score (0-1)."""
        message_lower = message.lower()
        
        domain_scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                domain_scores[domain] = score / len(keywords)
        
        if not domain_scores:
            return 0.0
        
        # Return the highest domain specificity
        max_specificity = max(domain_scores.values())
        return min(max_specificity, 1.0)
    
    def _estimate_tokens(self, message: str) -> int:
        """Estimate token count for the message."""
        # Simple estimation: words * 1.3 (accounting for punctuation and encoding)
        word_count = len(message.split())
        return int(word_count * 1.3)
    
    def _requires_external_knowledge(
        self, 
        message: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Determine if message requires external knowledge."""
        
        # Check for interpretation requests
        if any(word in message.lower() for word in 
               ['interpret', 'meaning', 'significance', 'implications']):
            return True
        
        # Check for complex analysis requests
        if any(word in message.lower() for word in 
               ['comprehensive', 'detailed', 'in-depth', 'thorough']):
            return True
        
        # Check for domain-specific complex queries
        domain_specificity = self._calculate_domain_specificity(message)
        if domain_specificity > 0.7:
            return True
        
        # Check context
        if context.get('analysis_type') == 'production':
            return True
        
        return False
    
    def _extract_keywords(self, message: str) -> List[str]:
        """Extract important keywords from message."""
        keywords = []
        message_lower = message.lower()
        
        # Extract domain-specific keywords
        for domain_keywords in self.domain_keywords.values():
            for keyword in domain_keywords:
                if keyword in message_lower:
                    keywords.append(keyword)
        
        # Extract technical terms (simple heuristic)
        words = message.split()
        for word in words:
            if (len(word) > 6 and 
                word.lower() not in ['analysis', 'results', 'please', 'thanks']):
                keywords.append(word.lower())
        
        # Remove duplicates and limit count
        unique_keywords = list(set(keywords))
        return unique_keywords[:self.config.max_keywords]
    
    async def _analyze_sentiment(self, message: str) -> str:
        """Analyze message sentiment."""
        if not self.sentiment_analyzer:
            return "neutral"
        
        try:
            result = self.sentiment_analyzer(message)
            if result and len(result) > 0:
                return result[0]['label'].lower()
        except Exception as e:
            self.logger.warning(f"Sentiment analysis failed: {e}")
        
        return "neutral"
    
    def _detect_urgency(self, message: str) -> float:
        """Detect urgency level (0-1)."""
        message_lower = message.lower()
        urgency_score = 0.0
        
        for pattern in self.urgency_patterns:
            if re.search(pattern, message_lower):
                urgency_score += 0.3
        
        # Check for exclamation marks
        exclamation_count = message.count('!')
        urgency_score += min(exclamation_count * 0.1, 0.3)
        
        # Check for capital letters (shouting)
        if message.isupper():
            urgency_score += 0.2
        
        return min(urgency_score, 1.0)
    
    def _estimate_cost(self, tokens: int, complexity: QueryComplexity) -> float:
        """Estimate processing cost based on tokens and complexity."""
        base_cost = tokens * 0.001  # Base cost per token
        
        # Complexity multiplier
        complexity_multipliers = {
            QueryComplexity.SIMPLE: 1.0,
            QueryComplexity.MODERATE: 1.5,
            QueryComplexity.COMPLEX: 2.0,
            QueryComplexity.EXPERT: 3.0
        }
        
        multiplier = complexity_multipliers.get(complexity, 1.0)
        return base_cost * multiplier
    
    def _calculate_confidence(
        self,
        message: str,
        complexity: QueryComplexity,
        category: QueryCategory,
        domain_specificity: float
    ) -> float:
        """Calculate confidence score for the analysis."""
        
        confidence = 0.8  # Base confidence
        
        # Adjust based on message length
        word_count = len(message.split())
        if word_count < 5:
            confidence -= 0.2
        elif word_count > 50:
            confidence += 0.1
        
        # Adjust based on domain specificity
        if domain_specificity > 0.5:
            confidence += 0.1
        
        # Adjust based on pattern matches
        pattern_matches = sum(1 for patterns in self.complexity_patterns.values()
                            for pattern in patterns
                            if re.search(pattern, message.lower()))
        
        if pattern_matches > 0:
            confidence += min(pattern_matches * 0.05, 0.2)
        
        return min(confidence, 1.0)
    
    def _create_fallback_analysis(self, message: str) -> MessageAnalysis:
        """Create basic analysis when detailed analysis fails."""
        return MessageAnalysis(
            complexity=QueryComplexity.MODERATE,
            category=QueryCategory.INFORMATIONAL,
            domain_specificity=0.3,
            estimated_tokens=len(message.split()),
            requires_external_knowledge=False,
            confidence=0.5,
            keywords=[],
            sentiment="neutral",
            urgency=0.0,
            estimated_cost=0.01
        )


def main():
    """Main function for testing message analyzer."""
    import asyncio
    
    async def test_analyzer():
        print("🧪 Testing Message Analyzer...")
        
        analyzer = MessageAnalyzer()
        
        test_messages = [
            "What is RNA-seq?",
            "Help me interpret my differential expression analysis results",
            "I need a comprehensive pathway analysis of my data ASAP!",
            "Can you run a PCA on my single-cell data and create a UMAP visualization?",
            "Error in my clustering algorithm - need debugging help immediately",
            "Simple question about gene expression"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 Test {i}: '{message}'")
            
            analysis = await analyzer.analyze_message(message)
            
            print(f"   Complexity: {analysis.complexity.name}")
            print(f"   Category: {analysis.category.value}")
            print(f"   Domain Specificity: {analysis.domain_specificity:.2f}")
            print(f"   Est. Tokens: {analysis.estimated_tokens}")
            print(f"   External Knowledge: {analysis.requires_external_knowledge}")
            print(f"   Keywords: {analysis.keywords[:3]}")
            print(f"   Sentiment: {analysis.sentiment}")
            print(f"   Urgency: {analysis.urgency:.2f}")
            print(f"   Est. Cost: ${analysis.estimated_cost:.4f}")
            print(f"   Confidence: {analysis.confidence:.2f}")
        
        print("\n🎉 Message analyzer tests completed!")
    
    asyncio.run(test_analyzer())


if __name__ == "__main__":
    main() 