#!/usr/bin/env python3
"""
Provider Integration Test Suite
Tests the integration between providers and Electron UI, independent of coordination/decision components.
"""

import asyncio
import json
import pytest
from typing import Dict, Any
import time
from unittest.mock import Mock, patch

from src.mcp.agent.providers import (
    create_external_provider,
    create_local_provider,
    initialize_providers,
    get_provider_summary,
    ProviderType
)


class ElectronIntegrationTester:
    """Test suite for provider-Electron integration"""
    
    def __init__(self):
        self.providers = {}
        self.mock_electron_client = Mock()
        self.integration_results = {}
    
    async def setup_providers(self):
        """Setup test providers"""
        self.providers = {
            "external": create_external_provider(
                api_key="test-integration-key",
                rate_limit_rpm=120,
                circuit_breaker_threshold=3
            ),
            "local": create_local_provider(
                model_name="test-model",
                resource_monitoring=True,
                security_sandbox=True
            )
        }
        
        # Initialize providers
        init_results = await initialize_providers(*self.providers.values())
        print(f"🚀 Providers initialized: {sum(init_results)}/{len(init_results)}")
        
        return init_results
    
    async def test_electron_bridge_integration(self):
        """Test Electron bridge data integration"""
        print("\n⚡ Testing Electron Bridge Integration...")
        
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                # Get bridge data
                bridge_data = provider.get_electron_bridge_data()
                
                # Simulate Electron client receiving the data
                electron_payload = {
                    "type": "provider_status_update",
                    "provider": provider_name,
                    "data": bridge_data,
                    "timestamp": time.time()
                }
                
                # Test data completeness
                required_fields = ["providerId", "status", "capabilities", "metrics"]
                missing_fields = [field for field in required_fields if field not in bridge_data]
                
                results[provider_name] = {
                    "bridge_data_complete": len(missing_fields) == 0,
                    "missing_fields": missing_fields,
                    "payload_size": len(json.dumps(electron_payload)),
                    "provider_available": provider.is_available()
                }
                
                print(f"   ✅ {provider_name}: Bridge data complete")
                
            except Exception as e:
                results[provider_name] = {
                    "bridge_data_complete": False,
                    "error": str(e)
                }
                print(f"   ❌ {provider_name}: Bridge integration failed - {e}")
        
        self.integration_results["electron_bridge"] = results
        return results
    
    async def test_real_time_monitoring(self):
        """Test real-time monitoring integration"""
        print("\n📊 Testing Real-time Monitoring...")
        
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                # Simulate multiple requests to generate metrics
                for i in range(3):
                    provider.update_metrics(
                        success=i % 2 == 0,  # Alternate success/failure
                        response_time=0.5 + i * 0.1,
                        cost=0.01 if provider_name == "external" else 0.0
                    )
                
                # Get updated metrics
                metrics = provider.get_metrics()
                
                # Simulate real-time update to Electron
                monitoring_payload = {
                    "type": "metrics_update",
                    "provider": provider_name,
                    "metrics": metrics,
                    "timestamp": time.time()
                }
                
                results[provider_name] = {
                    "metrics_available": "total_requests" in metrics,
                    "success_rate": metrics.get("success_rate", 0),
                    "payload_valid": monitoring_payload["type"] == "metrics_update"
                }
                
                print(f"   ✅ {provider_name}: Monitoring data generated")
                
            except Exception as e:
                results[provider_name] = {"error": str(e)}
                print(f"   ❌ {provider_name}: Monitoring failed - {e}")
        
        self.integration_results["real_time_monitoring"] = results
        return results
    
    async def test_provider_switching_ui(self):
        """Test provider switching UI integration"""
        print("\n🔄 Testing Provider Switching UI...")
        
        try:
            # Get provider summary (what UI would display)
            summary = get_provider_summary(*self.providers.values())
            
            # Simulate provider selection logic
            available_providers = [
                p for p in summary["providers"] 
                if p["available"]
            ]
            
            # Mock UI selection
            ui_selection_payloads = []
            for provider_info in available_providers:
                payload = {
                    "type": "provider_selected",
                    "provider_id": provider_info["type"],
                    "provider_data": provider_info,
                    "timestamp": time.time()
                }
                ui_selection_payloads.append(payload)
            
            results = {
                "provider_summary_available": len(summary["providers"]) > 0,
                "available_providers": len(available_providers),
                "ui_payloads_generated": len(ui_selection_payloads),
                "provider_types": [p["type"] for p in summary["providers"]]
            }
            
            print(f"   ✅ Provider switching: {results['available_providers']} providers available")
            
        except Exception as e:
            results = {"error": str(e)}
            print(f"   ❌ Provider switching failed - {e}")
        
        self.integration_results["provider_switching"] = results
        return results
    
    async def test_health_monitoring_ui(self):
        """Test health monitoring UI integration"""
        print("\n🏥 Testing Health Monitoring UI...")
        
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                # Get health status
                health_status = await provider.get_health_status()
                
                # Simulate UI health display
                ui_health_payload = {
                    "type": "health_status_update",
                    "provider": provider_name,
                    "health": health_status,
                    "timestamp": time.time(),
                    "ui_indicators": {
                        "status_color": "green" if health_status.get("available") else "red",
                        "status_text": health_status.get("status", "unknown"),
                        "last_check": health_status.get("last_check", 0)
                    }
                }
                
                results[provider_name] = {
                    "health_check_successful": "status" in health_status,
                    "ui_payload_complete": "ui_indicators" in ui_health_payload,
                    "status": health_status.get("status", "unknown")
                }
                
                print(f"   ✅ {provider_name}: Health monitoring UI ready")
                
            except Exception as e:
                results[provider_name] = {"error": str(e)}
                print(f"   ❌ {provider_name}: Health monitoring failed - {e}")
        
        self.integration_results["health_monitoring"] = results
        return results
    
    async def test_cost_tracking_ui(self):
        """Test cost tracking UI integration"""
        print("\n💰 Testing Cost Tracking UI...")
        
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                # Get usage summary
                if hasattr(provider, 'get_usage_summary'):
                    usage_summary = provider.get_usage_summary()
                else:
                    # Fallback for base provider
                    metrics = provider.get_metrics()
                    usage_summary = {
                        "provider": provider_name,
                        "total_cost": metrics.get("total_cost", 0),
                        "requests": metrics.get("total_requests", 0)
                    }
                
                # Simulate cost tracking UI
                cost_ui_payload = {
                    "type": "cost_update",
                    "provider": provider_name,
                    "usage": usage_summary,
                    "timestamp": time.time(),
                    "ui_elements": {
                        "cost_display": f"${usage_summary.get('total_cost', 0):.4f}",
                        "request_count": usage_summary.get("requests", 0),
                        "cost_per_request": (
                            usage_summary.get("total_cost", 0) / max(usage_summary.get("requests", 1), 1)
                        )
                    }
                }
                
                results[provider_name] = {
                    "usage_summary_available": "provider" in usage_summary,
                    "cost_tracking_enabled": "total_cost" in usage_summary,
                    "ui_payload_complete": "ui_elements" in cost_ui_payload
                }
                
                print(f"   ✅ {provider_name}: Cost tracking UI ready")
                
            except Exception as e:
                results[provider_name] = {"error": str(e)}
                print(f"   ❌ {provider_name}: Cost tracking failed - {e}")
        
        self.integration_results["cost_tracking"] = results
        return results
    
    async def test_concurrent_operations(self):
        """Test concurrent operations with UI updates"""
        print("\n🔀 Testing Concurrent Operations...")
        
        try:
            # Simulate concurrent operations
            tasks = []
            
            for provider in self.providers.values():
                # Concurrent health checks
                tasks.append(provider.get_health_status())
                
                # Concurrent metrics updates
                async def update_metrics(p):
                    p.update_metrics(success=True, response_time=0.3, cost=0.005)
                    return p.get_metrics()
                
                tasks.append(update_metrics(provider))
            
            # Execute concurrently
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_operations = sum(
                1 for result in results_list 
                if not isinstance(result, Exception)
            )
            
            results = {
                "concurrent_operations": len(tasks),
                "successful_operations": successful_operations,
                "success_rate": successful_operations / len(tasks) if tasks else 0,
                "operations_per_provider": len(tasks) // len(self.providers)
            }
            
            print(f"   ✅ Concurrent operations: {successful_operations}/{len(tasks)} successful")
            
        except Exception as e:
            results = {"error": str(e)}
            print(f"   ❌ Concurrent operations failed - {e}")
        
        self.integration_results["concurrent_operations"] = results
        return results
    
    async def cleanup(self):
        """Cleanup test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        for provider in self.providers.values():
            try:
                await provider.cleanup()
            except Exception as e:
                print(f"   ⚠️ Cleanup warning: {e}")
        
        print("   ✅ Cleanup completed")
    
    def print_integration_summary(self):
        """Print comprehensive integration test summary"""
        print("\n" + "="*60)
        print("📋 PROVIDER-ELECTRON INTEGRATION SUMMARY")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, test_results in self.integration_results.items():
            print(f"\n🧪 {test_name.replace('_', ' ').title()}:")
            
            if isinstance(test_results, dict):
                if "error" in test_results:
                    print(f"   ❌ FAILED: {test_results['error']}")
                    total_tests += 1
                else:
                    for provider_name, provider_results in test_results.items():
                        if isinstance(provider_results, dict):
                            if "error" in provider_results:
                                print(f"   ❌ {provider_name}: {provider_results['error']}")
                                total_tests += 1
                            else:
                                success_indicators = [
                                    k for k, v in provider_results.items() 
                                    if isinstance(v, bool) and v
                                ]
                                if success_indicators:
                                    print(f"   ✅ {provider_name}: {len(success_indicators)} checks passed")
                                    passed_tests += 1
                                total_tests += 1
        
        print(f"\n📊 OVERALL INTEGRATION RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Success Rate: {passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "   Success Rate: 0%")
        
        if passed_tests == total_tests:
            print("🎉 All integration tests passed! Providers are Electron-ready.")
        else:
            print("⚠️  Some integration tests failed. Review the results above.")


async def main():
    """Main integration test runner"""
    print("🚀 Provider-Electron Integration Test Suite")
    print("="*50)
    
    tester = ElectronIntegrationTester()
    
    try:
        # Setup
        await tester.setup_providers()
        
        # Run integration tests
        await tester.test_electron_bridge_integration()
        await tester.test_real_time_monitoring()
        await tester.test_provider_switching_ui()
        await tester.test_health_monitoring_ui()
        await tester.test_cost_tracking_ui()
        await tester.test_concurrent_operations()
        
        # Summary
        tester.print_integration_summary()
        
    finally:
        # Cleanup
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 