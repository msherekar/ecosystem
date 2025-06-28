"""
Strategy System Main Orchestrator

Central orchestrator for the bioinformatics analysis strategy system.
Provides unified interface for Electron integration, API endpoints,
and comprehensive system management.
"""

import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import asyncio
from datetime import datetime

# Core strategy imports
from .factory import StrategyFactory, strategy_registry
from .base import WorkflowStage, AnalysisStrategy
from .security import SecurityManager, validate_input
from .electron_bridge import ElectronBridge
from .performance import PerformanceMonitor
from .logging_config import setup_logging

# Version and metadata
__version__ = "2.1.0"
__author__ = "Mukul Sherekar"


class StrategySystemOrchestrator:
    """Main orchestrator for the strategy system"""
    
    def __init__(self, config_path: Optional[str] = None, debug: bool = False):
        self.config = self._load_config(config_path)
        self.debug = debug
        self.logger = setup_logging(debug=debug)
        self.security_manager = SecurityManager()
        self.electron_bridge = ElectronBridge()
        self.performance_monitor = PerformanceMonitor()
        self.active_strategies: Dict[str, AnalysisStrategy] = {}
        
        # Initialize system
        self._initialize_system()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load system configuration"""
        default_config = {
            "security": {
                "max_file_size": 100 * 1024 * 1024,  # 100MB
                "allowed_extensions": [".h5ad", ".csv", ".tsv", ".xlsx", ".txt"],
                "sanitize_inputs": True
            },
            "performance": {
                "max_concurrent_analyses": 3,
                "cache_size": 50,
                "timeout_seconds": 300
            },
            "electron": {
                "port": 8765,
                "host": "localhost",
                "auto_launch": True
            },
            "logging": {
                "level": "INFO",
                "max_file_size": "10MB",
                "backup_count": 5
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
        
        return default_config
    
    def _initialize_system(self):
        """Initialize all system components"""
        self.logger.info("Initializing Strategy System Orchestrator")
        
        # Validate system dependencies
        self._validate_dependencies()
        
        # Initialize performance monitoring
        self.performance_monitor.start()
        
        # Initialize Electron bridge if configured
        if self.config["electron"]["auto_launch"]:
            self.electron_bridge.initialize(
                host=self.config["electron"]["host"],
                port=self.config["electron"]["port"]
            )
        
        self.logger.info("System initialization complete")
    
    def _validate_dependencies(self):
        """Validate system dependencies and requirements"""
        required_strategies = ["scrnaseq", "rnaseq", "atacseq"]
        available_strategies = strategy_registry.get_available_strategies()
        
        missing_strategies = set(required_strategies) - set(available_strategies)
        if missing_strategies:
            raise RuntimeError(f"Missing required strategies: {missing_strategies}")
        
        self.logger.info(f"Available strategies: {available_strategies}")
    
    @validate_input
    def create_strategy(self, analysis_type: str, session_id: Optional[str] = None) -> AnalysisStrategy:
        """Create and cache a strategy instance"""
        # Sanitize input
        analysis_type = self.security_manager.sanitize_string(analysis_type)
        
        # Create strategy
        strategy = strategy_registry.create_strategy(analysis_type)
        
        # Cache for session management
        if session_id:
            self.active_strategies[session_id] = strategy
        
        self.logger.info(f"Created strategy: {analysis_type} for session: {session_id}")
        return strategy
    
    @validate_input
    def get_actions(self, analysis_type: str, context: Dict[str, Any], 
                   session_id: Optional[str] = None) -> List[str]:
        """Get suggested actions for analysis context"""
        # Validate and sanitize context
        context = self.security_manager.sanitize_context(context)
        
        # Get or create strategy
        if session_id and session_id in self.active_strategies:
            strategy = self.active_strategies[session_id]
        else:
            strategy = self.create_strategy(analysis_type, session_id)
        
        # Monitor performance
        with self.performance_monitor.measure("get_actions"):
            actions = strategy.get_actions(context)
        
        return actions
    
    @validate_input
    def get_insights(self, analysis_type: str, context: Dict[str, Any],
                    session_id: Optional[str] = None) -> str:
        """Get analysis insights for context"""
        # Validate and sanitize context
        context = self.security_manager.sanitize_context(context)
        
        # Get or create strategy
        if session_id and session_id in self.active_strategies:
            strategy = self.active_strategies[session_id]
        else:
            strategy = self.create_strategy(analysis_type, session_id)
        
        # Monitor performance
        with self.performance_monitor.measure("get_insights"):
            insights = strategy.get_insights(context)
        
        return insights
    
    def get_workflow_steps(self, analysis_type: str) -> List[Dict[str, Any]]:
        """Get workflow steps for analysis type"""
        strategy = strategy_registry.create_strategy(analysis_type)
        workflow_steps = strategy.get_workflow_steps()
        
        # Convert to JSON-serializable format for Electron
        return [
            {
                "key": step.key,
                "title": step.title,
                "description": step.description,
                "stage": step.stage.value,
                "dependencies": step.dependencies or [],
                "optional": step.optional
            }
            for step in workflow_steps
        ]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "version": __version__,
            "uptime": self.performance_monitor.get_uptime(),
            "available_strategies": strategy_registry.get_available_strategies(),
            "active_sessions": len(self.active_strategies),
            "performance_stats": self.performance_monitor.get_stats(),
            "memory_usage": self.performance_monitor.get_memory_usage(),
            "security_status": self.security_manager.get_status()
        }
    
    def cleanup_session(self, session_id: str):
        """Clean up resources for a session"""
        if session_id in self.active_strategies:
            del self.active_strategies[session_id]
            self.logger.info(f"Cleaned up session: {session_id}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {}
        }
        
        # Check strategy factory
        try:
            test_strategy = strategy_registry.create_strategy("scrnaseq")
            health_status["checks"]["strategy_factory"] = "ok"
        except Exception as e:
            health_status["checks"]["strategy_factory"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Check Electron bridge
        health_status["checks"]["electron_bridge"] = self.electron_bridge.get_status()
        
        # Check performance monitor
        health_status["checks"]["performance_monitor"] = "ok" if self.performance_monitor.is_running() else "warning"
        
        return health_status
    
    def shutdown(self):
        """Graceful system shutdown"""
        self.logger.info("Initiating system shutdown")
        
        # Stop performance monitoring
        self.performance_monitor.stop()
        
        # Close Electron bridge
        self.electron_bridge.cleanup()
        
        # Clear active strategies
        self.active_strategies.clear()
        
        self.logger.info("System shutdown complete")


# Global orchestrator instance
_orchestrator_instance: Optional[StrategySystemOrchestrator] = None


def get_orchestrator(config_path: Optional[str] = None, debug: bool = False) -> StrategySystemOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = StrategySystemOrchestrator(config_path, debug)
    return _orchestrator_instance


# CLI interface functions
def cli_create_strategy(args):
    """CLI command to create strategy"""
    orchestrator = get_orchestrator(debug=args.debug)
    strategy = orchestrator.create_strategy(args.analysis_type)
    print(f"Created {args.analysis_type} strategy: {strategy.__class__.__name__}")


def cli_get_actions(args):
    """CLI command to get actions"""
    orchestrator = get_orchestrator(debug=args.debug)
    
    # Parse context from JSON string or file
    if args.context_file:
        with open(args.context_file, 'r') as f:
            context = json.load(f)
    else:
        context = json.loads(args.context) if args.context else {}
    
    actions = orchestrator.get_actions(args.analysis_type, context)
    print("Suggested Actions:")
    for i, action in enumerate(actions, 1):
        print(f"{i}. {action}")


def cli_system_status(args):
    """CLI command to get system status"""
    orchestrator = get_orchestrator(debug=args.debug)
    status = orchestrator.get_system_status()
    print(json.dumps(status, indent=2))


async def cli_health_check(args):
    """CLI command to perform health check"""
    orchestrator = get_orchestrator(debug=args.debug)
    health = await orchestrator.health_check()
    print(json.dumps(health, indent=2))


def main():
    """Main entry point for the strategy system"""
    parser = argparse.ArgumentParser(description="Bioinformatics Analysis Strategy System")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--version", action="version", version=f"Strategy System {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create strategy command
    create_parser = subparsers.add_parser("create", help="Create a strategy")
    create_parser.add_argument("analysis_type", help="Analysis type (scrnaseq, rnaseq, atacseq)")
    create_parser.set_defaults(func=cli_create_strategy)
    
    # Get actions command
    actions_parser = subparsers.add_parser("actions", help="Get suggested actions")
    actions_parser.add_argument("analysis_type", help="Analysis type")
    actions_parser.add_argument("--context", help="Context as JSON string")
    actions_parser.add_argument("--context-file", help="Context from JSON file")
    actions_parser.set_defaults(func=cli_get_actions)
    
    # System status command
    status_parser = subparsers.add_parser("status", help="Get system status")
    status_parser.set_defaults(func=cli_system_status)
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Perform health check")
    health_parser.set_defaults(func=lambda args: asyncio.run(cli_health_check(args)))
    
    # Start server command
    server_parser = subparsers.add_parser("server", help="Start Electron bridge server")
    server_parser.add_argument("--port", type=int, default=8765, help="Server port")
    server_parser.add_argument("--host", default="localhost", help="Server host")
    
    args = parser.parse_args()
    
    if args.command:
        try:
            if args.command == "server":
                orchestrator = get_orchestrator(config_path=args.config, debug=args.debug)
                orchestrator.electron_bridge.start_server(host=args.host, port=args.port)
            else:
                args.func(args)
        except Exception as e:
            print(f"Error: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        # Interactive mode
        print(f"Strategy System {__version__}")
        print("Use --help for available commands")
        
        # Start interactive session
        orchestrator = get_orchestrator(config_path=args.config, debug=args.debug)
        print(f"Available strategies: {strategy_registry.get_available_strategies()}")
        print("System ready!")


if __name__ == "__main__":
    def test_static_orchestrator():
        """Static tests for orchestrator functionality"""
        print("Running static orchestrator tests...")
        
        # Test configuration loading
        orchestrator = StrategySystemOrchestrator()
        assert orchestrator.config is not None, "Config should be loaded"
        assert "security" in orchestrator.config, "Security config should exist"
        
        # Test strategy creation
        strategy = orchestrator.create_strategy("scrnaseq")
        assert strategy is not None, "Strategy should be created"
        
        # Test action generation
        actions = orchestrator.get_actions("scrnaseq", {})
        assert isinstance(actions, list), "Actions should be a list"
        assert len(actions) > 0, "Should have at least one action"
        
        # Test workflow steps
        workflow_steps = orchestrator.get_workflow_steps("scrnaseq")
        assert isinstance(workflow_steps, list), "Workflow steps should be a list"
        assert len(workflow_steps) > 0, "Should have workflow steps"
        
        # Test system status
        status = orchestrator.get_system_status()
        assert isinstance(status, dict), "Status should be a dict"
        assert "version" in status, "Status should include version"
        
        print("✅ Static orchestrator tests passed!")
    
    def test_dynamic_orchestrator():
        """Dynamic tests for orchestrator functionality"""
        print("Running dynamic orchestrator tests...")
        
        orchestrator = StrategySystemOrchestrator(debug=True)
        
        # Test session management
        session_id = "test_session_123"
        strategy1 = orchestrator.create_strategy("scrnaseq", session_id)
        strategy2 = orchestrator.active_strategies.get(session_id)
        assert strategy1 is strategy2, "Session strategy should be cached"
        
        # Test context sanitization
        unsafe_context = {
            "data_uploaded": True,
            "script_tag": "<script>alert('xss')</script>",
            "sql_injection": "'; DROP TABLE users; --"
        }
        actions = orchestrator.get_actions("scrnaseq", unsafe_context, session_id)
        assert isinstance(actions, list), "Should handle unsafe context gracefully"
        
        # Test performance monitoring
        import time
        start_time = time.time()
        for _ in range(10):
            orchestrator.get_actions("scrnaseq", {"data_uploaded": True})
        elapsed = time.time() - start_time
        assert elapsed < 1.0, "Performance should be acceptable"
        
        # Test cleanup
        orchestrator.cleanup_session(session_id)
        assert session_id not in orchestrator.active_strategies, "Session should be cleaned up"
        
        # Test health check
        async def test_health():
            health = await orchestrator.health_check()
            assert "status" in health, "Health check should include status"
            assert "checks" in health, "Health check should include checks"
        
        asyncio.run(test_health())
        
        print("✅ Dynamic orchestrator tests passed!")
    
    def run_main_tests():
        """Run all orchestrator tests"""
        print("🧪 Testing Strategy System Orchestrator")
        print("=" * 50)
        
        try:
            test_static_orchestrator()
            test_dynamic_orchestrator()
            print("\n🎉 All orchestrator tests passed!")
            return True
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run tests when executed directly
    if not run_main_tests():
        sys.exit(1)
    
    # Run main CLI if no test failures
    main()