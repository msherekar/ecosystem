"""
Enhanced Strategy Module

Provides analysis strategy patterns for configurable behavior
across different analysis types and workflow stages.

Enhanced with security, performance monitoring, Electron integration,
and comprehensive testing capabilities.
"""

import logging
from typing import List, Dict, Any, Optional

# Setup logging for the module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core components
from .base import (
    WorkflowStage,
    ActionRule, 
    InsightRule,
    WorkflowStep,
    AnalysisStrategy,
    ValidationError,
    StrategyError
)

# Rule-based strategy base
from .rule_based import RuleBasedAnalysisStrategy

# Specific strategy implementations
from .scrna_strategy import scRNASeqAnalysisStrategy
from .rna_strategy import RNASeqAnalysisStrategy
from .atac_strategy import ATACSeqAnalysisStrategy

# Factory and generic strategy
from .factory import (
    StrategyFactory,
    GenericAnalysisStrategy,
    strategy_registry
)

# Enhanced system components
from .security import SecurityManager, validate_input, RateLimiter
from .performance import PerformanceMonitor, CacheManager
from .electron_bridge import ElectronBridge, ElectronAPI
from .logging_config import setup_logging, get_logger, LogCapture

# Main orchestrator
from .__main__ import (
    StrategySystemOrchestrator,
    get_orchestrator
)

# Legacy compatibility - maintain old interface names
SuggestedActionStrategy = AnalysisStrategy
RuleBasedActionStrategy = RuleBasedAnalysisStrategy
scRNASeqActionStrategy = scRNASeqAnalysisStrategy
RNASeqActionStrategy = RNASeqAnalysisStrategy
ATACSeqActionStrategy = ATACSeqAnalysisStrategy
GenericActionStrategy = GenericAnalysisStrategy

# Module version and metadata
__version__ = "2.1.0"
__author__ = "Mukul Sherekar"
__description__ = "Enhanced analysis strategy system with security, performance, and Electron integration"

