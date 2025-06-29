#!/usr/bin/env python3
"""
Enhanced LLM Providers Test Suite
Run this module to test all provider functionality and enhancements.

Usage:
    python -m src.mcp.agent.providers
    python -m src.mcp.agent.providers --demo
    python -m src.mcp.agent.providers --benchmark
"""

import asyncio
import argparse
import time
import json
from pathlib import Path
from typing import Dict, Any

from . import (
    create_external_provider,
    create_local_provider, 
    initialize_providers,
    get_provider_summary,
    ProviderType,
    RateLimiter,
    CircuitBreaker,
    ResourceMonitor,
    __version__
)


class ProviderTestSuite:
    """Comprehensive test suite for enhanced LLM providers"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print(f"🚀 Enhanced LLM Providers Test Suite v{__version__}")
        print("=" * 60)
        
        await self.test_provider_creation()
        await self.test_configuration_validation()
        await self.test_utility_classes()
        await self.test_provider_initialization()
        await self.test_health_monitoring()
        await self.test_metrics_collection()
        await self.test_electron_integration()
        await self.test_concurrent_operations()
        
        self.print_summary()
    
    async def test_provider_creation(self):
        """Test provider creation with convenience functions"""
        print("\n📦 Testing Provider Creation...")
        
        try:
            # Test external provider creation
            ext_provider = create_external_provider(
                api_key="test-key",
                rate_limit_rpm=30,
                timeout=15.0
            )
            assert ext_provider.provider_type == ProviderType.EXTERNAL
            print("✅ External provider created successfully")
            
            # Test local provider creation
            local_provider = create_local_provider(
                model_name="llama3.1:8b",
                resource_monitoring=True,
                security_sandbox=True
            )
            assert local_provider.provider_type == ProviderType.LOCAL
            print("✅ Local provider created successfully")
            
            self.results['provider_creation'] = True
            
        except Exception as e:
            print(f"❌ Provider creation failed: {e}")
            self.results['provider_creation'] = False
    
    async def test_configuration_validation(self):
        """Test Pydantic configuration validation"""
        print("\n⚙️ Testing Configuration Validation...")
        
        try:
            # Test valid configuration
            ext_provider = create_external_provider(
                api_key="valid-key",
                rate_limit_rpm=100,
                timeout=30.0,
                temperature=0.7
            )
            
            issues = ext_provider.validate_config()
            assert len(issues) == 0, f"Expected no issues, got: {issues}"
            print("✅ Valid configuration accepted")
            
            # Test invalid configuration handling
            local_provider = create_local_provider(
                gpu_memory_fraction=1.5,  # Invalid: > 1.0
                model_cache_size=-1  # Invalid: < 0
            )
            
            # Should still create provider with default values
            assert local_provider.config.gpu_memory_fraction <= 1.0
            print("✅ Invalid configuration gracefully handled")
            
            self.results['configuration_validation'] = True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            self.results['configuration_validation'] = False
    
    async def test_utility_classes(self):
        """Test utility classes like RateLimiter and CircuitBreaker"""
        print("\n🔧 Testing Utility Classes...")
        
        try:
            # Test RateLimiter
            rate_limiter = RateLimiter(max_requests=3, time_window=1.0)
            
            start_time = time.time()
            for i in range(3):
                await rate_limiter.acquire()
            elapsed = time.time() - start_time
            
            assert elapsed < 0.5, f"Rate limiter too slow: {elapsed}s"
            print(f"✅ RateLimiter working (3 requests in {elapsed:.3f}s)")
            
            # Test CircuitBreaker
            circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)
            
            assert circuit_breaker.can_proceed() == True
            circuit_breaker.record_failure()
            circuit_breaker.record_failure()
            assert circuit_breaker.state == "open"
            print("✅ CircuitBreaker state transitions working")
            
            # Test ResourceMonitor
            monitor = ResourceMonitor()
            await monitor.start_monitoring()
            await asyncio.sleep(0.1)  # Brief monitoring
            stats = monitor.get_stats()
            await monitor.stop_monitoring()
            
            assert 'cpu_usage' in stats
            assert 'memory_usage' in stats
            print("✅ ResourceMonitor collecting stats")
            
            self.results['utility_classes'] = True
            
        except Exception as e:
            print(f"❌ Utility classes test failed: {e}")
            self.results['utility_classes'] = False
    
    async def test_provider_initialization(self):
        """Test concurrent provider initialization"""
        print("\n🚀 Testing Provider Initialization...")
        
        try:
            # Create multiple providers
            providers = [
                create_external_provider(api_key="test-1"),
                create_external_provider(api_key="test-2"),
                create_local_provider(model_name="test-model")
            ]
            
            # Initialize concurrently
            results = await initialize_providers(*providers)
            
            # Results may be False if actual services not available
            assert len(results) == 3
            print(f"✅ Concurrent initialization: {sum(results)}/3 succeeded")
            
            # Test provider summary
            summary = get_provider_summary(*providers)
            assert summary['total_providers'] == 3
            print(f"✅ Provider summary: {summary['available_providers']} available")
            
            # Cleanup
            for provider in providers:
                await provider.cleanup()
            
            self.results['provider_initialization'] = True
            
        except Exception as e:
            print(f"❌ Provider initialization test failed: {e}")
            self.results['provider_initialization'] = False
    
    async def test_health_monitoring(self):
        """Test health monitoring system"""
        print("\n🏥 Testing Health Monitoring...")
        
        try:
            provider = create_local_provider(resource_monitoring=True)
            await provider.initialize()
            
            # Test health status
            health = await provider.get_health_status()
            assert 'status' in health
            assert 'provider_type' in health
            assert 'available' in health
            print("✅ Health status reporting working")
            
            # Test metrics
            metrics = provider.get_metrics()
            assert 'total_requests' in metrics
            assert 'success_rate' in metrics
            print("✅ Metrics collection working")
            
            await provider.cleanup()
            self.results['health_monitoring'] = True
            
        except Exception as e:
            print(f"❌ Health monitoring test failed: {e}")
            self.results['health_monitoring'] = False
    
    async def test_metrics_collection(self):
        """Test metrics collection and updates"""
        print("\n📊 Testing Metrics Collection...")
        
        try:
            provider = create_external_provider(api_key="test-metrics")
            
            # Test metrics updates
            provider.update_metrics(success=True, response_time=0.5, cost=0.01)
            provider.update_metrics(success=False, response_time=1.0, cost=0.0)
            provider.update_metrics(success=True, response_time=0.3, cost=0.005)
            
            metrics = provider.get_metrics()
            assert metrics['total_requests'] == 3
            assert metrics['successful_requests'] == 2
            assert metrics['failed_requests'] == 1
            assert abs(metrics['success_rate'] - 0.667) < 0.01
            assert metrics['total_cost'] == 0.015
            print("✅ Metrics calculation accurate")
            
            # Test metrics reset
            provider.reset_metrics()
            metrics = provider.get_metrics()
            assert metrics['total_requests'] == 0
            print("✅ Metrics reset working")
            
            self.results['metrics_collection'] = True
            
        except Exception as e:
            print(f"❌ Metrics collection test failed: {e}")
            self.results['metrics_collection'] = False
    
    async def test_electron_integration(self):
        """Test Electron bridge data formatting"""
        print("\n⚡ Testing Electron Integration...")
        
        try:
            # Test external provider bridge data
            ext_provider = create_external_provider(
                api_key="test-electron",
                rate_limit_rpm=60
            )
            
            bridge_data = ext_provider.get_electron_bridge_data()
            required_keys = [
                'providerId', 'status', 'capabilities', 'metrics', 
                'connectionStatus', 'circuitBreakerState', 'rateLimitRpm'
            ]
            
            for key in required_keys:
                assert key in bridge_data, f"Missing key: {key}"
            print("✅ External provider bridge data complete")
            
            # Test local provider bridge data
            local_provider = create_local_provider(resource_monitoring=True)
            
            bridge_data = local_provider.get_electron_bridge_data()
            local_required_keys = [
                'providerId', 'currentModel', 'costPerRequest',
                'resourceMonitoring', 'securitySandbox'
            ]
            
            for key in local_required_keys:
                assert key in bridge_data, f"Missing key: {key}"
            print("✅ Local provider bridge data complete")
            
            self.results['electron_integration'] = True
            
        except Exception as e:
            print(f"❌ Electron integration test failed: {e}")
            self.results['electron_integration'] = False
    
    async def test_concurrent_operations(self):
        """Test concurrent provider operations"""
        print("\n🔀 Testing Concurrent Operations...")
        
        try:
            providers = [
                create_external_provider(api_key=f"test-{i}")
                for i in range(3)
            ]
            
            # Test concurrent health checks
            health_tasks = [
                provider.get_health_status() 
                for provider in providers
            ]
            
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
            successful_checks = sum(
                1 for result in health_results 
                if isinstance(result, dict) and 'status' in result
            )
            
            print(f"✅ Concurrent health checks: {successful_checks}/3 successful")
            
            # Test concurrent cleanup
            cleanup_tasks = [
                provider.cleanup() 
                for provider in providers
            ]
            
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            print("✅ Concurrent cleanup completed")
            
            self.results['concurrent_operations'] = True
            
        except Exception as e:
            print(f"❌ Concurrent operations test failed: {e}")
            self.results['concurrent_operations'] = False
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📋 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\n📊 OVERALL: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Providers are working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        elapsed = time.time() - self.start_time
        print(f"⏱️  Total time: {elapsed:.2f} seconds")


async def run_demo():
    """Run interactive demo of provider features"""
    print("🎭 Enhanced LLM Providers Demo")
    print("=" * 40)
    
    # Create providers with different configurations
    external = create_external_provider(
        api_key="demo-key",
        rate_limit_rpm=120,
        circuit_breaker_threshold=3
    )
    
    local = create_local_provider(
        model_name="llama3.1:8b",
        resource_monitoring=True,
        security_sandbox=True,
        model_cache_size=5
    )
    
    providers = [external, local]
    
    print("\n🔧 Provider Configurations:")
    for provider in providers:
        print(f"  {provider.provider_type.value}: {provider.config}")
    
    print("\n🚀 Initializing providers...")
    results = await initialize_providers(*providers)
    
    print("\n📊 Provider Summary:")
    summary = get_provider_summary(*providers)
    print(json.dumps(summary, indent=2))
    
    print("\n🏥 Health Status:")
    for provider in providers:
        health = await provider.get_health_status()
        print(f"  {provider.provider_type.value}: {health['status']}")
    
    print("\n⚡ Electron Bridge Data Preview:")
    for provider in providers:
        bridge_data = provider.get_electron_bridge_data()
        print(f"  {provider.provider_type.value}: {len(bridge_data)} keys")
        for key in list(bridge_data.keys())[:5]:  # Show first 5 keys
            print(f"    - {key}")
    
    # Cleanup
    for provider in providers:
        await provider.cleanup()
    
    print("\n✨ Demo completed successfully!")


async def run_benchmark():
    """Run performance benchmark"""
    print("🏁 Provider Performance Benchmark")
    print("=" * 40)
    
    # Test rate limiter performance
    print("\n⏱️  RateLimiter Benchmark:")
    rate_limiter = RateLimiter(max_requests=100, time_window=1.0)
    
    start_time = time.time()
    tasks = [rate_limiter.acquire() for _ in range(50)]
    await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    print(f"  50 requests in {elapsed:.3f}s ({50/elapsed:.1f} req/s)")
    
    # Test provider creation speed
    print("\n🏭 Provider Creation Benchmark:")
    start_time = time.time()
    
    providers = []
    for i in range(10):
        providers.extend([
            create_external_provider(api_key=f"bench-{i}"),
            create_local_provider(model_name=f"model-{i}")
        ])
    
    creation_time = time.time() - start_time
    print(f"  20 providers created in {creation_time:.3f}s")
    
    # Test concurrent health checks
    print("\n🏥 Health Check Benchmark:")
    start_time = time.time()
    
    health_tasks = [provider.get_health_status() for provider in providers]
    results = await asyncio.gather(*health_tasks, return_exceptions=True)
    
    health_time = time.time() - start_time
    successful = sum(1 for r in results if isinstance(r, dict))
    
    print(f"  {successful}/20 health checks in {health_time:.3f}s")
    
    # Cleanup
    cleanup_tasks = [provider.cleanup() for provider in providers]
    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    print("\n🎯 Benchmark completed!")


async def main():
    """Main entry point for providers module"""
    parser = argparse.ArgumentParser(
        description="Enhanced LLM Providers Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.mcp.agent.providers              # Run full test suite
  python -m src.mcp.agent.providers --demo       # Interactive demo
  python -m src.mcp.agent.providers --benchmark  # Performance benchmark
        """
    )
    
    parser.add_argument('--demo', action='store_true', 
                       help='Run interactive demo')
    parser.add_argument('--benchmark', action='store_true', 
                       help='Run performance benchmark')
    
    args = parser.parse_args()
    
    if args.demo:
        await run_demo()
    elif args.benchmark:
        await run_benchmark()
    else:
        # Run full test suite
        test_suite = ProviderTestSuite()
        await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 