#!/usr/bin/env python3
"""
MCP Core System - Main Entry Point

Provides comprehensive CLI interface and orchestration for the entire MCP Core system.
Supports multiple operation modes:
- Interactive mode with Electron UI
- CLI mode for automation
- Demo/test modes
- Health monitoring
- System administration

Usage:
    python -m src.mcp.core [command] [options]
    python -m src.mcp.core --interactive  # Start with Electron UI
    python -m src.mcp.core --demo         # Run demonstration
    python -m src.mcp.core --health       # Health check
    python -m src.mcp.core --status       # System status
"""

import argparse
import asyncio
import logging
import signal
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import traceback

# Import the unified MCP Core system
from . import (
    MCPCoreSystem, MCPCoreConfiguration, 
    initialize_mcp_core, get_mcp_core, shutdown_mcp_core,
    execute_analysis, connect_server, get_system_status,
    __version__, __author__
)

# Import specific components for advanced usage
from .exceptions import MCPBaseException
from .prompts import get_system_info as get_prompt_system_info
from .strategy import get_system_info as get_strategy_system_info

# Setup module logger
logger = logging.getLogger(__name__)

class MCPCoreOrchestrator:
    """
    Main orchestrator for the MCP Core system
    
    Handles CLI parsing, system initialization, demo modes,
    health monitoring, and graceful shutdown coordination.
    """
    
    def __init__(self):
        self.system: Optional[MCPCoreSystem] = None
        self.running = False
        self.start_time: Optional[datetime] = None
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Performance tracking
        self.metrics = {
            "operations_completed": 0,
            "errors_encountered": 0,
            "last_operation_time": None
        }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if self.running:
            asyncio.create_task(self._graceful_shutdown())
    
    async def _graceful_shutdown(self):
        """Perform graceful shutdown of the entire system"""
        logger.info("Starting graceful shutdown...")
        self.running = False
        self.shutdown_event.set()
        
        if self.system:
            await self.system.shutdown()
        
        # Final cleanup
        await shutdown_mcp_core()
        
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        logger.info(f"MCP Core System shutdown complete. Uptime: {uptime:.2f} seconds")
    
    async def initialize_system(self, config: Dict[str, Any]) -> bool:
        """Initialize the MCP Core system with configuration"""
        try:
            self.start_time = datetime.now()
            logger.info("Initializing MCP Core System...")
            
            # Create configuration
            mcp_config = MCPCoreConfiguration(**config)
            
            # Initialize the global system
            self.system = await initialize_mcp_core(mcp_config)
            
            # Register our event handler for system events
            self.system.register_ui_event_handler(self._handle_system_event)
            
            self.running = True
            logger.info(f"MCP Core System v{__version__} initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _handle_system_event(self, event_data):
        """Handle system events for monitoring and logging"""
        event_type = event_data.get("event", "unknown")
        
        if event_type == "analysis_completed":
            self.metrics["operations_completed"] += 1
            self.metrics["last_operation_time"] = datetime.now()
        elif event_type.endswith("_error"):
            self.metrics["errors_encountered"] += 1
        
        # Log significant events
        if event_type in ["system_initialized", "server_connected", "analysis_completed", "system_shutdown"]:
            logger.info(f"System event: {event_type}")
    
    async def run_interactive_mode(self, config: Dict[str, Any]) -> int:
        """Run in interactive mode with Electron UI"""
        logger.info("Starting interactive mode with Electron UI...")
        
        # Ensure Electron mode is enabled
        config["electron_mode"] = True
        config["electron_bridge_enabled"] = True
        
        if not await self.initialize_system(config):
            logger.error("Failed to initialize system for interactive mode")
            return 1
        
        try:
            # Start the system and wait for shutdown signal
            logger.info("MCP Core System running in interactive mode")
            logger.info("Connect to the Electron UI to interact with the system")
            logger.info("Press Ctrl+C to shutdown gracefully")
            
            # Keep the system running until shutdown
            await self.shutdown_event.wait()
            
            return 0
            
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            return 1
        finally:
            await self._graceful_shutdown()
    
    async def run_cli_mode(self, command: str, args: argparse.Namespace) -> int:
        """Run specific CLI commands"""
        logger.info(f"Running CLI command: {command}")
        
        config = self._create_config_from_args(args)
        config["electron_mode"] = False  # CLI mode doesn't need Electron
        
        if not await self.initialize_system(config):
            logger.error("Failed to initialize system for CLI mode")
            return 1
        
        try:
            if command == "status":
                return await self._cmd_status(args)
            elif command == "health":
                return await self._cmd_health(args)
            elif command == "demo":
                return await self._cmd_demo(args)
            elif command == "test":
                return await self._cmd_test(args)
            elif command == "connect":
                return await self._cmd_connect(args)
            elif command == "analyze":
                return await self._cmd_analyze(args)
            elif command == "export":
                return await self._cmd_export(args)
            elif command == "info":
                return await self._cmd_info(args)
            else:
                logger.error(f"Unknown command: {command}")
                return 1
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            logger.debug(traceback.format_exc())
            return 1
        finally:
            await self._graceful_shutdown()
    
    async def _cmd_status(self, args: argparse.Namespace) -> int:
        """Get and display system status"""
        try:
            status = await get_system_status()
            
            if args.format == "json":
                print(json.dumps(status, indent=2, default=str))
            else:
                self._print_status_formatted(status)
            
            return 0
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return 1
    
    async def _cmd_health(self, args: argparse.Namespace) -> int:
        """Perform comprehensive health check"""
        try:
            health = await self.system.health_check()
            
            if args.format == "json":
                print(json.dumps(health, indent=2, default=str))
            else:
                self._print_health_formatted(health)
            
            # Return appropriate exit code based on health
            overall_health = health.get("overall_health", "unknown")
            if overall_health == "healthy":
                return 0
            elif overall_health == "degraded":
                return 1
            else:  # unhealthy or unknown
                return 2
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return 2
    
    async def _cmd_demo(self, args: argparse.Namespace) -> int:
        """Run demonstration scenarios"""
        try:
            logger.info("Starting MCP Core demonstration...")
            
            # Connect demo servers
            demo_results = []
            
            # Demo 1: Connect mock servers
            logger.info("Demo 1: Connecting mock analysis servers...")
            from ..servers.rnaseq_server import RNASeqServer
            from ..servers.scrnaseq_server import scRNASeqServer
            
            success1 = await connect_server("rnaseq_demo", RNASeqServer)
            success2 = await connect_server("scrnaseq_demo", scRNASeqServer)
            
            demo_results.append({
                "demo": "server_connection",
                "rnaseq_connected": success1,
                "scrnaseq_connected": success2
            })
            
            # Demo 2: Execute sample analysis
            if success1 or success2:
                logger.info("Demo 2: Executing sample analysis workflow...")
                analysis_result = await execute_analysis("scrnaseq", {
                    "dataset": "demo_dataset",
                    "sample_count": 1000,
                    "feature_count": 2000
                })
                demo_results.append({
                    "demo": "analysis_execution",
                    "success": analysis_result.get("success", False),
                    "insights": analysis_result.get("insights", "")
                })
            
            # Demo 3: System performance metrics
            logger.info("Demo 3: Collecting system metrics...")
            status = await get_system_status()
            demo_results.append({
                "demo": "system_metrics",
                "uptime": status.get("uptime", 0),
                "subsystems": len(status.get("subsystems", {})),
                "servers": len(status.get("servers", {}))
            })
            
            # Output results
            if args.format == "json":
                print(json.dumps(demo_results, indent=2, default=str))
            else:
                self._print_demo_results(demo_results)
            
            logger.info("Demonstration completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Demo execution failed: {e}")
            return 1
    
    async def _cmd_test(self, args: argparse.Namespace) -> int:
        """Run comprehensive system tests"""
        try:
            logger.info("Starting comprehensive system tests...")
            
            test_results = {
                "timestamp": datetime.now().isoformat(),
                "tests": []
            }
            
            # Test 1: Subsystem initialization
            logger.info("Test 1: Subsystem initialization...")
            status = await get_system_status()
            test_results["tests"].append({
                "name": "subsystem_initialization",
                "passed": status.get("initialized", False),
                "details": status.get("subsystems", {})
            })
            
            # Test 2: Health checks
            logger.info("Test 2: Health checks...")
            health = await self.system.health_check()
            test_results["tests"].append({
                "name": "health_checks",
                "passed": health.get("overall_health") in ["healthy", "degraded"],
                "details": health.get("checks", {})
            })
            
            # Test 3: Prompt system
            logger.info("Test 3: Prompt system...")
            try:
                prompt_info = get_prompt_system_info()
                test_results["tests"].append({
                    "name": "prompt_system",
                    "passed": prompt_info.get("initialized", False),
                    "details": {
                        "experts_count": len(prompt_info.get("experts", [])),
                        "techniques_count": len(prompt_info.get("techniques", []))
                    }
                })
            except Exception as e:
                test_results["tests"].append({
                    "name": "prompt_system",
                    "passed": False,
                    "error": str(e)
                })
            
            # Test 4: Strategy system
            logger.info("Test 4: Strategy system...")
            try:
                strategy_info = get_strategy_system_info()
                test_results["tests"].append({
                    "name": "strategy_system",
                    "passed": strategy_info.get("initialized", False),
                    "details": strategy_info
                })
            except Exception as e:
                test_results["tests"].append({
                    "name": "strategy_system",
                    "passed": False,
                    "error": str(e)
                })
            
            # Calculate overall test results
            passed_tests = sum(1 for test in test_results["tests"] if test.get("passed", False))
            total_tests = len(test_results["tests"])
            test_results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            }
            
            # Output results
            if args.format == "json":
                print(json.dumps(test_results, indent=2, default=str))
            else:
                self._print_test_results(test_results)
            
            # Return appropriate exit code
            return 0 if passed_tests == total_tests else 1
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return 1
    
    async def _cmd_connect(self, args: argparse.Namespace) -> int:
        """Connect to a specific server"""
        try:
            server_name = args.server_name
            server_type = args.server_type
            
            logger.info(f"Connecting to {server_type} server: {server_name}")
            
            # Import appropriate server class
            server_class = self._get_server_class(server_type)
            if not server_class:
                logger.error(f"Unknown server type: {server_type}")
                return 1
            
            success = await connect_server(server_name, server_class)
            
            if success:
                logger.info(f"Successfully connected to {server_name}")
                return 0
            else:
                logger.error(f"Failed to connect to {server_name}")
                return 1
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return 1
    
    async def _cmd_analyze(self, args: argparse.Namespace) -> int:
        """Execute an analysis workflow"""
        try:
            analysis_type = args.analysis_type
            context = {}
            
            # Parse context from args
            if args.context:
                try:
                    context = json.loads(args.context)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON context provided")
                    return 1
            
            logger.info(f"Executing {analysis_type} analysis...")
            
            result = await execute_analysis(analysis_type, context)
            
            if args.format == "json":
                print(json.dumps(result, indent=2, default=str))
            else:
                self._print_analysis_result(result)
            
            return 0 if result.get("success", False) else 1
            
        except Exception as e:
            logger.error(f"Analysis execution failed: {e}")
            return 1
    
    async def _cmd_export(self, args: argparse.Namespace) -> int:
        """Export system data"""
        try:
            export_type = args.export_type
            output_path = Path(args.output) if args.output else Path(f"mcp_export_{export_type}_{int(time.time())}.json")
            
            logger.info(f"Exporting {export_type} data to {output_path}")
            
            if export_type == "status":
                data = await get_system_status()
            elif export_type == "health":
                data = await self.system.health_check()
            elif export_type == "metrics":
                data = self.metrics
            elif export_type == "all":
                data = {
                    "status": await get_system_status(),
                    "health": await self.system.health_check(),
                    "metrics": self.metrics,
                    "export_timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"Unknown export type: {export_type}")
                return 1
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Data exported successfully to {output_path}")
            return 0
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return 1
    
    async def _cmd_info(self, args: argparse.Namespace) -> int:
        """Display system information"""
        try:
            info = {
                "version": __version__,
                "author": __author__,
                "system_status": await get_system_status() if self.system else "Not initialized",
                "subsystem_info": {}
            }
            
            # Add subsystem information
            if args.detailed:
                try:
                    info["subsystem_info"]["prompts"] = get_prompt_system_info()
                except Exception as e:
                    info["subsystem_info"]["prompts"] = f"Error: {e}"
                
                try:
                    info["subsystem_info"]["strategy"] = get_strategy_system_info()
                except Exception as e:
                    info["subsystem_info"]["strategy"] = f"Error: {e}"
            
            if args.format == "json":
                print(json.dumps(info, indent=2, default=str))
            else:
                self._print_info_formatted(info)
            
            return 0
            
        except Exception as e:
            logger.error(f"Info command failed: {e}")
            return 1
    
    def _create_config_from_args(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Create system configuration from command line arguments"""
        config = {}
        
        if hasattr(args, 'debug') and args.debug:
            config["debug"] = True
        
        if hasattr(args, 'port') and args.port:
            config["websocket_port"] = args.port
        
        if hasattr(args, 'data_dir') and args.data_dir:
            config["training_data_path"] = Path(args.data_dir)
        
        if hasattr(args, 'electron') and args.electron is False:
            config["electron_mode"] = False
        
        return config
    
    def _get_server_class(self, server_type: str):
        """Get server class by type name"""
        try:
            if server_type.lower() == "rnaseq":
                from ..servers.rnaseq_server import RNASeqServer
                return RNASeqServer
            elif server_type.lower() == "scrnaseq":
                from ..servers.scrnaseq_server import scRNASeqServer
                return scRNASeqServer
            elif server_type.lower() == "atacseq":
                from ..servers.atacseq_server import ATACSeqServer
                return ATACSeqServer
            elif server_type.lower() == "proteomics":
                from ..servers.proteomics_server import ProteomicsServer
                return ProteomicsServer
            else:
                return None
        except ImportError:
            return None
    
    # Formatting methods for output
    
    def _print_status_formatted(self, status: Dict[str, Any]):
        """Print formatted status information"""
        print(f"\n{'='*50}")
        print(f"MCP CORE SYSTEM STATUS")
        print(f"{'='*50}")
        print(f"Version: {status.get('version', 'Unknown')}")
        print(f"Initialized: {status.get('initialized', False)}")
        print(f"Running: {status.get('running', False)}")
        print(f"Uptime: {status.get('uptime', 0):.2f} seconds")
        print(f"Electron Mode: {status.get('electron_mode', False)}")
        
        subsystems = status.get('subsystems', {})
        if subsystems:
            print(f"\nSubsystems ({len(subsystems)}):")
            for name, info in subsystems.items():
                print(f"  - {name}: {info.get('status', 'Unknown')}")
        
        servers = status.get('servers', {})
        if servers:
            print(f"\nConnected Servers ({len(servers)}):")
            for name, info in servers.items():
                print(f"  - {name}: {info.get('type', 'Unknown')}")
        
        print(f"{'='*50}\n")
    
    def _print_health_formatted(self, health: Dict[str, Any]):
        """Print formatted health information"""
        print(f"\n{'='*50}")
        print(f"MCP CORE SYSTEM HEALTH")
        print(f"{'='*50}")
        print(f"Overall Health: {health.get('overall_health', 'Unknown').upper()}")
        print(f"Timestamp: {health.get('timestamp', 'Unknown')}")
        
        checks = health.get('checks', {})
        if checks:
            print(f"\nHealth Checks ({len(checks)}):")
            for name, check in checks.items():
                status = check.get('status', 'unknown')
                symbol = "✓" if status == "healthy" else "⚠" if status == "degraded" else "✗"
                print(f"  {symbol} {name}: {status.upper()}")
                
                if 'error' in check:
                    print(f"    Error: {check['error']}")
        
        print(f"{'='*50}\n")
    
    def _print_demo_results(self, results: List[Dict[str, Any]]):
        """Print formatted demo results"""
        print(f"\n{'='*50}")
        print(f"MCP CORE DEMONSTRATION RESULTS")
        print(f"{'='*50}")
        
        for i, result in enumerate(results, 1):
            demo_name = result.get('demo', f'Demo {i}')
            print(f"\n{i}. {demo_name.replace('_', ' ').title()}:")
            
            for key, value in result.items():
                if key != 'demo':
                    print(f"   {key}: {value}")
        
        print(f"\n{'='*50}\n")
    
    def _print_test_results(self, results: Dict[str, Any]):
        """Print formatted test results"""
        print(f"\n{'='*50}")
        print(f"MCP CORE SYSTEM TESTS")
        print(f"{'='*50}")
        
        summary = results.get('summary', {})
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('passed_tests', 0)}")
        print(f"Failed: {summary.get('failed_tests', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        
        tests = results.get('tests', [])
        if tests:
            print(f"\nTest Details:")
            for test in tests:
                name = test.get('name', 'Unknown')
                passed = test.get('passed', False)
                symbol = "✓" if passed else "✗"
                print(f"  {symbol} {name.replace('_', ' ').title()}")
                
                if 'error' in test:
                    print(f"    Error: {test['error']}")
        
        print(f"\n{'='*50}\n")
    
    def _print_analysis_result(self, result: Dict[str, Any]):
        """Print formatted analysis result"""
        print(f"\n{'='*50}")
        print(f"ANALYSIS RESULT")
        print(f"{'='*50}")
        print(f"Type: {result.get('analysis_type', 'Unknown')}")
        print(f"Success: {result.get('success', False)}")
        print(f"Timestamp: {result.get('timestamp', 'Unknown')}")
        
        insights = result.get('insights', '')
        if insights:
            print(f"\nInsights:")
            print(f"  {insights}")
        
        actions = result.get('suggested_actions', [])
        if actions:
            print(f"\nSuggested Actions:")
            for i, action in enumerate(actions, 1):
                print(f"  {i}. {action}")
        
        print(f"\n{'='*50}\n")
    
    def _print_info_formatted(self, info: Dict[str, Any]):
        """Print formatted system information"""
        print(f"\n{'='*50}")
        print(f"MCP CORE SYSTEM INFORMATION")
        print(f"{'='*50}")
        print(f"Version: {info.get('version', 'Unknown')}")
        print(f"Author: {info.get('author', 'Unknown')}")
        
        system_status = info.get('system_status', {})
        if isinstance(system_status, dict):
            print(f"Initialized: {system_status.get('initialized', False)}")
            print(f"Running: {system_status.get('running', False)}")
        
        subsystem_info = info.get('subsystem_info', {})
        if subsystem_info:
            print(f"\nSubsystem Information:")
            for name, details in subsystem_info.items():
                print(f"  {name.title()}:")
                if isinstance(details, dict):
                    for key, value in details.items():
                        print(f"    {key}: {value}")
                else:
                    print(f"    {details}")
        
        print(f"\n{'='*50}\n")

def create_parser() -> argparse.ArgumentParser:
    """Create comprehensive command line argument parser"""
    parser = argparse.ArgumentParser(
        description="MCP Core System - Unified Model Context Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.mcp.core --interactive
  python -m src.mcp.core status --format json
  python -m src.mcp.core health
  python -m src.mcp.core demo --format json
  python -m src.mcp.core test --detailed
  python -m src.mcp.core connect rnaseq_server rnaseq
  python -m src.mcp.core analyze scrnaseq --context '{"dataset": "test"}'
        """
    )
    
    # Global options
    parser.add_argument("--version", action="version", version=f"MCP Core v{__version__}")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--data-dir", type=str, help="Data directory path")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--no-electron", dest="electron", action="store_false", help="Disable Electron integration")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Interactive mode
    subparsers.add_parser("interactive", help="Start interactive mode with Electron UI")
    
    # Status command
    subparsers.add_parser("status", help="Get system status")
    
    # Health command
    subparsers.add_parser("health", help="Perform health check")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run demonstration")
    demo_parser.add_argument("--scenario", type=str, help="Specific demo scenario")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run system tests")
    test_parser.add_argument("--detailed", action="store_true", help="Detailed test output")
    
    # Connect command
    connect_parser = subparsers.add_parser("connect", help="Connect to a server")
    connect_parser.add_argument("server_name", help="Server instance name")
    connect_parser.add_argument("server_type", choices=["rnaseq", "scrnaseq", "atacseq", "proteomics"], help="Server type")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Execute analysis")
    analyze_parser.add_argument("analysis_type", choices=["scrnaseq", "rnaseq", "atacseq"], help="Analysis type")
    analyze_parser.add_argument("--context", type=str, help="JSON context for analysis")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export system data")
    export_parser.add_argument("export_type", choices=["status", "health", "metrics", "all"], help="Data to export")
    export_parser.add_argument("--output", type=str, help="Output file path")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Display system information")
    info_parser.add_argument("--detailed", action="store_true", help="Detailed information")
    
    return parser

async def main():
    """Main entry point for the MCP Core system"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging level
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Create orchestrator
    orchestrator = MCPCoreOrchestrator()
    
    try:
        # Handle different operation modes
        if args.command == "interactive" or (not args.command and not any(vars(args).values())):
            # Interactive mode (default)
            config = orchestrator._create_config_from_args(args)
            return await orchestrator.run_interactive_mode(config)
        
        elif args.command:
            # CLI command mode
            return await orchestrator.run_cli_mode(args.command, args)
        
        else:
            # Show help if no command provided
            parser.print_help()
            return 0
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        return 1

def run_sync():
    """Synchronous entry point for compatibility"""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        return 0

if __name__ == "__main__":
    sys.exit(run_sync()) 