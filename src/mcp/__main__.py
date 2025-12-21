#!/usr/bin/env python3
"""
MCP (Model Context Protocol) - Main Entry Point

Command-line interface for the unified MCP bioinformatics analysis platform.
Provides comprehensive access to agent, core, and server subsystems with
full Electron UI/UX integration.

Usage:
    python -m src.mcp [command] [options]
    
Commands:
    start       Start the complete MCP system
    demo        Run system demonstrations
    test        Run integration tests
    status      Check system status
    health      Perform health checks
    connect     Connect to specific servers
    analyze     Execute analysis tasks
    agent       Interact with the agent system
    electron    Start Electron UI mode
    monitor     Monitor system performance
    export      Export system data/metrics

Examples:
    python -m src.mcp start --electron              # Start with Electron UI
    python -m src.mcp demo --comprehensive          # Run full demo
    python -m src.mcp test --component agent        # Test agent system
    python -m src.mcp agent --chat "Analyze RNA-seq" # Chat with agent
    python -m src.mcp analyze --type rnaseq         # Run RNA-seq analysis
"""

import argparse
import asyncio
import logging
import signal
import sys
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import traceback

# Import the unified MCP system
from . import (
    MCPSystem,
    MCPSystemConfiguration,
    initialize_mcp_system,
    get_mcp_system,
    shutdown_mcp_system,
    quick_start,
    __version__,
    __author__,
    __description__
)

# Setup module logger
logger = logging.getLogger(__name__)


