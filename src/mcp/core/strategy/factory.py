"""
Strategy Factory and Generic Strategy

Enhanced factory for creating analysis strategies with
plugin support, caching, and configuration management.
"""

import logging
import threading
from typing import List, Dict, Type, Optional, Any
from pathlib import Path
import importlib.util
import inspect

from .base import AnalysisStrategy, WorkflowStage, WorkflowStep, ValidationError
from .rule_based import RuleBasedAnalysisStrategy
from .performance import CacheManager

logger = logging.getLogger(__name__)


class GenericAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Generic fallback strategy for unknown analysis types"""
    
    def __init__(self, analysis_type: str = "generic"):
        super().__init__(analysis_type)
        self.metadata = {
            "description": "Generic analysis strategy for unknown types",
            "capabilities": ["basic_workflow", "file_upload", "progress_tracking"],
            "limitations": ["limited_analysis_options", "no_specialized_insights"]
        }
    
    def _initialize_rules(self):
        """Initialize generic rules for unknown analysis types"""
        # Basic workflow action rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload data files for analysis",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Upload your analysis data files",
            estimated_time=5
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and 
                                 not ctx.get("analysis_configured", False)),
            action="Configure analysis parameters",
            priority=8,
            stage=WorkflowStage.PREPROCESSING,
            description="Set up analysis configuration",
            estimated_time=10
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("analysis_configured", False) and
                                 not ctx.get("analysis_started", False)),
            action="Begin analysis workflow",
            priority=7,
            stage=WorkflowStage.ANALYSIS,
            description="Start the analysis process",
            estimated_time=30
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("analysis_started", False) and 
                                 not ctx.get("analysis_complete", False)),
            action="Monitor analysis progress",
            priority=5,
            stage=WorkflowStage.ANALYSIS,
            description="Check analysis status and progress",
            estimated_time=2
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("analysis_complete", False) and
                                 not ctx.get("results_exported", False)),
            action="Export analysis results",
            priority=6,
            stage=WorkflowStage.EXPORT,
            description="Save and export your results",
            estimated_time=5
        )
        
        # Basic insight rules
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False),
            insight_generator=lambda ctx: "Data uploaded and ready for analysis",
            priority=8,
            category="data_status",
            severity="success"
        )
        
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("analysis_configured", False),
            insight_generator=lambda ctx: "Analysis parameters configured",
            priority=7,
            category="configuration",
            severity="info"
        )
        
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("analysis_started", False),
            insight_generator=lambda ctx: "Analysis workflow initiated",
            priority=6,
            category="progress",
            severity="info",
            actionable=True
        )
        
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("analysis_complete", False),
            insight_generator=lambda ctx: "Analysis workflow completed successfully",
            priority=9,
            category="completion",
            severity="success"
        )
        
        # Define basic workflow steps
        self.workflow_steps = [
            WorkflowStep(
                key="data_upload",
                title="Data Upload",
                description="Upload analysis data files",
                stage=WorkflowStage.DATA_UPLOAD,
                estimated_time=5,
                complexity="low"
            ),
            WorkflowStep(
                key="configuration",
                title="Configuration",
                description="Configure analysis parameters",
                stage=WorkflowStage.PREPROCESSING,
                dependencies=["data_upload"],
                estimated_time=10,
                complexity="medium"
            ),
            WorkflowStep(
                key="analysis",
                title="Analysis",
                description="Perform data analysis",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["configuration"],
                estimated_time=30,
                complexity="high"
            ),
            WorkflowStep(
                key="visualization",
                title="Visualization",
                description="Create visualizations",
                stage=WorkflowStage.VISUALIZATION,
                dependencies=["analysis"],
                estimated_time=15,
                complexity="medium",
                optional=True
            ),
            WorkflowStep(
                key="export",
                title="Export Results",
                description="Export analysis results",
                stage=WorkflowStage.EXPORT,
                dependencies=["analysis"],
                estimated_time=5,
                complexity="low"
            )
        ]


class StrategyFactory:
    """Enhanced factory for creating and managing analysis strategies"""
    
    def __init__(self):
        self._strategies: Dict[str, Type[AnalysisStrategy]] = {}
        self._strategy_cache = CacheManager(max_size=50)
        self._plugin_directories: List[Path] = []
        self._lock = threading.RLock()
        self._metadata: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in strategies
        self._register_builtin_strategies()
        
        # Load external plugins
        self._load_plugins()
    
    def _register_builtin_strategies(self):
        """Register built-in strategy implementations"""
        try:
            # Import specific strategies
            from .scrna_strategy import scRNASeqAnalysisStrategy
            from .rna_strategy import RNASeqAnalysisStrategy
            from .atac_strategy import ATACSeqAnalysisStrategy
            
            self._strategies.update({
                "scrnaseq": scRNASeqAnalysisStrategy,
                "rnaseq": RNASeqAnalysisStrategy,
                "atacseq": ATACSeqAnalysisStrategy
            })
            
            # Add metadata for built-in strategies
            self._metadata.update({
                "scrnaseq": {
                    "name": "Single-cell RNA-seq",
                    "description": "Strategy for single-cell RNA sequencing analysis",
                    "version": "1.0.0",
                    "author": "Strategy Team",
                    "data_types": ["h5ad", "csv", "tsv"],
                    "capabilities": ["qc", "clustering", "differential_expression", "visualization"]
                },
                "rnaseq": {
                    "name": "Bulk RNA-seq",
                    "description": "Strategy for bulk RNA sequencing analysis",
                    "version": "1.0.0",
                    "author": "Strategy Team",
                    "data_types": ["csv", "tsv", "xlsx"],
                    "capabilities": ["deseq2", "go_enrichment", "visualization"]
                },
                "atacseq": {
                    "name": "ATAC-seq",
                    "description": "Strategy for chromatin accessibility analysis",
                    "version": "1.0.0",
                    "author": "Strategy Team",
                    "data_types": ["bed", "bam", "csv"],
                    "capabilities": ["peak_calling", "differential_accessibility", "motif_analysis"]
                }
            })
            
            logger.info(f"Registered {len(self._strategies)} built-in strategies")
            
        except ImportError as e:
            logger.warning(f"Could not import some built-in strategies: {e}")
    
    def _load_plugins(self):
        """Load strategy plugins from configured directories"""
        plugin_dir = Path("plugins/strategies")
        if plugin_dir.exists():
            self.add_plugin_directory(plugin_dir)
    
    def add_plugin_directory(self, directory: Path):
        """Add directory to search for strategy plugins"""
        if not directory.exists():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return
        
        self._plugin_directories.append(directory)
        
        # Load plugins from this directory
        for plugin_file in directory.glob("*_strategy.py"):
            try:
                self._load_plugin_file(plugin_file)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
    
    def _load_plugin_file(self, plugin_file: Path):
        """Load strategy from plugin file"""
        spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find strategy classes in module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, AnalysisStrategy) and 
                    obj != AnalysisStrategy and
                    obj != RuleBasedAnalysisStrategy):
                    
                    # Register strategy
                    strategy_name = getattr(obj, 'STRATEGY_NAME', name.lower())
                    self.register_strategy(strategy_name, obj)
                    logger.info(f"Loaded plugin strategy: {strategy_name}")
    
    def create_strategy(self, analysis_type: str, use_cache: bool = True) -> AnalysisStrategy:
        """Create strategy instance with caching support"""
        if not analysis_type:
            raise ValidationError("Analysis type cannot be empty")
        
        analysis_type_lower = analysis_type.lower()
        
        # Check cache first
        if use_cache:
            cached_strategy = self._strategy_cache.get(analysis_type_lower)
            if cached_strategy:
                return cached_strategy
        
        with self._lock:
            strategy_class = self._strategies.get(analysis_type_lower)
            
            if strategy_class:
                try:
                    strategy = strategy_class()
                    logger.debug(f"Created strategy instance: {analysis_type}")
                except Exception as e:
                    logger.error(f"Failed to create strategy {analysis_type}: {e}")
                    # Fall back to generic strategy
                    strategy = GenericAnalysisStrategy(analysis_type)
            else:
                # Create generic strategy for unknown types
                strategy = GenericAnalysisStrategy(analysis_type)
                logger.info(f"Using generic strategy for unknown type: {analysis_type}")
            
            # Cache the strategy if enabled
            if use_cache:
                self._strategy_cache.put(analysis_type_lower, strategy)
            
            return strategy
    
    def register_strategy(self, analysis_type: str, strategy_class: Type[AnalysisStrategy],
                         metadata: Optional[Dict[str, Any]] = None):
        """Register new strategy with metadata"""
        if not analysis_type:
            raise ValidationError("Analysis type cannot be empty")
        
        if not inspect.isclass(strategy_class) or not issubclass(strategy_class, AnalysisStrategy):
            raise ValidationError("Strategy class must inherit from AnalysisStrategy")
        
        with self._lock:
            analysis_type_lower = analysis_type.lower()
            self._strategies[analysis_type_lower] = strategy_class
            
            # Store metadata
            if metadata:
                self._metadata[analysis_type_lower] = metadata
            
            # Clear cache for this strategy type
            self._strategy_cache.put(analysis_type_lower, None)
            
            logger.info(f"Registered strategy: {analysis_type}")
    
    def unregister_strategy(self, analysis_type: str):
        """Unregister a strategy"""
        with self._lock:
            analysis_type_lower = analysis_type.lower()
            if analysis_type_lower in self._strategies:
                del self._strategies[analysis_type_lower]
                
                # Remove metadata
                if analysis_type_lower in self._metadata:
                    del self._metadata[analysis_type_lower]
                
                # Clear cache
                self._strategy_cache.put(analysis_type_lower, None)
                
                logger.info(f"Unregistered strategy: {analysis_type}")
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategy types"""
        with self._lock:
            return list(self._strategies.keys())
    
    def is_strategy_registered(self, analysis_type: str) -> bool:
        """Check if strategy is registered"""
        return analysis_type.lower() in self._strategies
    
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all registered strategies"""
        return self._metadata.copy()
    
    def clear_cache(self):
        """Clear strategy cache"""
        self._strategy_cache.clear()
        logger.info("Strategy cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self._strategy_cache.get_stats()
    
    def validate_strategy_class(self, strategy_class: Type[AnalysisStrategy]) -> bool:
        """Validate that strategy class is properly implemented"""
        required_methods = ['get_actions', 'get_insights', 'get_workflow_steps']
        
        for method_name in required_methods:
            if not hasattr(strategy_class, method_name):
                return False
            
            method = getattr(strategy_class, method_name)
            if not callable(method):
                return False
        
        return True
    
    def get_strategies_by_capability(self, capability: str) -> List[str]:
        """Get strategies that support a specific capability"""
        matching_strategies = []
        
        for strategy_type, metadata in self._metadata.items():
            capabilities = metadata.get('capabilities', [])
            if capability in capabilities:
                matching_strategies.append(strategy_type)
        
        return matching_strategies
    
    def get_strategies_by_data_type(self, data_type: str) -> List[str]:
        """Get strategies that support a specific data type"""
        matching_strategies = []
        
        for strategy_type, metadata in self._metadata.items():
            data_types = metadata.get('data_types', [])
            if data_type in data_types:
                matching_strategies.append(strategy_type)
        
        return matching_strategies


# Global strategy registry instance
strategy_registry = StrategyFactory()


def main():
    """Test strategy factory functionality with comprehensive validation"""
    print("🧪 Testing Strategy Factory")
    print("=" * 50)
    
    # Test factory initialization
    print("Testing factory initialization...")
    factory = StrategyFactory()
    assert len(factory.get_available_strategies()) >= 3, "Should have built-in strategies"
    print("✅ Factory initialization passed")
    
    # Test strategy creation
    print("Testing strategy creation...")
    available_strategies = factory.get_available_strategies()
    
    for strategy_type in available_strategies:
        strategy = factory.create_strategy(strategy_type)
        assert strategy is not None, f"Should create {strategy_type} strategy"
        assert hasattr(strategy, 'get_actions'), f"{strategy_type} should have get_actions"
        assert hasattr(strategy, 'get_insights'), f"{strategy_type} should have get_insights"
        assert hasattr(strategy, 'get_workflow_steps'), f"{strategy_type} should have get_workflow_steps"
        print(f"✅ Created {strategy_type} strategy successfully")
    
    # Test generic strategy for unknown type
    print("Testing generic strategy fallback...")
    unknown_strategy = factory.create_strategy("unknown_analysis_type")
    assert isinstance(unknown_strategy, GenericAnalysisStrategy), "Should return GenericAnalysisStrategy"
    assert unknown_strategy.analysis_type == "unknown_analysis_type", "Should preserve analysis type"
    
    # Test generic strategy functionality
    generic_actions = unknown_strategy.get_actions({})
    assert len(generic_actions) > 0, "Generic strategy should have actions"
    assert any("Upload data files" in action for action in generic_actions), "Should suggest data upload"
    
    generic_workflow = unknown_strategy.get_workflow_steps()
    assert len(generic_workflow) >= 3, "Generic strategy should have workflow steps"
    print("✅ Generic strategy tests passed")
    
    # Test caching
    print("Testing strategy caching...")
    strategy1 = factory.create_strategy("scrnaseq", use_cache=True)
    strategy2 = factory.create_strategy("scrnaseq", use_cache=True)
    
    cache_stats = factory.get_cache_stats()
    assert cache_stats["hit_count"] > 0, "Should have cache hits"
    print("✅ Caching tests passed")
    
    # Test strategy registration
    print("Testing strategy registration...")
    
    class CustomTestStrategy(RuleBasedAnalysisStrategy):
        STRATEGY_NAME = "custom_test"
        
        def _initialize_rules(self):
            self.add_action_rule(
                condition=lambda ctx: True,
                action="Custom test action",
                priority=1
            )
    
    # Test registration
    initial_count = len(factory.get_available_strategies())
    custom_metadata = {
        "name": "Custom Test Strategy",
        "description": "A test strategy for validation",
        "version": "1.0.0",
        "capabilities": ["testing"]
    }
    
    factory.register_strategy("custom_test", CustomTestStrategy, custom_metadata)
    
    new_count = len(factory.get_available_strategies())
    assert new_count == initial_count + 1, "Should increase strategy count"
    assert "custom_test" in factory.get_available_strategies(), "Should include new strategy"
    assert factory.is_strategy_registered("custom_test"), "Should confirm registration"
    
    # Test metadata retrieval
    retrieved_metadata = factory.get_strategy_metadata("custom_test")
    assert retrieved_metadata == custom_metadata, "Should retrieve correct metadata"
    
    # Test custom strategy creation
    custom_strategy = factory.create_strategy("custom_test")
    assert isinstance(custom_strategy, CustomTestStrategy), "Should create custom strategy"
    print("✅ Strategy registration tests passed")
    
    # Test strategy search by capabilities
    print("Testing strategy search functionality...")
    testing_strategies = factory.get_strategies_by_capability("testing")
    assert "custom_test" in testing_strategies, "Should find strategy by capability"
    
    # Test validation
    print("Testing strategy validation...")
    assert factory.validate_strategy_class(CustomTestStrategy), "Valid strategy should pass validation"
    
    class InvalidStrategy:
        pass
    
    assert not factory.validate_strategy_class(InvalidStrategy), "Invalid strategy should fail validation"
    print("✅ Strategy validation tests passed")
    
    # Test unregistration
    print("Testing strategy unregistration...")
    factory.unregister_strategy("custom_test")
    final_count = len(factory.get_available_strategies())
    assert final_count == initial_count, "Should decrease strategy count"
    assert not factory.is_strategy_registered("custom_test"), "Should confirm unregistration"
    print("✅ Strategy unregistration tests passed")
    
    # Test case insensitivity
    print("Testing case insensitivity...")
    scrna_upper = factory.create_strategy("SCRNASEQ")
    scrna_lower = factory.create_strategy("scrnaseq")
    assert type(scrna_upper) == type(scrna_lower), "Should be case insensitive"
    print("✅ Case insensitivity tests passed")
    
    # Test error handling
    print("Testing error handling...")
    try:
        factory.create_strategy("")
        assert False, "Should reject empty strategy type"
    except ValidationError:
        pass  # Expected
    
    try:
        factory.register_strategy("", CustomTestStrategy)
        assert False, "Should reject empty strategy name"
    except ValidationError:
        pass  # Expected
    
    try:
        factory.register_strategy("test", InvalidStrategy)
        assert False, "Should reject invalid strategy class"
    except ValidationError:
        pass  # Expected
    
    print("✅ Error handling tests passed")
    
    # Test global registry
    print("Testing global registry...")
    global_strategies = strategy_registry.get_available_strategies()
    factory_strategies = factory.get_available_strategies()
    assert len(global_strategies) >= len(factory_strategies), "Global registry should have strategies"
    print("✅ Global registry tests passed")
    
    print("\n🎉 All factory tests passed!")
    return True


if __name__ == "__main__":
    def test_static_factory():
        """Static tests for factory functionality"""
        print("Running static factory tests...")
        
        factory = StrategyFactory()
        
        # Test initial state
        strategies = factory.get_available_strategies()
        assert len(strategies) > 0, "Should have registered strategies"
        
        # Test metadata structure
        all_metadata = factory.get_all_metadata()
        assert isinstance(all_metadata, dict), "Metadata should be a dictionary"
        
        print("✅ Static factory tests passed!")
    
    def test_dynamic_factory():
        """Dynamic tests for factory functionality"""
        print("Running dynamic factory tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic factory tests passed!")
    
    # Run all tests
    test_static_factory()
    test_dynamic_factory()