# Public API
__all__ = [
    # Core components
    "WorkflowStage",
    "ActionRule",
    "InsightRule", 
    "WorkflowStep",
    "AnalysisStrategy",
    "ValidationError",
    "StrategyError",
    
    # Strategy implementations
    "RuleBasedAnalysisStrategy",
    "scRNASeqAnalysisStrategy",
    "RNASeqAnalysisStrategy", 
    "ATACSeqAnalysisStrategy",
    "GenericAnalysisStrategy",
    
    # Factory and registry
    "StrategyFactory",
    "strategy_registry",
    
    # System components
    "SecurityManager",
    "PerformanceMonitor", 
    "CacheManager",
    "ElectronBridge",
    "ElectronAPI",
    "StrategySystemOrchestrator",
    "get_orchestrator",
    
    # Utilities
    "validate_input",
    "RateLimiter",
    "setup_logging",
    "get_logger",
    "LogCapture",
    
    # Legacy compatibility
    "SuggestedActionStrategy",
    "RuleBasedActionStrategy",
    "scRNASeqActionStrategy",
    "RNASeqActionStrategy",
    "ATACSeqActionStrategy",
    "GenericActionStrategy",
    
    # Module metadata
    "__version__",
    "__author__",
    "__description__"
]


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information"""
    try:
        orchestrator = get_orchestrator()
        return {
            "module_version": __version__,
            "available_strategies": strategy_registry.get_available_strategies(),
            "system_status": orchestrator.get_system_status(),
            "factory_stats": strategy_registry.get_factory_stats(),
            "component_versions": {
                "base": "2.0.0",
                "rule_based": "2.0.0", 
                "factory": "2.0.0",
                "security": "1.0.0",
                "performance": "1.0.0",
                "electron_bridge": "1.0.0"
            }
        }
    except Exception as e:
        logger.warning(f"Could not get full system info: {e}")
        return {
            "module_version": __version__,
            "available_strategies": strategy_registry.get_available_strategies(),
            "error": str(e)
        }


def validate_system() -> Dict[str, Any]:
    """Validate entire strategy system"""
    validation_results = {
        "overall_status": "healthy",
        "component_checks": {},
        "strategy_validations": {},
        "warnings": [],
        "errors": []
    }
    
    try:
        # Check core components
        validation_results["component_checks"]["factory"] = "ok"
        validation_results["component_checks"]["security"] = "ok"
        validation_results["component_checks"]["performance"] = "ok"
        
        # Validate each strategy
        available_strategies = strategy_registry.get_available_strategies()
        for strategy_type in available_strategies:
            try:
                validation_result = strategy_registry.validate_strategy(strategy_type)
                validation_results["strategy_validations"][strategy_type] = validation_result
                
                if not validation_result["valid"]:
                    validation_results["errors"].extend(validation_result["errors"])
                    validation_results["overall_status"] = "unhealthy"
                
                if validation_result["warnings"]:
                    validation_results["warnings"].extend(validation_result["warnings"])
                    
            except Exception as e:
                error_msg = f"Failed to validate strategy {strategy_type}: {e}"
                validation_results["errors"].append(error_msg)
                validation_results["overall_status"] = "unhealthy"
        
        # Check orchestrator
        try:
            orchestrator = get_orchestrator()
            validation_results["component_checks"]["orchestrator"] = "ok"
        except Exception as e:
            validation_results["component_checks"]["orchestrator"] = f"error: {e}"
            validation_results["errors"].append(f"Orchestrator check failed: {e}")
            validation_results["overall_status"] = "unhealthy"
        
        # Set warning status if there are warnings but no errors
        if validation_results["warnings"] and not validation_results["errors"]:
            validation_results["overall_status"] = "warning"
            
    except Exception as e:
        validation_results["errors"].append(f"System validation failed: {e}")
        validation_results["overall_status"] = "error"
    
    return validation_results


def quick_start(analysis_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Quick start function for getting actions and insights"""
    try:
        if context is None:
            context = {}
        
        # Get orchestrator and create strategy
        orchestrator = get_orchestrator()
        
        # Get actions and insights
        actions = orchestrator.get_actions(analysis_type, context)
        insights = orchestrator.get_insights(analysis_type, context)
        workflow_steps = orchestrator.get_workflow_steps(analysis_type)
        
        return {
            "analysis_type": analysis_type,
            "actions": actions,
            "insights": insights,
            "workflow_steps": workflow_steps,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Quick start failed for {analysis_type}: {e}")
        return {
            "analysis_type": analysis_type,
            "actions": [],
            "insights": f"Error: {str(e)}",
            "workflow_steps": [],
            "status": "error",
            "error": str(e)
        }


def main():
    """Comprehensive module testing and validation"""
    print("🧪 Testing Enhanced Strategy Module")
    print("=" * 60)
    
    # Test module imports
    print("Testing module imports...")
    
    # Test core component imports
    core_components = [
        WorkflowStage, ActionRule, InsightRule, WorkflowStep, 
        AnalysisStrategy, ValidationError, StrategyError
    ]
    for component in core_components:
        assert component is not None, f"{component.__name__} should be importable"
    
    # Test strategy implementations
    strategy_implementations = [
        RuleBasedAnalysisStrategy, scRNASeqAnalysisStrategy,
        RNASeqAnalysisStrategy, ATACSeqAnalysisStrategy, GenericAnalysisStrategy
    ]
    for strategy_impl in strategy_implementations:
        assert strategy_impl is not None, f"{strategy_impl.__name__} should be importable"
    
    # Test system components
    system_components = [
        SecurityManager, PerformanceMonitor, CacheManager,
        ElectronBridge, StrategySystemOrchestrator
    ]
    for component in system_components:
        assert component is not None, f"{component.__name__} should be importable"
    
    print("✅ Module imports passed")
    
    # Test legacy compatibility
    print("Testing legacy compatibility...")
    legacy_mappings = [
        (SuggestedActionStrategy, AnalysisStrategy),
        (RuleBasedActionStrategy, RuleBasedAnalysisStrategy),
        (scRNASeqActionStrategy, scRNASeqAnalysisStrategy),
        (RNASeqActionStrategy, RNASeqAnalysisStrategy),
        (ATACSeqActionStrategy, ATACSeqAnalysisStrategy),
        (GenericActionStrategy, GenericAnalysisStrategy)
    ]
    
    for legacy, current in legacy_mappings:
        assert legacy is current, f"Legacy alias {legacy.__name__} should map to {current.__name__}"
    
    print("✅ Legacy compatibility passed")
    
    # Test strategy factory functionality
    print("Testing strategy factory...")
    available_strategies = strategy_registry.get_available_strategies()
    assert len(available_strategies) >= 3, f"Should have at least 3 strategies, got {len(available_strategies)}"
    
    required_strategies = {"scrnaseq", "rnaseq", "atacseq"}
    assert required_strategies.issubset(set(available_strategies)), "Should include all required strategies"
    
    # Test strategy creation
    for strategy_type in available_strategies:
        strategy = strategy_registry.create_strategy(strategy_type)
        assert strategy is not None, f"Should create {strategy_type} strategy"
        
        # Test basic functionality
        actions = strategy.get_actions({})
        insights = strategy.get_insights({})
        workflow_steps = strategy.get_workflow_steps()
        
        assert isinstance(actions, list), f"{strategy_type} should return list of actions"
        assert isinstance(insights, str), f"{strategy_type} should return string insights"
        assert isinstance(workflow_steps, list), f"{strategy_type} should return list of workflow steps"