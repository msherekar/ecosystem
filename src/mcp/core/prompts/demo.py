"""
Enhanced Domain Prompts System - Demonstration Coordinator

Orchestrates interactive demos with Electron integration, security validation,
and scalable execution. Provides both programmatic and UI-friendly interfaces.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directories for imports if needed
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .demo_core import DemoRunner, DemoConfig, DemoResult, DemoProgressReporter
from .demo_scenarios import (
    BasicUsageDemoScenario, SearchAndFilteringDemoScenario, 
    SystemManagementDemoScenario
)
from .security import SecurityValidator, SecurityLevel
from .events import get_event_emitter, emit_system_event, emit_ui_update
from .performance import get_performance_monitor

import logging
logger = logging.getLogger(__name__)


class EnhancedDemoCoordinator:
    """Enhanced demo coordinator with Electron integration and security"""
    
    def __init__(self, config: Optional[DemoConfig] = None):
        self.config = config or DemoConfig()
        self.runner = DemoRunner(self.config)
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
        
        # Register all available scenarios
        self._register_scenarios()
    
    def _register_scenarios(self):
        """Register all demo scenarios"""
        scenarios = [
            BasicUsageDemoScenario(),
            SearchAndFilteringDemoScenario(),
            SystemManagementDemoScenario()
        ]
        
        for scenario in scenarios:
            self.runner.register_scenario(scenario)
        
        logger.info(f"Registered {len(scenarios)} demo scenarios")
    
    async def run_interactive_demo(self, electron_mode: bool = False) -> Dict[str, Any]:
        """Run interactive demo with real-time updates"""
        if electron_mode:
            self.config.output_format = "electron"
            self.config.enable_events = True
        
        progress = DemoProgressReporter("interactive_demo", 4, self.config)
        
        # Emit demo start event
        if self.config.enable_events:
            emit_system_event("interactive_demo_started", {
                "electron_mode": electron_mode,
                "total_scenarios": len(self.runner._scenarios)
            })
        
        try:
            progress.update("Preparing demonstration")
            
            # Get available scenarios
            scenarios = self.runner.get_available_scenarios()
            demo_results = {
                "intro": {
                    "version": "2.0",
                    "description": "Enhanced Domain Prompts System Demo",
                    "total_scenarios": len(scenarios),
                    "electron_mode": electron_mode
                },
                "scenarios": {}
            }
            
            # Run each scenario
            for i, scenario_meta in enumerate(scenarios):
                scenario_name = scenario_meta["name"]
                progress.update(f"Running {scenario_name}", data={"scenario": scenario_name})
                
                result = await self.runner.run_scenario_async(scenario_name)
                demo_results["scenarios"][scenario_name] = result.to_dict()
                
                # Emit individual scenario completion
                if self.config.enable_events:
                    emit_ui_update("demo_scenario", "completed", {
                        "scenario_name": scenario_name,
                        "success": result.success,
                        "duration": result.duration
                    })
            
            progress.update("Generating summary")
            
            # Generate summary
            successful_scenarios = sum(
                1 for result in demo_results["scenarios"].values() 
                if result["success"]
            )
            
            demo_results["summary"] = {
                "total_scenarios": len(scenarios),
                "successful": successful_scenarios,
                "failed": len(scenarios) - successful_scenarios,
                "success_rate": (successful_scenarios / len(scenarios)) * 100,
                "execution_mode": "electron" if electron_mode else "standard"
            }
            
            progress.complete(True, f"Demo completed: {successful_scenarios}/{len(scenarios)} scenarios successful")
            
            # Emit completion event
            if self.config.enable_events:
                emit_system_event("interactive_demo_completed", demo_results["summary"])
            
            return demo_results
            
        except Exception as e:
            error_msg = f"Interactive demo failed: {e}"
            progress.complete(False, error_msg)
            
            return {
                "error": error_msg,
                "partial_results": demo_results if 'demo_results' in locals() else {}
            }
    
    async def run_specific_scenario(self, scenario_name: str) -> DemoResult:
        """Run a specific demo scenario"""
        validated_name = SecurityValidator.validate_identifier(scenario_name, "scenario_name")
        return await self.runner.run_scenario_async(validated_name)
    
    def get_scenario_catalog(self) -> Dict[str, Any]:
        """Get catalog of available scenarios for UI"""
        scenarios = self.runner.get_available_scenarios()
        
        # Group by category
        catalog = {"categories": {}, "all_scenarios": scenarios}
        
        for scenario in scenarios:
            category = scenario.get("category", "general")
            if category not in catalog["categories"]:
                catalog["categories"][category] = []
            catalog["categories"][category].append(scenario)
        
        return catalog
    
    def export_demo_results(self, output_path: Path) -> bool:
        """Export demo execution history"""
        try:
            validated_path = SecurityValidator.validate_file_path(output_path, "write")
            
            export_data = {
                "export_metadata": {
                    "version": "2.0",
                    "exported_at": DemoResult("", True, 0.0).timestamp,
                    "coordinator_config": self.config.to_dict()
                },
                "execution_history": self.runner.get_execution_history(50),
                "available_scenarios": self.runner.get_available_scenarios()
            }
            
            with open(validated_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Demo results exported to {validated_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export demo results: {e}")
            return False


def demonstrate_basic_usage(output_format: str = "text"):
    """Simplified basic usage demonstration"""
    print("🧬 Domain Prompts System - Enhanced Demo")
    print("=" * 50)
    
    coordinator = EnhancedDemoCoordinator(DemoConfig(
        output_format=output_format,
        enable_events=output_format == "electron"
    ))
    
    async def run_basic():
        result = await coordinator.run_specific_scenario("basic_usage_demo")
        
        if output_format == "json":
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Demo: {result.demo_name}")
            print(f"Success: {result.success}")
            print(f"Duration: {result.duration:.2f}s")
            if result.data:
                print(f"Data keys: {list(result.data.keys())}")
    
    return asyncio.run(run_basic())


def demonstrate_electron_integration():
    """Demonstrate Electron-specific features"""
    print("⚡ Electron Integration Demo")
    print("=" * 30)
    
    coordinator = EnhancedDemoCoordinator(DemoConfig(
        output_format="electron",
        enable_events=True,
        emit_progress=True
    ))
    
    async def run_electron():
        # Get scenario catalog for UI
        catalog = coordinator.get_scenario_catalog()
        print(f"Available categories: {list(catalog['categories'].keys())}")
        
        # Run interactive demo
        results = await coordinator.run_interactive_demo(electron_mode=True)
        print(f"Interactive demo results: {results['summary']}")
    
    return asyncio.run(run_electron())


def main():
    """Enhanced main demonstration with multiple modes"""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "--electron":
            demonstrate_electron_integration()
        elif mode == "--json":
            demonstrate_basic_usage("json")
        elif mode == "--help":
            print("Enhanced Domain Prompts Demo Usage:")
            print("  python demo.py            # Standard text demo")
            print("  python demo.py --electron # Electron integration demo")
            print("  python demo.py --json     # JSON output demo")
            print("  python demo.py --help     # This help message")
        else:
            demonstrate_basic_usage("text")
    else:
        # Default: run comprehensive demo
        print("🧬 Welcome to the Enhanced Domain Prompts System Demo!")
        print("This demonstration showcases the new scalable, secure,")
        print("and Electron-integrated architecture.\n")
        
        try:
            # Create coordinator
            coordinator = EnhancedDemoCoordinator(DemoConfig(
                output_format="text",
                enable_events=False
            ))
            
            # Run interactive demo
            async def run_full_demo():
                results = await coordinator.run_interactive_demo(electron_mode=False)
                
                print("\n" + "=" * 60)
                print("✅ Enhanced Demo Completed Successfully!")
                print(f"\nResults Summary:")
                print(f"• Total scenarios: {results['summary']['total_scenarios']}")
                print(f"• Successful: {results['summary']['successful']}")
                print(f"• Success rate: {results['summary']['success_rate']:.1f}%")
                
                print(f"\nKey improvements demonstrated:")
                print("• Modular demo architecture with reusable scenarios")
                print("• Real-time progress reporting for Electron UI")
                print("• Security validation for all inputs and operations")
                print("• Structured output formats (text/json/electron)")
                print("• Comprehensive error handling and recovery")
                print("• Performance monitoring and metrics collection")
                
                print(f"\nElectron Integration Features:")
                print("• Event emission for real-time UI updates")
                print("• Progress reporting with detailed step information")
                print("• Structured data output for frontend consumption")
                print("• Error reporting with context for UI display")
                print("• Scenario catalog for interactive selection")
                
                return results
            
            results = asyncio.run(run_full_demo())
            return 0
            
        except Exception as e:
            print(f"\n❌ Demo encountered an error: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main()) 