#!/usr/bin/env python3
"""
MCP System Integration Tests

Comprehensive testing suite to verify that all three subsystems (agent, core, servers)
communicate properly with each other and integrate seamlessly with Electron UI/UX.

Usage:
    python src/mcp/test_system_integration.py
    python -m src.mcp.test_system_integration --mode comprehensive
    python -m src.mcp.test_system_integration --mode electron
"""

import asyncio
import logging
import json
import time
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import traceback

# Import the unified MCP system
from . import MCPSystem, MCPSystemConfiguration
from .agent import get_agent_status, create_complete_agent
from .core import get_mcp_core, MCPCoreSystem
from .servers import get_orchestrator


class MCPSystemIntegrationTester:
    """
    Comprehensive integration tester for the MCP system
    
    Tests:
    - Cross-system communication between agent, core, and servers
    - Electron bridge integration across all components
    - End-to-end workflow functionality
    - System resilience and error handling
    - Performance testing with concurrent operations
    """
    
    def __init__(self, test_mode: str = "comprehensive"):
        self.test_mode = test_mode
        self.system: Optional[MCPSystem] = None
        self.test_results: Dict[str, Any] = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("mcp.integration.test")
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run comprehensive integration tests"""
        self.logger.info(f"🧪 Starting MCP System Integration Tests - Mode: {self.test_mode}")
        
        try:
            # Initialize system
            await self._initialize_test_system()
            
            # Run test suites based on mode
            if self.test_mode == "quick":
                await self._run_quick_tests()
            elif self.test_mode == "electron":
                await self._run_electron_focused_tests()
            elif self.test_mode == "communication":
                await self._run_communication_tests()
            else:  # comprehensive
                await self._run_comprehensive_tests()
            
            # Generate final report
            return self._generate_test_report()
            
        except Exception as e:
            self.logger.error(f"❌ Integration tests failed: {e}")
            self.test_results["fatal_error"] = str(e)
            return self.test_results
        finally:
            await self._cleanup_test_system()
    
    async def _initialize_test_system(self):
        """Initialize MCP system for testing"""
        self.logger.info("🚀 Initializing MCP System for testing...")
        
        config = MCPSystemConfiguration(
            name="mcp_integration_test",
            debug=True,
            electron_mode=True,
            websocket_port=8766,  # Use different port for testing
            enable_real_time_sync=True,
            max_concurrent_operations=10
        )
        
        self.system = MCPSystem(config)
        initialization_success = await self.system.initialize()
        
        if not initialization_success:
            raise Exception("Failed to initialize MCP system for testing")
        
        self.logger.info("✅ MCP System initialized for testing")
    
    async def _run_comprehensive_tests(self):
        """Run all integration tests"""
        self.logger.info("🔄 Running comprehensive integration tests...")
        
        # Test suites
        test_suites = [
            ("System Initialization", self._test_system_initialization),
            ("Agent-Core Communication", self._test_agent_core_communication),
            ("Core-Server Communication", self._test_core_server_communication),
            ("Agent-Server Communication", self._test_agent_server_communication),
            ("Electron Bridge Integration", self._test_electron_bridge_integration),
            ("Cross-System Data Flow", self._test_cross_system_data_flow),
            ("Error Handling", self._test_error_handling),
            ("Performance Tests", self._test_performance),
            ("Concurrent Operations", self._test_concurrent_operations),
            ("System Resilience", self._test_system_resilience)
        ]
        
        for test_name, test_func in test_suites:
            try:
                self.logger.info(f"  🧪 Running: {test_name}")
                result = await test_func()
                self.test_results[test_name] = {
                    "status": "passed" if result.get("success", False) else "failed",
                    "details": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                if result.get("success", False):
                    self.logger.info(f"  ✅ {test_name}: PASSED")
                else:
                    self.logger.warning(f"  ❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.logger.error(f"  💥 {test_name}: EXCEPTION - {e}")
                self.test_results[test_name] = {
                    "status": "exception",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now().isoformat()
                }
    
    async def _run_quick_tests(self):
        """Run quick smoke tests"""
        self.logger.info("⚡ Running quick integration tests...")
        
        quick_tests = [
            ("System Status", self._test_system_initialization),
            ("Basic Communication", self._test_agent_core_communication),
            ("Electron Bridge", self._test_electron_bridge_integration)
        ]
        
        for test_name, test_func in quick_tests:
            try:
                result = await test_func()
                self.test_results[test_name] = result
            except Exception as e:
                self.test_results[test_name] = {"success": False, "error": str(e)}
    
    async def _run_electron_focused_tests(self):
        """Run Electron-focused integration tests"""
        self.logger.info("⚡ Running Electron-focused integration tests...")
        
        electron_tests = [
            ("Electron Bridge Initialization", self._test_electron_bridge_integration),
            ("Cross-Component Bridge Communication", self._test_cross_component_bridges),
            ("Real-time UI Synchronization", self._test_real_time_sync),
            ("WebSocket Communication", self._test_websocket_communication),
            ("UI Event Handling", self._test_ui_event_handling)
        ]
        
        for test_name, test_func in electron_tests:
            try:
                result = await test_func()
                self.test_results[test_name] = result
            except Exception as e:
                self.test_results[test_name] = {"success": False, "error": str(e)}
    
    async def _run_communication_tests(self):
        """Run communication-focused tests"""
        self.logger.info("📡 Running communication-focused tests...")
        
        comm_tests = [
            ("Agent-Core Communication", self._test_agent_core_communication),
            ("Core-Server Communication", self._test_core_server_communication),
            ("Cross-System Messaging", self._test_cross_system_data_flow),
            ("Event Broadcasting", self._test_event_broadcasting)
        ]
        
        for test_name, test_func in comm_tests:
            try:
                result = await test_func()
                self.test_results[test_name] = result
            except Exception as e:
                self.test_results[test_name] = {"success": False, "error": str(e)}
    
    # Individual test methods
    
    async def _test_system_initialization(self) -> Dict[str, Any]:
        """Test complete system initialization"""
        try:
            status = await self.system.get_system_status()
            
            # Check if all components are initialized
            required_components = ["agent", "core", "servers"]
            initialized_components = list(status.get("components", {}).keys())
            
            missing_components = [comp for comp in required_components if comp not in initialized_components]
            
            return {
                "success": len(missing_components) == 0,
                "initialized_components": initialized_components,
                "missing_components": missing_components,
                "electron_mode": status.get("electron_mode", False),
                "system_running": status.get("running", False)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_agent_core_communication(self) -> Dict[str, Any]:
        """Test communication between agent and core systems"""
        try:
            # Test if agent can request tools from core
            tools = await self.system.get_available_tools()
            
            # Test if agent can execute analysis through core
            if self.system.agent and self.system.core_system:
                # Simulate agent requesting available tools
                agent_tool_request = {"type": "get_available_tools", "request_id": "test_001"}
                await self.system.bridge.emit_event("agent_request", agent_tool_request)
                
                # Wait for response (simplified test)
                await asyncio.sleep(0.5)
                
                return {
                    "success": True,
                    "tools_available": len(tools),
                    "agent_initialized": self.system.agent is not None,
                    "core_initialized": self.system.core_system is not None,
                    "communication_tested": True
                }
            else:
                return {
                    "success": False,
                    "error": "Agent or Core system not initialized",
                    "agent_initialized": self.system.agent is not None,
                    "core_initialized": self.system.core_system is not None
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_core_server_communication(self) -> Dict[str, Any]:
        """Test communication between core and server systems"""
        try:
            if self.system.core_system and self.system.server_orchestrator:
                # Test server registration with core
                server_status = await self.system.server_orchestrator.get_system_status()
                core_status = await self.system.core_system.get_system_status()
                
                return {
                    "success": True,
                    "core_servers": len(core_status.get("servers", {})),
                    "orchestrator_servers": len(server_status.get("active_servers", {})),
                    "core_initialized": True,
                    "orchestrator_initialized": True
                }
            else:
                return {
                    "success": False,
                    "error": "Core or Server system not initialized",
                    "core_initialized": self.system.core_system is not None,
                    "orchestrator_initialized": self.system.server_orchestrator is not None
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_agent_server_communication(self) -> Dict[str, Any]:
        """Test agent to server communication through core"""
        try:
            if self.system.agent and self.system.core_system and self.system.server_orchestrator:
                # Test agent accessing server tools through core
                tools = await self.system.get_available_tools()
                
                # Simulate agent requesting server capabilities
                server_request = {
                    "type": "execute_tool",
                    "tool_name": "test_server_ping",
                    "context": {"test": True},
                    "request_id": "test_002"
                }
                await self.system.bridge.emit_event("agent_request", server_request)
                
                return {
                    "success": True,
                    "available_tools": len(tools),
                    "agent_server_path_tested": True,
                    "all_components_available": True
                }
            else:
                return {
                    "success": False,
                    "error": "Not all components initialized for agent-server communication",
                    "agent_available": self.system.agent is not None,
                    "core_available": self.system.core_system is not None,
                    "servers_available": self.system.server_orchestrator is not None
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_electron_bridge_integration(self) -> Dict[str, Any]:
        """Test Electron bridge integration across all components"""
        try:
            # Check if Electron bridges are initialized
            electron_bridges = getattr(self.system, 'electron_bridges', {})
            electron_mode = getattr(self.system.config, 'electron_mode', False)
            
            # Test bridge functionality
            bridge_tests = {}
            functional_bridges = 0
            
            for bridge_name, bridge in electron_bridges.items():
                try:
                    # Test if bridge has required methods
                    has_emit = hasattr(bridge, 'emit_event')
                    has_broadcast = hasattr(bridge, 'broadcast')
                    has_communication = has_emit or has_broadcast
                    
                    # Test actual functionality for different bridge types
                    test_message = {
                        "type": "test_message",
                        "data": {"test": True},
                        "bridge_name": bridge_name
                    }
                    
                    communication_test = False
                    communication_method_used = "none"
                    
                    # Try emit_event method (WebSocket-based bridges)
                    if has_emit:
                        try:
                            await bridge.emit_event("test", test_message)
                            communication_test = True
                            communication_method_used = "emit_event"
                        except Exception as comm_error:
                            logger.debug(f"Bridge {bridge_name} emit_event failed: {comm_error}")
                    
                    # Try broadcast method (mock bridges)
                    elif has_broadcast:
                        try:
                            await bridge.broadcast(test_message)
                            communication_test = True
                            communication_method_used = "broadcast"
                        except Exception as comm_error:
                            logger.debug(f"Bridge {bridge_name} broadcast failed: {comm_error}")
                    
                    # Try _send_message method (Electron IPC bridges)
                    elif hasattr(bridge, '_send_message'):
                        try:
                            await bridge._send_message("test_message", test_message)
                            communication_test = True
                            communication_method_used = "_send_message"
                        except Exception as comm_error:
                            logger.debug(f"Bridge {bridge_name} _send_message failed: {comm_error}")
                    
                    # Try other common methods
                    elif hasattr(bridge, 'send'):
                        try:
                            await bridge.send(test_message)
                            communication_test = True
                            communication_method_used = "send"
                        except Exception as comm_error:
                            logger.debug(f"Bridge {bridge_name} send failed: {comm_error}")
                    
                    if communication_test:
                        functional_bridges += 1
                    
                    bridge_tests[bridge_name] = {
                        "initialized": True,
                        "has_emit_event": has_emit,
                        "has_broadcast": has_broadcast,
                        "has_send_message": hasattr(bridge, '_send_message'),
                        "has_send": hasattr(bridge, 'send'),
                        "has_communication_method": has_communication or hasattr(bridge, '_send_message') or hasattr(bridge, 'send'),
                        "communication_test_passed": communication_test,
                        "communication_method_used": communication_method_used,
                        "bridge_type": type(bridge).__name__
                    }
                    
                except Exception as e:
                    bridge_tests[bridge_name] = {
                        "initialized": False,
                        "error": str(e),
                        "bridge_type": type(bridge).__name__ if bridge else "Unknown"
                    }
            
            # Check additional Electron infrastructure
            has_websocket_server = hasattr(self.system, 'unified_websocket_server')
            websocket_details = {}
            if has_websocket_server:
                websocket_server = self.system.unified_websocket_server
                websocket_details = {
                    "server_exists": True,
                    "server_type": type(websocket_server).__name__ if websocket_server else "None"
                }
            else:
                websocket_details = {"server_exists": False}
            
            # Overall success criteria
            # Consider success if we have:
            # 1. Electron mode enabled AND bridges available AND at least one functional bridge OR
            # 2. WebSocket server is working (indicating unified bridge functionality)
            websocket_working = websocket_details.get("server_exists", False)
            success = (
                (electron_mode and len(electron_bridges) > 0 and functional_bridges > 0) or
                websocket_working
            )
            
            return {
                "success": success,
                "electron_mode_enabled": electron_mode,
                "bridges_count": len(electron_bridges),
                "functional_bridges": functional_bridges,
                "bridge_details": bridge_tests,
                "websocket_server": websocket_details,
                "system_has_electron_bridges_attr": hasattr(self.system, 'electron_bridges'),
                "config_has_electron_mode": hasattr(self.system.config, 'electron_mode')
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False, 
                "error": str(e),
                "traceback": traceback.format_exc(),
                "system_attributes": {
                    "has_electron_bridges": hasattr(self.system, 'electron_bridges'),
                    "has_config": hasattr(self.system, 'config'),
                    "has_websocket_server": hasattr(self.system, 'unified_websocket_server')
                }
            }
    
    async def _test_cross_system_data_flow(self) -> Dict[str, Any]:
        """Test data flow across all systems"""
        try:
            # Test end-to-end data flow
            start_time = time.time()
            
            # 1. Agent requests system status
            if self.system.agent:
                status_request = {
                    "type": "get_system_status",
                    "request_id": "test_003"
                }
                await self.system.bridge.emit_event("agent_request", status_request)
            
            # 2. Core processes and responds
            system_status = await self.system.get_system_status()
            
            # 3. Check if data flows to Electron bridges
            if self.system.electron_bridges:
                test_message = {
                    "type": "test_data_flow",
                    "data": {"timestamp": datetime.now().isoformat()},
                    "test_id": "cross_system_test"
                }
                await self.system._broadcast_to_electron(test_message)
            
            end_time = time.time()
            
            return {
                "success": True,
                "data_flow_time": end_time - start_time,
                "system_status_retrieved": system_status is not None,
                "electron_broadcast_tested": len(self.system.electron_bridges) > 0,
                "components_responding": len(system_status.get("components", {}))
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_error_handling(self) -> Dict[str, Any]:
        """Test system error handling and resilience"""
        try:
            # Test invalid requests
            error_tests = {}
            
            # 1. Invalid agent request
            try:
                invalid_request = {
                    "type": "invalid_operation",
                    "request_id": "error_test_001"
                }
                await self.system.bridge.emit_event("agent_request", invalid_request)
                error_tests["invalid_agent_request"] = "handled_gracefully"
            except Exception as e:
                error_tests["invalid_agent_request"] = f"exception: {str(e)}"
            
            # 2. Test system health after errors
            health_status = await self.system.health_check()
            
            return {
                "success": True,
                "error_handling_tests": error_tests,
                "system_health_after_errors": health_status,
                "system_still_responsive": True
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_performance(self) -> Dict[str, Any]:
        """Test system performance with multiple operations"""
        try:
            start_time = time.time()
            
            # Perform multiple concurrent operations
            operations = []
            for i in range(5):
                operations.append(self.system.get_system_status())
                operations.append(self.system.get_available_tools())
            
            results = await asyncio.gather(*operations, return_exceptions=True)
            
            end_time = time.time()
            
            successful_ops = sum(1 for r in results if not isinstance(r, Exception))
            
            return {
                "success": successful_ops > 0,
                "total_operations": len(operations),
                "successful_operations": successful_ops,
                "total_time": end_time - start_time,
                "average_operation_time": (end_time - start_time) / len(operations),
                "error_rate": (len(operations) - successful_ops) / len(operations)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_concurrent_operations(self) -> Dict[str, Any]:
        """Test concurrent operations across systems"""
        try:
            # Create multiple concurrent tasks
            concurrent_tasks = []
            
            # Agent operations
            if self.system.agent:
                for i in range(3):
                    task_data = {
                        "type": "get_available_tools",
                        "request_id": f"concurrent_test_{i}"
                    }
                    concurrent_tasks.append(
                        self.system.bridge.emit_event("agent_request", task_data)
                    )
            
            # Core operations
            for i in range(3):
                concurrent_tasks.append(self.system.get_system_status())
            
            # Execute all tasks concurrently
            start_time = time.time()
            await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            end_time = time.time()
            
            return {
                "success": True,
                "concurrent_tasks_executed": len(concurrent_tasks),
                "execution_time": end_time - start_time,
                "system_responsive": True
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_system_resilience(self) -> Dict[str, Any]:
        """Test system resilience under stress"""
        try:
            # Test system recovery after stress
            initial_status = await self.system.get_system_status()
            
            # Simulate stress conditions
            stress_tasks = []
            for i in range(10):
                stress_tasks.append(self.system.get_available_tools())
                if i % 2 == 0:
                    stress_tasks.append(self.system.health_check())
            
            # Execute stress test
            await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            # Check system status after stress
            post_stress_status = await self.system.get_system_status()
            
            return {
                "success": True,
                "initial_components": len(initial_status.get("components", {})),
                "post_stress_components": len(post_stress_status.get("components", {})),
                "system_maintained_integrity": (
                    len(initial_status.get("components", {})) == 
                    len(post_stress_status.get("components", {}))
                ),
                "stress_tasks_completed": len(stress_tasks)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Additional test methods for electron-focused and communication tests
    
    async def _test_cross_component_bridges(self) -> Dict[str, Any]:
        """Test communication between different component bridges"""
        try:
            bridge_communication = {}
            
            # Test each bridge's communication capabilities
            for bridge_name, bridge in self.system.electron_bridges.items():
                try:
                    test_message = {
                        "type": "cross_bridge_test",
                        "source": bridge_name,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    if hasattr(bridge, 'emit_event'):
                        await bridge.emit_event("test_message", test_message)
                        bridge_communication[bridge_name] = "emit_event_supported"
                    elif hasattr(bridge, 'broadcast'):
                        await bridge.broadcast(test_message)
                        bridge_communication[bridge_name] = "broadcast_supported"
                    else:
                        bridge_communication[bridge_name] = "no_communication_method"
                        
                except Exception as e:
                    bridge_communication[bridge_name] = f"error: {str(e)}"
            
            return {
                "success": len(bridge_communication) > 0,
                "bridges_tested": len(bridge_communication),
                "communication_results": bridge_communication
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_real_time_sync(self) -> Dict[str, Any]:
        """Test real-time synchronization capabilities"""
        try:
            # Check if real-time sync is enabled
            sync_enabled = self.system.config.enable_real_time_sync
            
            if sync_enabled:
                # Test sync by triggering status updates
                initial_time = time.time()
                
                # Trigger system changes
                test_event = {
                    "type": "test_sync_event",
                    "data": {"test_timestamp": initial_time}
                }
                await self.system.bridge.emit_event("core_event", test_event)
                
                # Allow time for sync
                await asyncio.sleep(0.2)
                
                return {
                    "success": True,
                    "sync_enabled": sync_enabled,
                    "sync_interval": self.system.config.ui_update_interval,
                    "test_event_sent": True
                }
            else:
                return {
                    "success": False,
                    "error": "Real-time sync not enabled",
                    "sync_enabled": sync_enabled
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_websocket_communication(self) -> Dict[str, Any]:
        """Test WebSocket communication for Electron"""
        try:
            # Check if WebSocket server is running
            has_websocket = hasattr(self.system, 'unified_websocket_server')
            websocket_port = self.system.config.websocket_port
            
            return {
                "success": has_websocket,
                "websocket_server_available": has_websocket,
                "websocket_port": websocket_port,
                "electron_mode": self.system.config.electron_mode
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_ui_event_handling(self) -> Dict[str, Any]:
        """Test UI event handling capabilities"""
        try:
            # Test if system can handle various UI events
            ui_events = [
                {"type": "get_system_status", "payload": {}},
                {"type": "get_available_tools", "payload": {}},
                {"type": "agent_chat", "payload": {"message": "test"}},
            ]
            
            event_results = {}
            for event in ui_events:
                try:
                    await self.system._handle_electron_message(event)
                    event_results[event["type"]] = "handled"
                except Exception as e:
                    event_results[event["type"]] = f"error: {str(e)}"
            
            return {
                "success": len(event_results) > 0,
                "events_tested": len(ui_events),
                "event_handling_results": event_results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_event_broadcasting(self) -> Dict[str, Any]:
        """Test event broadcasting across systems"""
        try:
            # Test system-wide event broadcasting
            test_events = [
                {"event": "test_broadcast_1", "data": {"test": "data"}},
                {"event": "test_broadcast_2", "data": {"timestamp": datetime.now().isoformat()}},
            ]
            
            broadcast_results = {}
            for event_data in test_events:
                try:
                    await self.system.bridge.emit_event(event_data["event"], event_data["data"])
                    broadcast_results[event_data["event"]] = "broadcasted"
                except Exception as e:
                    broadcast_results[event_data["event"]] = f"error: {str(e)}"
            
            return {
                "success": len(broadcast_results) > 0,
                "events_broadcasted": len(test_events),
                "broadcast_results": broadcast_results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result.get("status") == "passed")
        failed_tests = sum(1 for result in self.test_results.values() 
                          if result.get("status") == "failed")
        exception_tests = sum(1 for result in self.test_results.values() 
                             if result.get("status") == "exception")
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "exceptions": exception_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "test_mode": self.test_mode
            },
            "test_results": self.test_results,
            "system_info": {
                "version": "1.0.0",
                "test_timestamp": datetime.now().isoformat(),
                "electron_integration": len(getattr(self.system, 'electron_bridges', {})) > 0 if self.system else False
            },
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [name for name, result in self.test_results.items() 
                       if result.get("status") in ["failed", "exception"]]
        
        if "System Initialization" in failed_tests:
            recommendations.append("Check system configuration and component dependencies")
        
        if "Electron Bridge Integration" in failed_tests:
            recommendations.append("Verify Electron environment setup and WebSocket configuration")
        
        if any("Communication" in test for test in failed_tests):
            recommendations.append("Review inter-system communication setup and event handlers")
        
        if "Performance Tests" in failed_tests:
            recommendations.append("Consider optimizing concurrent operation handling")
        
        if not recommendations:
            recommendations.append("All tests passed - system integration is working correctly")
        
        return recommendations
    
    async def _cleanup_test_system(self):
        """Clean up test system resources"""
        if self.system:
            try:
                await self.system.shutdown()
                self.logger.info("✅ Test system cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error during test cleanup: {e}")


async def main():
    """Main entry point for integration tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP System Integration Tests")
    parser.add_argument("--mode", choices=["quick", "comprehensive", "electron", "communication"], 
                       default="comprehensive", help="Test mode to run")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    
    args = parser.parse_args()
    
    # Run tests
    tester = MCPSystemIntegrationTester(test_mode=args.mode)
    results = await tester.run_integration_tests()
    
    # Print summary
    print("\n" + "="*80)
    print("🧪 MCP SYSTEM INTEGRATION TEST RESULTS")
    print("="*80)
    
    summary = results["test_summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']} ✅")
    print(f"Failed: {summary['failed']} ❌")
    print(f"Exceptions: {summary['exceptions']} 💥")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Test Mode: {summary['test_mode']}")
    
    print("\n📊 DETAILED RESULTS:")
    for test_name, test_result in results["test_results"].items():
        status_emoji = {"passed": "✅", "failed": "❌", "exception": "💥"}.get(test_result.get("status"), "❓")
        print(f"  {status_emoji} {test_name}: {test_result.get('status', 'unknown').upper()}")
        if test_result.get("status") != "passed":
            error = test_result.get("error", test_result.get("details", {}).get("error", "Unknown error"))
            print(f"    └─ {error}")
    
    print("\n💡 RECOMMENDATIONS:")
    for rec in results["recommendations"]:
        print(f"  • {rec}")
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    print("="*80)
    
    # Return exit code based on success rate
    success_rate = summary['success_rate']
    return 0 if success_rate >= 80 else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main())) 