class MCPSystemCLI:
    """
    Command Line Interface for the MCP System
    
    Provides comprehensive control over the entire MCP platform including
    agent intelligence, core services, server orchestration, and Electron UI.
    """
    
    def __init__(self):
        self.system: Optional[MCPSystem] = None
        self.start_time: Optional[datetime] = None
        self.running = False
        self.metrics: Dict[str, Any] = {
            "commands_executed": 0,
            "errors_encountered": 0,
            "last_command_time": None
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self._graceful_shutdown())
    
    async def _graceful_shutdown(self):
        """Perform graceful shutdown of the MCP system"""
        self.running = False
        
        if self.system:
            try:
                await self.system.shutdown()
                logger.info("✅ MCP System shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        
        sys.exit(0)
    
    async def initialize_system(self, config: Dict[str, Any]) -> bool:
        """Initialize the MCP system with configuration"""
        try:
            self.start_time = datetime.now()
            logger.info("🚀 Initializing MCP System...")
            
            # Create configuration
            mcp_config = MCPSystemConfiguration(**config)
            
            # Initialize the system
            self.system = await initialize_mcp_system(mcp_config)
            
            self.running = True
            logger.info(f"✅ MCP System v{__version__} initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize system: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _handle_system_event(self, event_data):
        """Handle system events for monitoring and logging"""
        event_type = event_data.get("event", "unknown")
        
        if event_type == "analysis_completed":
            self.metrics["commands_executed"] += 1
            self.metrics["last_command_time"] = datetime.now()
        elif event_type.endswith("_error"):
            self.metrics["errors_encountered"] += 1
        
        # Log significant events
        if event_type in ["system_initialized", "server_connected", "analysis_completed", "system_shutdown"]:
            logger.info(f"System event: {event_type}")
    
    async def run_interactive_mode(self, config: Dict[str, Any]) -> int:
        """Run in interactive mode with Electron UI"""
        try:
            if not await self.initialize_system(config):
                return 1
            
            # Start Electron UI
            if config.get("electron_mode", True):
                logger.info("🖥️  Starting Electron UI...")
                await self.system.start_electron_ui()
                
                print("\n" + "="*60)
                print("🚀 MCP SYSTEM - ELECTRON UI MODE")
                print("="*60)
                print("The system is now running with Electron UI integration.")
                print("You can:")
                print("• Use the Electron desktop app for visual interface")
                print("• Chat with the intelligent agent")
                print("• Execute bioinformatics analyses")
                print("• Monitor system status in real-time")
                print("• Access all connected servers and tools")
                print("\nPress Ctrl+C to shutdown gracefully")
                print("="*60)
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            return 0
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            return 1
    
    async def run_cli_mode(self, command: str, args: argparse.Namespace) -> int:
        """Run specific commands in CLI mode"""
        try:
            # Initialize system for most commands
            if command not in ["help", "version"]:
                config = self._create_config_from_args(args)
                if not await self.initialize_system(config):
                    return 1
            
            # Route to appropriate command handler
            if command == "start":
                return await self._cmd_start(args)
            elif command == "demo":
                return await self._cmd_demo(args)
            elif command == "test":
                return await self._cmd_test(args)
            elif command == "status":
                return await self._cmd_status(args)
            elif command == "health":
                return await self._cmd_health(args)
            elif command == "connect":
                return await self._cmd_connect(args)
            elif command == "analyze":
                return await self._cmd_analyze(args)
            elif command == "agent":
                return await self._cmd_agent(args)
            elif command == "electron":
                return await self._cmd_electron(args)
            elif command == "monitor":
                return await self._cmd_monitor(args)
            elif command == "export":
                return await self._cmd_export(args)
            elif command == "version":
                return self._cmd_version()
            else:
                logger.error(f"Unknown command: {command}")
                return 1
                
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            logger.debug(traceback.format_exc())
            return 1
    
    async def _cmd_start(self, args: argparse.Namespace) -> int:
        """Start the MCP system"""
        logger.info("Starting MCP System...")
        
        if args.electron:
            await self.system.start_electron_ui()
            print("🚀 MCP System started with Electron UI")
            print(f"🌐 WebSocket server running on port {self.system.config.websocket_port}")
        else:
            print("🚀 MCP System started in CLI mode")
        
        if args.interactive:
            print("Entering interactive mode... (Press Ctrl+C to exit)")
            try:
                while self.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
        
        return 0
    
    async def _cmd_demo(self, args: argparse.Namespace) -> int:
        """Run system demonstrations"""
        logger.info("Running MCP System demonstrations...")
        
        demos = []
        
        if args.comprehensive or args.agent:
            demos.append(("Agent System Demo", self._demo_agent))
        
        if args.comprehensive or args.core:
            demos.append(("Core System Demo", self._demo_core))
        
        if args.comprehensive or args.servers:
            demos.append(("Server System Demo", self._demo_servers))
        
        if args.comprehensive or args.integration:
            demos.append(("Integration Demo", self._demo_integration))
        
        if not demos:
            demos = [
                ("Quick Demo", self._demo_quick),
                ("Agent System Demo", self._demo_agent),
                ("Core System Demo", self._demo_core)
            ]
        
        results = []
        for demo_name, demo_func in demos:
            try:
                print(f"\n{'='*50}")
                print(f"Running {demo_name}...")
                print('='*50)
                
                result = await demo_func()
                results.append({"name": demo_name, "success": True, "result": result})
                print(f"✅ {demo_name} completed successfully")
                
            except Exception as e:
                logger.error(f"❌ {demo_name} failed: {e}")
                results.append({"name": demo_name, "success": False, "error": str(e)})
        
        # Print summary
        self._print_demo_results(results)
        
        successful = sum(1 for r in results if r["success"])
        return 0 if successful == len(results) else 1
    
    async def _cmd_test(self, args: argparse.Namespace) -> int:
        """Run integration tests"""
        logger.info("Running MCP System tests...")
        
        test_results = {}
        
        # Component tests
        if args.component == "agent" or args.component == "all":
            test_results["agent"] = await self._test_agent_system()
        
        if args.component == "core" or args.component == "all":
            test_results["core"] = await self._test_core_system()
        
        if args.component == "servers" or args.component == "all":
            test_results["servers"] = await self._test_server_system()
        
        if args.component == "integration" or args.component == "all":
            test_results["integration"] = await self._test_integration()
        
        if args.component == "electron" or args.component == "all":
            test_results["electron"] = await self._test_electron_integration()
        
        # Print results
        self._print_test_results(test_results)
        
        # Return success if all tests passed
        all_passed = all(result.get("success", False) for result in test_results.values())
        return 0 if all_passed else 1
    
    async def _cmd_status(self, args: argparse.Namespace) -> int:
        """Check system status"""
        try:
            status = await self.system.get_system_status()
            self._print_status_formatted(status)
            return 0
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return 1
    
    async def _cmd_health(self, args: argparse.Namespace) -> int:
        """Perform health checks"""
        try:
            health = await self.system.health_check()
            self._print_health_formatted(health)
            
            # Return error code if any component is unhealthy
            unhealthy = any(not status.get("healthy", True) for status in health.values())
            return 1 if unhealthy else 0
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return 1
    
    async def _cmd_connect(self, args: argparse.Namespace) -> int:
        """Connect to specific servers"""
        try:
            server_type = args.server_type
            server_class = self._get_server_class(server_type)
            
            if not server_class:
                logger.error(f"Unknown server type: {server_type}")
                return 1
            
            success = await self.system.core_system.connect_server(
                server_type, 
                server_class,
                **vars(args)
            )
            
            if success:
                print(f"✅ Successfully connected to {server_type} server")
                return 0
            else:
                print(f"❌ Failed to connect to {server_type} server")
                return 1
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return 1
    
    async def _cmd_analyze(self, args: argparse.Namespace) -> int:
        """Execute analysis tasks"""
        try:
            analysis_type = args.type
            context = getattr(args, 'context', {})
            
            if hasattr(args, 'input_file') and args.input_file:
                context['input_file'] = args.input_file
            
            if hasattr(args, 'output_dir') and args.output_dir:
                context['output_dir'] = args.output_dir
            
            print(f"🔬 Executing {analysis_type} analysis...")
            
            result = await self.system.execute_analysis(analysis_type, context)
            
            self._print_analysis_result(result)
            
            return 0 if result.get("success", False) else 1
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return 1
    
    async def _cmd_agent(self, args: argparse.Namespace) -> int:
        """Interact with the agent system"""
        try:
            if args.chat:
                print(f"💬 Chatting with agent: {args.chat}")
                response, tools_used = await self.system.chat_with_agent(args.chat)
                
                print(f"\n🤖 Agent Response:")
                print(response)
                
                if tools_used:
                    print(f"\n🔧 Tools Used: {', '.join(tools_used)}")
                
                return 0
            
            elif args.status:
                # Import agent status function
                from .agent import get_agent_status
                status = get_agent_status()
                print(json.dumps(status, indent=2))
                return 0
            
            else:
                print("No agent command specified. Use --chat or --status")
                return 1
                
        except Exception as e:
            logger.error(f"Agent command failed: {e}")
            return 1
    
    async def _cmd_electron(self, args: argparse.Namespace) -> int:
        """Start Electron UI mode"""
        try:
            print("🖥️  Starting Electron UI mode...")
            await self.system.start_electron_ui()
            
            print(f"🌐 Electron UI started on port {self.system.config.websocket_port}")
            print("🚀 System ready for Electron connections")
            
            if args.wait:
                print("Press Ctrl+C to shutdown...")
                try:
                    while self.running:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
            
            return 0
            
        except Exception as e:
            logger.error(f"Electron mode failed: {e}")
            return 1
    
    async def _cmd_monitor(self, args: argparse.Namespace) -> int:
        """Monitor system performance"""
        try:
            print("📊 Starting system monitoring...")
            print("Press Ctrl+C to stop monitoring")
            
            interval = getattr(args, 'interval', 5)
            
            try:
                while self.running:
                    # Clear screen
                    os.system('clear' if os.name == 'posix' else 'cls')
                    
                    # Get current status
                    status = await self.system.get_system_status()
                    health = await self.system.health_check()
                    
                    # Print monitoring display
                    print(f"🔍 MCP SYSTEM MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("="*60)
                    
                    # System overview
                    print(f"Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
                    print(f"Uptime: {status['uptime']:.1f} seconds")
                    print(f"Electron: {'🖥️  Active' if status['electron_mode'] else '❌ Disabled'}")
                    
                    # Component health
                    print("\nComponent Health:")
                    for component, health_info in health.items():
                        healthy = health_info.get("healthy", False)
                        emoji = "🟢" if healthy else "🔴"
                        print(f"  {emoji} {component.title()}")
                    
                    # Performance metrics
                    if hasattr(self.system, 'metrics'):
                        print(f"\nMetrics:")
                        print(f"  Operations: {self.system.metrics.get('operations_completed', 0)}")
                        print(f"  Errors: {self.system.metrics.get('errors_encountered', 0)}")
                    
                    print(f"\nNext update in {interval} seconds... (Ctrl+C to stop)")
                    
                    await asyncio.sleep(interval)
                    
            except KeyboardInterrupt:
                print("\n📊 Monitoring stopped")
                return 0
                
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            return 1
    
    async def _cmd_export(self, args: argparse.Namespace) -> int:
        """Export system data/metrics"""
        try:
            output_file = args.output or f"mcp_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "version": __version__,
                "system_status": await self.system.get_system_status(),
                "health_check": await self.system.health_check(),
                "metrics": self.metrics
            }
            
            if args.include_logs and hasattr(self.system, 'get_logs'):
                export_data["logs"] = await self.system.get_logs()
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"✅ System data exported to {output_file}")
            return 0
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return 1
    
    def _cmd_version(self) -> int:
        """Show version information"""
        print(f"MCP System v{__version__}")
        print(f"Author: {__author__}")
        print(f"Description: {__description__}")
        return 0
    
    # Demo functions
    
    async def _demo_quick(self) -> Dict[str, Any]:
        """Quick system demonstration"""
        try:
            # Test basic functionality
            status = await self.system.get_system_status()
            health = await self.system.health_check()
            tools = await self.system.get_available_tools()
            
            return {
                "components_initialized": len(status.get("components", {})),
                "healthy_components": sum(1 for h in health.values() if h.get("healthy")),
                "available_tools": len(tools)
            }
        except Exception as e:
            raise Exception(f"Quick demo failed: {e}")
    
    async def _demo_agent(self) -> Dict[str, Any]:
        """Demonstrate agent system capabilities"""
        try:
            # Test agent chat
            test_message = "What bioinformatics analyses are available?"
            response, tools_used = await self.system.chat_with_agent(test_message)
            
            print(f"Test Query: {test_message}")
            print(f"Agent Response: {response[:100]}...")
            print(f"Tools Used: {tools_used}")
            
            return {
                "chat_successful": len(response) > 0,
                "tools_identified": len(tools_used),
                "response_length": len(response)
            }
        except Exception as e:
            raise Exception(f"Agent demo failed: {e}")
    
    async def _demo_core(self) -> Dict[str, Any]:
        """Demonstrate core system capabilities"""
        try:
            # Test core functionality
            tools = await self.system.get_available_tools()
            status = await self.system.get_system_status()
            
            print(f"Available Tools: {len(tools)}")
            print(f"Connected Servers: {len(status.get('components', {}).get('core', {}).get('servers', {}))}")
            
            return {
                "tools_available": len(tools),
                "servers_connected": len(status.get('components', {}).get('core', {}).get('servers', {})),
                "core_initialized": status.get('initialized', False)
            }
        except Exception as e:
            raise Exception(f"Core demo failed: {e}")
    
    async def _demo_servers(self) -> Dict[str, Any]:
        """Demonstrate server system capabilities"""
        try:
            # Test server functionality
            status = await self.system.get_system_status()
            server_status = status.get('components', {}).get('servers', {})
            
            print(f"Server Orchestrator: {server_status.get('status', 'Unknown')}")
            print(f"Active Servers: {len(server_status.get('active_servers', {}))}")
            
            return {
                "orchestrator_running": server_status.get('status') == 'running',
                "active_servers": len(server_status.get('active_servers', {}))
            }
        except Exception as e:
            raise Exception(f"Server demo failed: {e}")
    
    async def _demo_integration(self) -> Dict[str, Any]:
        """Demonstrate cross-system integration"""
        try:
            # Test integration between components
            tools = await self.system.get_available_tools()
            
            # Test agent accessing tools
            if tools and self.system.agent:
                # Use a query that would actually trigger a tool call
                test_query = "What is the current pipeline status?"
                response, tools_used = await self.system.chat_with_agent(test_query)
                
                integration_success = len(tools_used) > 0
                print(f"🔧 DEBUG: Tools used: {tools_used}")
                print(f"🔧 DEBUG: Integration success: {integration_success}")
            else:
                integration_success = False
            
            print(f"Integration Test: {'✅ Passed' if integration_success else '❌ Failed'}")
            
            return {
                "agent_tool_access": integration_success,
                "cross_component_communication": True
            }
        except Exception as e:
            raise Exception(f"Integration demo failed: {e}")
    
    # Test functions
    
    async def _test_agent_system(self) -> Dict[str, Any]:
        """Test agent system functionality"""
        try:
            if not self.system.agent:
                return {"success": False, "error": "Agent not initialized"}
            
            # Test basic agent functionality
            from .agent import get_agent_status
            status = get_agent_status()
            
            return {
                "success": status.get("agent_initialized", False),
                "details": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_core_system(self) -> Dict[str, Any]:
        """Test core system functionality"""
        try:
            if not self.system.core_system:
                return {"success": False, "error": "Core system not initialized"}
            
            health = await self.system.core_system.health_check()
            
            return {
                "success": health.get("overall_healthy", False),
                "details": health
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_server_system(self) -> Dict[str, Any]:
        """Test server system functionality"""
        try:
            if not self.system.server_orchestrator:
                return {"success": False, "error": "Server orchestrator not initialized"}
            
            status = self.system.server_orchestrator.get_system_status()
            
            return {
                "success": status.get("status") == "running",
                "details": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_integration(self) -> Dict[str, Any]:
        """Test cross-system integration"""
        try:
            # Test communication between components
            status = await self.system.get_system_status()
            components = status.get("components", {})
            
            all_running = all(
                comp.get("status") == "running" 
                for comp in components.values() 
                if isinstance(comp, dict)
            )
            
            return {
                "success": all_running,
                "details": {"components_running": len(components)}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_electron_integration(self) -> Dict[str, Any]:
        """Test Electron integration"""
        try:
            bridges = len(self.system.electron_bridges)
            electron_enabled = self.system.config.electron_mode
            
            return {
                "success": electron_enabled and bridges > 0,
                "details": {
                    "electron_mode": electron_enabled,
                    "bridges_active": bridges
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_config_from_args(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Create system configuration from command line arguments"""
        config = {
            "debug": getattr(args, 'debug', False),
            "electron_mode": getattr(args, 'electron', True),
        }
        
        # Add API key if provided
        if hasattr(args, 'api_key') and args.api_key:
            config["agent_api_key"] = args.api_key
        
        # Add other configuration options as needed
        if hasattr(args, 'port') and args.port:
            config["websocket_port"] = args.port
        
        return config
    
    def _get_server_class(self, server_type: str):
        """Get server class by type name"""
        try:
            if server_type.lower() == "rnaseq":
                from .servers.rnaseq_server import RNASeqMCPServer
                return RNASeqMCPServer
            elif server_type.lower() == "scrnaseq":
                from .servers.scrnaseq_server import scRNASeqMCPServer
                return scRNASeqMCPServer
            elif server_type.lower() == "atacseq":
                from .servers.atacseq_server import ATACSeqMCPServer
                return ATACSeqMCPServer
            elif server_type.lower() == "proteomics":
                from .servers.proteomics_server import ProteomicsMCPServer
                return ProteomicsMCPServer
            elif server_type.lower() == "data":
                from .servers.data_server import DataMCPServer
                return DataMCPServer
            else:
                return None
        except ImportError:
            return None
    
    # Formatting methods for output
    
    def _print_status_formatted(self, status: Dict[str, Any]):
        """Print formatted status information"""
        print(f"\n{'='*60}")
        print(f"MCP SYSTEM STATUS")
        print(f"{'='*60}")
        print(f"Version: {status.get('version', 'Unknown')}")
        print(f"Initialized: {status.get('initialized', False)}")
        print(f"Running: {status.get('running', False)}")
        print(f"Uptime: {status.get('uptime', 0):.2f} seconds")
        print(f"Electron Mode: {status.get('electron_mode', False)}")
        
        components = status.get('components', {})
        if components:
            print(f"\nComponents ({len(components)}):")
            for name, info in components.items():
                if isinstance(info, dict):
                    component_status = info.get('status', 'Unknown')
                    print(f"  • {name.title()}: {component_status}")
                else:
                    print(f"  • {name.title()}: Active")
        
        bridges = status.get('electron_bridges', [])
        if bridges:
            print(f"\nElectron Bridges ({len(bridges)}):")
            for bridge in bridges:
                print(f"  • {bridge}")
        
        print(f"{'='*60}\n")
    
    def _print_health_formatted(self, health: Dict[str, Any]):
        """Print formatted health information"""
        print(f"\n{'='*60}")
        print(f"MCP SYSTEM HEALTH CHECK")
        print(f"{'='*60}")
        
        overall_healthy = all(status.get("healthy", False) for status in health.values())
        print(f"Overall Health: {'🟢 Healthy' if overall_healthy else '🔴 Issues Detected'}")
        
        print(f"\nComponent Health:")
        for component, health_info in health.items():
            healthy = health_info.get("healthy", False)
            emoji = "🟢" if healthy else "🔴"
            print(f"  {emoji} {component.title()}: {'Healthy' if healthy else 'Issues'}")
            
            if not healthy and "error" in health_info:
                print(f"      Error: {health_info['error']}")
        
        print(f"{'='*60}\n")
    
    def _print_demo_results(self, results: List[Dict[str, Any]]):
        """Print formatted demo results"""
        print(f"\n{'='*60}")
        print(f"DEMO RESULTS SUMMARY")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        
        print(f"Total Demos: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success Rate: {(successful/total*100):.1f}%")
        
        print(f"\nDetailed Results:")
        for result in results:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['name']}")
            if not result["success"]:
                print(f"      Error: {result.get('error', 'Unknown error')}")
        
        print(f"{'='*60}\n")
    
    def _print_test_results(self, results: Dict[str, Any]):
        """Print formatted test results"""
        print(f"\n{'='*60}")
        print(f"TEST RESULTS SUMMARY")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results.values() if r.get("success", False))
        total = len(results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success Rate: {(successful/total*100):.1f}%")
        
        print(f"\nDetailed Results:")
        for test_name, result in results.items():
            status = "✅" if result.get("success", False) else "❌"
            print(f"  {status} {test_name.title()} Test")
            if not result.get("success", False):
                print(f"      Error: {result.get('error', 'Unknown error')}")
        
        print(f"{'='*60}\n")
    
    def _print_analysis_result(self, result: Dict[str, Any]):
        """Print formatted analysis result"""
        print(f"\n{'='*60}")
        print(f"ANALYSIS RESULT")
        print(f"{'='*60}")
        
        success = result.get("success", False)
        print(f"Status: {'✅ Success' if success else '❌ Failed'}")
        
        if success:
            if "output_files" in result:
                print(f"Output Files:")
                for file_path in result["output_files"]:
                    print(f"  • {file_path}")
            
            if "summary" in result:
                print(f"Summary: {result['summary']}")
        else:
            if "error" in result:
                print(f"Error: {result['error']}")
        
        print(f"{'='*60}\n")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="MCP (Model Context Protocol) - Unified Bioinformatics Analysis Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --electron              Start with Electron UI
  %(prog)s demo --comprehensive          Run full demonstration
  %(prog)s test --component agent        Test agent system
  %(prog)s agent --chat "Analyze data"   Chat with agent
  %(prog)s analyze --type rnaseq         Run RNA-seq analysis
  %(prog)s status                        Check system status
  %(prog)s health                        Perform health check
  %(prog)s monitor --interval 10         Monitor system performance
        """
    )
    
    # Global options
    parser.add_argument("--version", action="version", version=f"MCP System v{__version__}")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--electron", action="store_true", default=True, help="Enable Electron UI mode")
    parser.add_argument("--no-electron", dest="electron", action="store_false", help="Disable Electron UI")
    parser.add_argument("--api-key", help="API key for external services")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port for Electron communication")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the MCP system")
    start_parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run system demonstrations")
    demo_parser.add_argument("--comprehensive", action="store_true", help="Run all demonstrations")
    demo_parser.add_argument("--agent", action="store_true", help="Demo agent system")
    demo_parser.add_argument("--core", action="store_true", help="Demo core system")
    demo_parser.add_argument("--servers", action="store_true", help="Demo server system")
    demo_parser.add_argument("--integration", action="store_true", help="Demo integration")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run integration tests")
    test_parser.add_argument("--component", choices=["agent", "core", "servers", "integration", "electron", "all"],
                           default="all", help="Component to test")
    
    # Status command
    subparsers.add_parser("status", help="Check system status")
    
    # Health command
    subparsers.add_parser("health", help="Perform health checks")
    
    # Connect command
    connect_parser = subparsers.add_parser("connect", help="Connect to specific servers")
    connect_parser.add_argument("server_type", choices=["rnaseq", "scrnaseq", "atacseq", "proteomics", "data"],
                              help="Type of server to connect to")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Execute analysis tasks")
    analyze_parser.add_argument("--type", required=True, choices=["rnaseq", "scrnaseq", "atacseq", "proteomics"],
                              help="Type of analysis to run")
    analyze_parser.add_argument("--input-file", help="Input file for analysis")
    analyze_parser.add_argument("--output-dir", help="Output directory for results")
    
    # Agent command
    agent_parser = subparsers.add_parser("agent", help="Interact with the agent system")
    agent_group = agent_parser.add_mutually_exclusive_group(required=True)
    agent_group.add_argument("--chat", help="Chat message to send to agent")
    agent_group.add_argument("--status", action="store_true", help="Get agent status")
    
    # Electron command
    electron_parser = subparsers.add_parser("electron", help="Start Electron UI mode")
    electron_parser.add_argument("--wait", action="store_true", help="Wait for interrupt after starting")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor system performance")
    monitor_parser.add_argument("--interval", type=int, default=5, help="Update interval in seconds")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export system data/metrics")
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument("--include-logs", action="store_true", help="Include system logs")
    
    return parser


async def main():
    """Main entry point for the MCP system CLI"""
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Parse command line arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Create CLI instance
        cli = MCPSystemCLI()
        
        # Handle special case of no command (interactive mode)
        if not args.command:
            config = cli._create_config_from_args(args)
            return await cli.run_interactive_mode(config)
        
        # Handle specific commands
        return await cli.run_cli_mode(args.command, args)
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        return 1


def run_sync():
    """Synchronous wrapper for the main function"""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(run_sync()) 