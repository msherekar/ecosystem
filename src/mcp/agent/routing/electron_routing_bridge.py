"""
Electron Bridge for Biological Context Routing Module

Provides seamless integration between routing module and Electron frontend
for real-time biological context analysis and routing suggestions.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .enhanced_context_analyzer import EnhancedBiologicalContextAnalyzer
from .workflow_predictor import WorkflowPredictionEngine
from .file_analyzer import DataFileAnalyzer
from .temporal_analyzer import TemporalPatternAnalyzer
from .multimodal_integrator import MultiModalContextIntegrator
from .learning_engine import ContinuousLearningEngine

logger = logging.getLogger(__name__)


class ElectronRoutingBridge:
    """Bridge for routing module communication with Electron frontend."""
    
    def __init__(self):
        """Initialize the routing bridge."""
        self.context_analyzer = EnhancedBiologicalContextAnalyzer()
        self.workflow_predictor = WorkflowPredictionEngine()
        self.file_analyzer = DataFileAnalyzer()
        self.temporal_analyzer = TemporalPatternAnalyzer()
        self.multimodal_integrator = MultiModalContextIntegrator()
        self.learning_engine = ContinuousLearningEngine()
        
        # Session tracking
        self.active_sessions = {}
        self.user_contexts = {}
        
        # Statistics
        self.stats = {
            "context_analyses": 0,
            "workflow_predictions": 0,
            "file_analyses": 0,
            "user_interactions": 0
        }
        
        logger.info("Electron Routing Bridge initialized")
    
    async def analyze_query_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze biological context for a query."""
        try:
            query = data.get("query", "")
            session_id = data.get("session_id")
            user_id = data.get("user_id", "anonymous")
            
            # Get session context
            session_state = self.active_sessions.get(session_id, {})
            previous_queries = session_state.get("queries", [])
            
            # Analyze context
            context = await self.context_analyzer.analyze_context(
                query=query,
                session_state=session_state,
                user_id=user_id,
                previous_queries=previous_queries
            )
            
            # Update session
            if session_id:
                self._update_session(session_id, query, context)
            
            self.stats["context_analyses"] += 1
            
            return {
                "type": "context_analysis_response",
                "context": {
                    "primary_domain": context.primary_domain,
                    "secondary_domains": context.secondary_domains,
                    "data_types": context.data_types,
                    "experimental_design": context.experimental_design,
                    "analysis_objectives": context.analysis_objectives,
                    "workflow_stage": context.workflow_stage,
                    "complexity_score": context.complexity_score,
                    "tool_recommendations": context.tool_recommendations,
                    "confidence_metrics": context.confidence_metrics
                },
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            return {
                "type": "error",
                "error": f"Context analysis failed: {str(e)}"
            }
    
    async def predict_workflow_steps(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict next workflow steps based on context."""
        try:
            context_data = data.get("context", {})
            session_id = data.get("session_id")
            
            # Convert context data to BiologicalContext object
            from .biological_context import BiologicalContext
            context = BiologicalContext(
                primary_domain=context_data.get("primary_domain", "unknown"),
                secondary_domains=context_data.get("secondary_domains", []),
                data_types=context_data.get("data_types", []),
                experimental_design=context_data.get("experimental_design", "unknown"),
                analysis_objectives=context_data.get("analysis_objectives", []),
                workflow_stage=context_data.get("workflow_stage", "initial"),
                complexity_score=context_data.get("complexity_score", 0.5),
                tool_recommendations=context_data.get("tool_recommendations", {}),
                integration_requirements=context_data.get("integration_requirements", {}),
                confidence_metrics=context_data.get("confidence_metrics", {})
            )
            
            # Predict next steps
            predictions = await self.workflow_predictor.predict_next_steps(context)
            
            self.stats["workflow_predictions"] += 1
            
            return {
                "type": "workflow_prediction_response",
                "predictions": predictions,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error predicting workflow: {e}")
            return {
                "type": "error",
                "error": f"Workflow prediction failed: {str(e)}"
            }
    
    async def analyze_uploaded_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze uploaded files for context."""
        try:
            files_data = data.get("files", [])
            session_id = data.get("session_id")
            
            # Create mock file objects from data
            class MockFile:
                def __init__(self, file_data):
                    self.name = file_data.get("name", "unknown")
                    self.size = file_data.get("size", 0)
                    self.content = file_data.get("content", "")
                
                def read(self, n):
                    return self.content.encode('utf-8')
            
            files = [MockFile(file_data) for file_data in files_data]
            
            # Analyze files
            analysis_result = await self.file_analyzer.analyze(files)
            
            # Update session with file context
            if session_id and session_id in self.active_sessions:
                self.active_sessions[session_id]["uploaded_files"] = analysis_result
            
            self.stats["file_analyses"] += 1
            
            return {
                "type": "file_analysis_response",
                "analysis": analysis_result,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing files: {e}")
            return {
                "type": "error",
                "error": f"File analysis failed: {str(e)}"
            }
    
    async def get_tool_recommendations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get tool recommendations based on context."""
        try:
            context_data = data.get("context", {})
            domain = context_data.get("primary_domain", "unknown")
            data_types = context_data.get("data_types", [])
            objectives = context_data.get("analysis_objectives", [])
            
            # Generate recommendations based on domain and objectives
            recommendations = self._generate_tool_recommendations(domain, data_types, objectives)
            
            return {
                "type": "tool_recommendations_response",
                "recommendations": recommendations,
                "domain": domain,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting tool recommendations: {e}")
            return {
                "type": "error",
                "error": f"Tool recommendation failed: {str(e)}"
            }
    
    async def record_user_interaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Record user interaction for learning."""
        try:
            query = data.get("query", "")
            action = data.get("action", "")
            outcome = data.get("outcome", "unknown")
            session_id = data.get("session_id")
            user_id = data.get("user_id", "anonymous")
            
            # Get predicted context if available
            predicted_context = data.get("predicted_context")
            
            # Record interaction for learning
            if predicted_context:
                from .biological_context import BiologicalContext
                context_obj = BiologicalContext(
                    primary_domain=predicted_context.get("primary_domain", "unknown"),
                    secondary_domains=predicted_context.get("secondary_domains", []),
                    data_types=predicted_context.get("data_types", []),
                    experimental_design=predicted_context.get("experimental_design", "unknown"),
                    analysis_objectives=predicted_context.get("analysis_objectives", []),
                    workflow_stage=predicted_context.get("workflow_stage", "initial"),
                    complexity_score=predicted_context.get("complexity_score", 0.5),
                    tool_recommendations=predicted_context.get("tool_recommendations", {}),
                    integration_requirements=predicted_context.get("integration_requirements", {}),
                    confidence_metrics=predicted_context.get("confidence_metrics", {})
                )
                
                await self.learning_engine.record_interaction(
                    query=query,
                    predicted_context=context_obj,
                    user_actions=[action],
                    outcome_success=(outcome == "success"),
                    time_to_completion=data.get("time_to_completion", 0.0)
                )
            
            self.stats["user_interactions"] += 1
            
            return {
                "type": "interaction_recorded",
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
            return {
                "type": "error",
                "error": f"Interaction recording failed: {str(e)}"
            }
    
    async def get_session_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get current session context."""
        try:
            session_id = data.get("session_id")
            
            if session_id and session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                
                return {
                    "type": "session_context_response",
                    "session_data": {
                        "query_count": len(session_data.get("queries", [])),
                        "recent_queries": session_data.get("queries", [])[-5:],
                        "current_stage": session_data.get("current_stage", "initial"),
                        "uploaded_files": session_data.get("uploaded_files", {}),
                        "session_duration": (datetime.now() - session_data.get("start_time", datetime.now())).total_seconds()
                    },
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "type": "session_context_response",
                    "session_data": None,
                    "session_id": session_id,
                    "message": "Session not found"
                }
                
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return {
                "type": "error",
                "error": f"Session context retrieval failed: {str(e)}"
            }
    
    async def get_bridge_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "type": "bridge_stats_response",
            "stats": self.stats,
            "active_sessions": len(self.active_sessions),
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_session(self, session_id: str, query: str, context):
        """Update session data with new query and context."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "start_time": datetime.now(),
                "queries": [],
                "contexts": [],
                "current_stage": "initial"
            }
        
        session = self.active_sessions[session_id]
        session["queries"].append(query)
        session["contexts"].append(context)
        session["current_stage"] = context.workflow_stage
        session["last_update"] = datetime.now()
    
    def _generate_tool_recommendations(self, domain: str, data_types: List[str], objectives: List[str]) -> Dict[str, float]:
        """Generate tool recommendations based on analysis context."""
        recommendations = {}
        
        # Domain-based recommendations
        if domain == "transcriptomics":
            if "scrna_seq" in data_types:
                recommendations.update({
                    "seurat": 0.9,
                    "scanpy": 0.85,
                    "cellranger": 0.8,
                    "monocle3": 0.75
                })
            elif "bulk_rnaseq" in data_types:
                recommendations.update({
                    "deseq2": 0.9,
                    "edger": 0.85,
                    "limma": 0.8
                })
        
        elif domain == "proteomics":
            recommendations.update({
                "maxquant": 0.9,
                "perseus": 0.85,
                "proteomaps": 0.8
            })
        
        elif domain == "genomics":
            recommendations.update({
                "gatk": 0.9,
                "samtools": 0.85,
                "bcftools": 0.8
            })
        
        # Objective-based adjustments
        for objective in objectives:
            if objective == "differential_expression":
                if "deseq2" in recommendations:
                    recommendations["deseq2"] += 0.05
                if "seurat" in recommendations:
                    recommendations["seurat"] += 0.05
            elif objective == "clustering":
                if "seurat" in recommendations:
                    recommendations["seurat"] += 0.05
                if "scanpy" in recommendations:
                    recommendations["scanpy"] += 0.05
        
        # Normalize scores
        for tool in recommendations:
            recommendations[tool] = min(recommendations[tool], 1.0)
        
        return recommendations
    
    def get_message_handlers(self) -> Dict[str, callable]:
        """Get all message handlers for integration with main bridge."""
        return {
            "analyze_context": self.analyze_query_context,
            "predict_workflow": self.predict_workflow_steps,
            "analyze_files": self.analyze_uploaded_files,
            "get_tool_recommendations": self.get_tool_recommendations,
            "record_interaction": self.record_user_interaction,
            "get_session_context": self.get_session_context,
            "get_routing_stats": self.get_bridge_stats
        }


def main():
    """Test function for the routing bridge."""
    print("Testing ElectronRoutingBridge...")
    
    bridge = ElectronRoutingBridge()
    print(f"Bridge initialized with {len(bridge.get_message_handlers())} handlers")
    
    # Test handlers
    handlers = bridge.get_message_handlers()
    print(f"Available handlers: {list(handlers.keys())}")
    
    print("Routing bridge ready for electron integration")


if __name__ == "__main__":
    main() 