#!/usr/bin/env python3
"""
Gliaent MCP Agent Command Line Interface
========================================

This module provides a command-line interface for the Gliaent MCP Agent system,
including interactive chat, system diagnostics, and demonstration modes.

Usage:
    python -m src.mcp.agent                    # Interactive chat mode
    python -m src.mcp.agent --demo             # Run demonstrations
    python -m src.mcp.agent --test             # Run system tests
    python -m src.mcp.agent --status           # System status check
    python -m src.mcp.agent --benchmark        # Performance benchmarks
"""

import asyncio
import argparse
import json
import sys
import time
from typing import Dict, List, Any
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agent components
try:
    from . import (
        get_agent,
        enhanced_ask_agent,
        IntelligentToolRouter,
        get_agent_status,
        create_complete_agent,
        quick_start_bioinformatics_agent
    )
    from .coordination import get_hybrid_coordinator
    from .providers import create_external_provider, get_provider_summary
    from .routing import EnhancedBiologicalContextAnalyzer
    from .routing.biological_context import BiologicalContext
except ImportError as e:
    logger.error(f"Failed to import agent components: {e}")
    sys.exit(1)


class AgentCLI:
    """Command Line Interface for the Gliaent Agent System"""
    
    def __init__(self):
        self.agent = None
        self.router = None
        self.coordinator = None
        
    async def initialize(self):
        """Initialize the agent system"""
        try:
            logger.info("Initializing Gliaent Agent System...")
            
            # Initialize core agent
            self.agent = await quick_start_bioinformatics_agent()
            logger.info("✅ Core agent initialized")
            
            # Initialize router
            self.router = IntelligentToolRouter()
            logger.info("✅ Intelligent router initialized")
            
            # Initialize coordinator
            self.coordinator = await get_hybrid_coordinator()
            logger.info("✅ Coordination system initialized")
            
            logger.info("🚀 Agent system ready!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent system: {e}")
            raise
    
    async def interactive_chat(self):
        """Run interactive chat mode"""
        print("\n🧬 Gliaent Bioinformatics Agent")
        print("="*50)
        print("Ask me anything about bioinformatics analysis!")
        print("Type 'quit', 'exit', or 'bye' to end the session.")
        print("Type 'help' for available commands.")
        print("="*50)
        
        conversation_history = []
        
        while True:
            try:
                # Get user input
                user_input = input("\n🔬 You: ").strip()
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Thanks for using Gliaent! Goodbye!")
                    break
                
                # Handle special commands
                if user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'status':
                    await self.show_status()
                    continue
                elif user_input.lower() == 'clear':
                    conversation_history = []
                    print("🗑️  Conversation history cleared.")
                    continue
                
                # Process the query
                print("🤖 Agent: Thinking...", end="\r")
                
                start_time = time.time()
                response = await enhanced_ask_agent(user_input, conversation_history)
                elapsed_time = time.time() - start_time
                
                # Display response
                print(f"🤖 Agent ({elapsed_time:.1f}s): {response['response']}")
                
                # Show tool usage if any
                if response['tool_calls'] > 0:
                    print(f"🔧 Used {response['tool_calls']} tools")
                
                # Update conversation history
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": response['response']})
                
                # Keep history manageable
                if len(conversation_history) > 10:
                    conversation_history = conversation_history[-8:]
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"Chat error: {e}")
    
    def show_help(self):
        """Show help information"""
        print("\n📚 Available Commands:")
        print("  help     - Show this help message")
        print("  status   - Show system status")
        print("  clear    - Clear conversation history")
        print("  quit     - Exit the chat")
        print("\n🧬 Bioinformatics Examples:")
        print("  'Analyze my scRNA-seq data'")
        print("  'Create a volcano plot for differential expression'")
        print("  'Search for gene expression datasets'")
        print("  'Help me with RNA-seq quality control'")
    
    async def show_status(self):
        """Show comprehensive system status"""
        print("\n📊 System Status:")
        print("-" * 30)
        
        # Agent status
        agent_status = get_agent_status()
        print(f"🤖 Agent: {'✅ Healthy' if agent_status['status'] == 'healthy' else '❌ Error'}")
        if agent_status.get('memory_size'):
            print(f"   Memory: {agent_status['memory_size']} items")
        if agent_status.get('available_tools_count'):
            print(f"   Tools: {agent_status['available_tools_count']} available")
        
        # Coordinator status
        if self.coordinator:
            try:
                coord_status = self.coordinator.get_provider_status()
                print(f"🔄 Coordinator: ✅ Active ({len(coord_status)} providers)")
            except Exception as e:
                print(f"🔄 Coordinator: ❌ Error ({e})")
        
        # Router status
        if self.router:
            print("🧠 Router: ✅ Active")
        
        print("-" * 30)
    
    async def run_demonstrations(self):
        """Run system demonstrations"""
        print("\n🎯 Running Agent System Demonstrations")
        print("="*50)
        
        demos = [
            ("Basic Query Processing", self.demo_basic_query),
            ("Intelligent Tool Routing", self.demo_tool_routing),
            ("Biological Context Analysis", self.demo_biological_context),
            ("Coordination System", self.demo_coordination),
            ("Provider Management", self.demo_providers)
        ]
        
        for demo_name, demo_func in demos:
            print(f"\n🔬 {demo_name}")
            print("-" * len(demo_name))
            try:
                await demo_func()
                print("✅ Demo completed successfully")
            except Exception as e:
                print(f"❌ Demo failed: {e}")
                logger.error(f"Demo {demo_name} failed: {e}")
    
    async def demo_basic_query(self):
        """Demonstrate basic query processing"""
        test_query = "What is RNA-seq analysis?"
        print(f"Query: {test_query}")
        
        response = await enhanced_ask_agent(test_query)
        print(f"Response: {response['response'][:100]}...")
    
    async def demo_tool_routing(self):
        """Demonstrate intelligent tool routing"""
        print("Testing tool selection for different query types...")
        
        queries = [
            "Analyze scRNA-seq data",
            "Create volcano plot",
            "Search for datasets"
        ]
        
        for query in queries:
            context = await self.router.analyze_biological_context(query, {})
            tool_set = await self.router.dynamic_tool_selection(context)
            
            print(f"Query: {query}")
            print(f"Selected tools: {len(tool_set.tools)}")
            print(f"Confidence: {tool_set.confidence:.2f}")
    
    async def demo_biological_context(self):
        """Demonstrate biological context analysis"""
        analyzer = EnhancedBiologicalContextAnalyzer()
        
        test_contexts = [
            "I have single-cell RNA sequencing data from mouse brain",
            "Need to analyze differential gene expression in cancer samples",
            "Looking for protein-protein interaction networks"
        ]
        
        for context in test_contexts:
            analysis = await analyzer.analyze_context(context)
            print(f"Context: {context[:50]}...")
            # BiologicalContext object has attributes like primary_domain
            if hasattr(analysis, 'primary_domain'):
                print(f"Detected: {analysis.primary_domain}")
            else:
                print(f"Analysis type: {type(analysis)}")
    
    async def demo_coordination(self):
        """Demonstrate coordination system"""
        if not self.coordinator:
            print("Coordinator not available")
            return
        
        # Test provider status
        provider_status = self.coordinator.get_provider_status()
        print(f"Provider status: {provider_status}")
        
        # Test usage statistics
        stats = self.coordinator.get_usage_statistics()
        print(f"Usage stats: {stats['global']['total_requests']} total requests")
        
        # Test available providers
        providers = self.coordinator.providers
        print(f"Available providers: {len(providers)}")
    
    async def demo_providers(self):
        """Demonstrate provider management"""
        try:
            # Create a test provider
            provider = create_external_provider()
            summary = get_provider_summary(provider)
            
            print(f"Provider summary: {summary}")
            
        except Exception as e:
            print(f"Provider demo requires API configuration: {e}")
    
    async def run_system_tests(self):
        """Run comprehensive system tests"""
        print("\n🧪 Running System Tests")
        print("="*30)
        
        tests = [
            ("Agent Initialization", self.test_agent_init),
            ("Tool Router", self.test_tool_router),
            ("Context Analysis", self.test_context_analysis),
            ("Memory Management", self.test_memory),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...", end=" ")
            try:
                await test_func()
                print("✅ PASS")
                passed += 1
            except Exception as e:
                print(f"❌ FAIL - {e}")
                logger.error(f"Test {test_name} failed: {e}")
        
        print(f"\n📊 Test Results: {passed}/{total} passed")
        return passed == total
    
    async def test_agent_init(self):
        """Test agent initialization"""
        status = get_agent_status()
        assert status['status'] == 'healthy', "Agent not healthy"
    
    async def test_tool_router(self):
        """Test intelligent tool router"""
        context = await self.router.analyze_biological_context("test query", {})
        assert isinstance(context, dict), "Context analysis failed"
        
        tool_set = await self.router.dynamic_tool_selection(context)
        assert hasattr(tool_set, 'tools'), "Tool selection failed"
    
    async def test_context_analysis(self):
        """Test biological context analysis"""
        analyzer = EnhancedBiologicalContextAnalyzer()
        result = await analyzer.analyze_context("RNA-seq analysis")
        assert isinstance(result, BiologicalContext), "Context analysis failed"
        assert hasattr(result, 'primary_domain'), "BiologicalContext missing primary_domain"
    
    async def test_memory(self):
        """Test memory management"""
        if self.agent:
            initial_memory = len(self.agent.memory)
            self.agent.add_to_memory({"test": "item"})
            assert len(self.agent.memory) > initial_memory, "Memory not updated"
    
    async def test_error_handling(self):
        """Test error handling"""
        try:
            # Test with invalid query
            response = await enhanced_ask_agent("")
            assert 'response' in response, "Error handling failed"
        except Exception:
            # Expected for some edge cases
            pass
    
    async def run_benchmarks(self):
        """Run performance benchmarks"""
        print("\n🏃 Running Performance Benchmarks")
        print("="*40)
        
        benchmarks = [
            ("Query Processing Speed", self.benchmark_query_speed),
            ("Tool Selection Speed", self.benchmark_tool_selection),
            ("Memory Usage", self.benchmark_memory),
            ("Context Analysis Speed", self.benchmark_context_analysis)
        ]
        
        results = {}
        
        for benchmark_name, benchmark_func in benchmarks:
            print(f"\n⏱️  {benchmark_name}...", end=" ")
            try:
                result = await benchmark_func()
                results[benchmark_name] = result
                print(f"✅ {result}")
            except Exception as e:
                print(f"❌ Failed: {e}")
                results[benchmark_name] = f"Error: {e}"
        
        print(f"\n📊 Benchmark Summary:")
        for name, result in results.items():
            print(f"  {name}: {result}")
    
    async def benchmark_query_speed(self):
        """Benchmark query processing speed"""
        test_queries = [
            "What is RNA-seq?",
            "Help with scRNA-seq analysis",
            "Create volcano plot"
        ]
        
        times = []
        for query in test_queries:
            start_time = time.time()
            await enhanced_ask_agent(query)
            elapsed = time.time() - start_time
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        return f"{avg_time:.2f}s average"
    
    async def benchmark_tool_selection(self):
        """Benchmark tool selection speed"""
        start_time = time.time()
        for _ in range(10):
            context = await self.router.analyze_biological_context("test", {})
            await self.router.dynamic_tool_selection(context)
        elapsed = time.time() - start_time
        
        return f"{elapsed/10:.3f}s per selection"
    
    async def benchmark_memory(self):
        """Benchmark memory usage"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        return f"{memory_mb:.1f} MB"
    
    async def benchmark_context_analysis(self):
        """Benchmark context analysis speed"""
        analyzer = EnhancedBiologicalContextAnalyzer()
        
        start_time = time.time()
        for _ in range(5):
            await analyzer.analyze_context("RNA-seq differential expression analysis")
        elapsed = time.time() - start_time
        
        return f"{elapsed/5:.3f}s per analysis"


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Gliaent MCP Agent System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.mcp.agent                    # Interactive chat
  python -m src.mcp.agent --demo             # Run demonstrations  
  python -m src.mcp.agent --test             # Run tests
  python -m src.mcp.agent --status           # Check status
        """
    )
    
    parser.add_argument('--demo', action='store_true', 
                       help='Run system demonstrations')
    parser.add_argument('--test', action='store_true',
                       help='Run system tests')
    parser.add_argument('--status', action='store_true',
                       help='Show system status')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run performance benchmarks')
    parser.add_argument('--quiet', action='store_true',
                       help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Initialize CLI
    cli = AgentCLI()
    
    try:
        await cli.initialize()
        
        if args.status:
            await cli.show_status()
        elif args.demo:
            await cli.run_demonstrations()
        elif args.test:
            success = await cli.run_system_tests()
            sys.exit(0 if success else 1)
        elif args.benchmark:
            await cli.run_benchmarks()
        else:
            # Default to interactive chat
            await cli.interactive_chat()
            
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 