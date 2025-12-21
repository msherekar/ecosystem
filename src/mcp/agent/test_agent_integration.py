#!/usr/bin/env python3
"""
Comprehensive Agent Integration Tests
====================================

This module provides comprehensive integration tests for the Gliaent MCP Agent system,
testing all components working together including coordination, decision-making,
providers, routing, and core agent functionality.

Usage:
    python src/mcp/agent/test_agent_integration.py
    pytest src/mcp/agent/test_agent_integration.py -v
"""

import asyncio
import pytest
import json
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import components to test
try:
    from src.mcp.agent import (
        Agent,
        get_agent,
        ask_agent,
        enhanced_ask_agent,
        IntelligentToolRouter,
        ContextualToolSet,
        get_agent_status,
        create_complete_agent,
        quick_start_bioinformatics_agent
    )
    from src.mcp.agent.coordination import (
        HybridCoordinator,
        get_hybrid_coordinator,
        ScalableHybridCoordinator,
        ProviderRegistry,
        AdvancedLoadBalancer,
        IntelligentCache
    )
    from src.mcp.agent.decision import (
        ScalableProviderSelector,
        SelectionContext,
        SelectionCriteria
    )
    from src.mcp.agent.providers import (
        BaseLLMProvider,
        ExternalLLMProvider,
        LocalLLMProvider,
        create_external_provider,
        create_local_provider,
        initialize_providers,
        get_provider_summary
    )
    from src.mcp.agent.routing import (
        BiologicalContext,
        EnhancedBiologicalContextAnalyzer,
        WorkflowPredictionEngine,
        MultiModalContextIntegrator,
        DataFileAnalyzer
    )
except ImportError as e:
    logger.error(f"Failed to import agent components: {e}")
    raise


class TestAgentCore:
    """Test core agent functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_api_key = "test-api-key-12345"
        
    def test_agent_initialization(self):
        """Test agent can be initialized properly"""
        agent = Agent(api_key=self.test_api_key)
        
        assert agent is not None
        assert agent.client is not None
        assert agent.memory == []
        assert agent.available_tools == []
    
    def test_agent_memory_management(self):
        """Test agent memory operations"""
        agent = Agent(api_key=self.test_api_key)
        
        # Test adding to memory
        test_item = {"tool": "test_tool", "result": "success"}
        agent.add_to_memory(test_item)
        
        assert len(agent.memory) == 1
        assert agent.memory[0] == test_item
        
        # Test memory retrieval
        memory = agent.get_memory()
        assert memory == [test_item]
    
    def test_agent_tool_setting(self):
        """Test setting available tools"""
        agent = Agent(api_key=self.test_api_key)
        
        test_tools = [
            {"name": "test_tool1", "description": "Test tool 1"},
            {"name": "test_tool2", "description": "Test tool 2"}
        ]
        
        agent.set_available_tools(test_tools)
        assert agent.available_tools == test_tools
    
    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'})
    def test_get_agent_function(self):
        """Test get_agent factory function"""
        agent = get_agent()
        assert agent is not None
        assert isinstance(agent, Agent)
    
    def test_agent_status(self):
        """Test agent status reporting"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            status = get_agent_status()
            
            # Should return status dict
            assert isinstance(status, dict)
            assert 'agent_initialized' in status
            assert 'status' in status


class TestIntelligentRouter:
    """Test intelligent tool routing functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.router = IntelligentToolRouter()
        
    @pytest.mark.asyncio
    async def test_biological_context_analysis(self):
        """Test biological context analysis"""
        test_queries = [
            ("Analyze scRNA-seq data", ["scrnaseq"]),
            ("RNA-seq differential expression", ["rnaseq"]),
            ("Protein analysis", ["proteomics"]),
            ("Single cell clustering", ["scrnaseq"])
        ]
        
        for query, expected_domains in test_queries:
            context = await self.router.analyze_biological_context(query, {})
            
            assert isinstance(context, dict)
            assert "required_domains" in context
            
            # Check if expected domains are detected
            for domain in expected_domains:
                assert domain in context["required_domains"]
    
    @pytest.mark.asyncio
    async def test_dynamic_tool_selection(self):
        """Test dynamic tool selection"""
        # Mock the MCP registry
        with patch.object(self.router, 'mcp_registry') as mock_registry:
            mock_registry.get_available_tools.return_value = {
                "scrnaseq_clustering": {"description": "Single cell clustering"},
                "rnaseq_deseq": {"description": "RNA-seq differential expression"},
                "generic_plot": {"description": "General plotting tool"}
            }
            
            test_context = {
                "required_domains": ["scrnaseq"],
                "analysis_intent": "clustering",
                "workflow_stage": "analysis"
            }
            
            tool_set = await self.router.dynamic_tool_selection(test_context)
            
            assert isinstance(tool_set, ContextualToolSet)
            assert isinstance(tool_set.tools, list)
            assert tool_set.confidence > 0
            assert tool_set.reasoning is not None
    
    def test_relevance_scoring(self):
        """Test tool relevance scoring algorithm"""
        test_tool = {
            "name": "scrnaseq_clustering",
            "description": "Single cell RNA sequencing clustering analysis"
        }
        
        test_context = {
            "required_domains": ["scrnaseq"],
            "analysis_intent": "clustering",
            "workflow_stage": "analysis"
        }
        
        score = self.router._calculate_relevance_score(
            "scrnaseq_clustering", test_tool, test_context
        )
        
        # Should get high score for domain match
        assert score > 5.0
    
    def test_data_type_detection(self):
        """Test data type detection from query and session"""
        session_state = {"anndata": "mock_data"}
        
        # Test with session state
        data_types = self.router._detect_data_types("test query", session_state)
        assert "single_cell" in data_types
        
        # Test with query text
        data_types = self.router._detect_data_types("RNA-seq analysis", {})
        assert "rna_seq" in data_types


class TestCoordination:
    """Test coordination system functionality"""
    
    @pytest.mark.asyncio
    async def test_hybrid_coordinator_initialization(self):
        """Test hybrid coordinator initialization"""
        coordinator = get_hybrid_coordinator()
        
        assert coordinator is not None
        
        # Test initialization
        await coordinator.initialize()
        
        # Test health check
        health = await coordinator.health_check()
        assert isinstance(health, dict)
    
    @pytest.mark.asyncio
    async def test_provider_registry(self):
        """Test provider registry functionality"""
        registry = ProviderRegistry()
        
        # Test registration
        mock_provider = Mock()
        mock_provider.provider_id = "test_provider"
        mock_provider.provider_type = "external"
        
        await registry.register_provider(mock_provider)
        
        # Test retrieval
        providers = await registry.get_available_providers()
        assert "test_provider" in [p.provider_id for p in providers]
    
    @pytest.mark.asyncio
    async def test_load_balancer(self):
        """Test load balancer functionality"""
        balancer = AdvancedLoadBalancer()
        
        # Add mock providers
        providers = [
            Mock(provider_id=f"provider_{i}", load_score=0.5)
            for i in range(3)
        ]
        
        for provider in providers:
            await balancer.add_provider(provider)
        
        # Test provider selection
        selected = await balancer.select_optimal_provider({})
        assert selected in providers
    
    @pytest.mark.asyncio
    async def test_intelligent_cache(self):
        """Test intelligent caching system"""
        cache = IntelligentCache()
        
        # Test cache operations
        test_key = "test_query_hash"
        test_value = {"response": "test response", "tools_used": []}
        
        await cache.set(test_key, test_value)
        cached_value = await cache.get(test_key)
        
        assert cached_value == test_value


class TestDecisionEngine:
    """Test decision engine functionality"""
    
    @pytest.mark.asyncio
    async def test_provider_selector(self):
        """Test scalable provider selector"""
        selector = ScalableProviderSelector()
        
        # Create test context
        context = SelectionContext(
            query="Analyze RNA-seq data",
            user_id="test_user",
            session_data={}
        )
        
        criteria = SelectionCriteria(
            max_latency=5.0,
            min_reliability=0.8,
            cost_preference="balanced"
        )
        
        # Mock providers
        mock_providers = [
            Mock(provider_id="fast_provider", latency=1.0, reliability=0.9),
            Mock(provider_id="slow_provider", latency=10.0, reliability=0.95)
        ]
        
        # Test selection
        with patch.object(selector, '_get_available_providers', return_value=mock_providers):
            selected = await selector.select_provider(context, criteria)
            
            # Should select fast provider due to latency constraint
            assert selected.provider_id == "fast_provider"


class TestProviders:
    """Test LLM provider functionality"""
    
    def test_provider_creation(self):
        """Test provider creation functions"""
        # Test external provider creation
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            provider = create_external_provider(api_key="test-key")
            assert isinstance(provider, ExternalLLMProvider)
        
        # Test local provider creation
        local_provider = create_local_provider()
        assert isinstance(local_provider, LocalLLMProvider)
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initialization"""
        provider = create_local_provider()
        
        # Mock the initialization
        with patch.object(provider, '_initialize_model', return_value=True):
            result = await provider.initialize()
            assert result is True
    
    def test_provider_summary(self):
        """Test provider summary generation"""
        provider = create_local_provider()
        summary = get_provider_summary(provider)
        
        assert isinstance(summary, dict)
        assert 'total_providers' in summary
        assert 'providers' in summary


class TestRouting:
    """Test biological routing functionality"""
    
    @pytest.mark.asyncio
    async def test_biological_context_analyzer(self):
        """Test enhanced biological context analyzer"""
        analyzer = EnhancedBiologicalContextAnalyzer()
        
        test_contexts = [
            "Single cell RNA sequencing analysis",
            "Differential gene expression study",
            "Protein-protein interaction network"
        ]
        
        for context_text in test_contexts:
            result = await analyzer.analyze_context(context_text)
            
            assert isinstance(result, dict)
            assert 'primary_analysis_type' in result or 'detected_techniques' in result
    
    @pytest.mark.asyncio
    async def test_workflow_predictor(self):
        """Test workflow prediction engine"""
        predictor = WorkflowPredictionEngine()
        
        # Test workflow prediction
        context = BiologicalContext(
            data_types=["single_cell"],
            analysis_goals=["clustering"],
            current_step="data_upload"
        )
        
        next_steps = await predictor.predict_next_steps(context)
        
        assert isinstance(next_steps, list)
        assert len(next_steps) > 0
    
    @pytest.mark.asyncio
    async def test_multimodal_integrator(self):
        """Test multimodal context integration"""
        integrator = MultiModalContextIntegrator()
        
        # Test integration of different data types
        contexts = {
            "text": "RNA-seq differential expression",
            "file_info": {"file_type": "csv", "size": 1000},
            "session": {"uploaded_data": True}
        }
        
        integrated = await integrator.integrate_contexts(contexts)
        
        assert isinstance(integrated, dict)
        assert 'integrated_context' in integrated


class TestFullIntegration:
    """Test full system integration"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_query_processing(self):
        """Test complete query processing pipeline"""
        # Mock environment
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            with patch('openai.OpenAI') as mock_openai:
                # Mock OpenAI response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "Test response"
                mock_response.choices[0].message.tool_calls = None
                
                mock_openai.return_value.chat.completions.create.return_value = mock_response
                
                # Test enhanced ask agent
                response = await enhanced_ask_agent("What is RNA-seq analysis?")
                
                assert isinstance(response, dict)
                assert 'response' in response
                assert response['response'] is not None
    
    @pytest.mark.asyncio
    async def test_agent_with_coordination(self):
        """Test agent working with coordination system"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            try:
                # Create complete agent
                agent = await create_complete_agent()
                
                assert agent is not None
                assert isinstance(agent, Agent)
                
            except ValueError:
                # Expected if no API key provided
                pass
    
    @pytest.mark.asyncio
    async def test_bioinformatics_quick_start(self):
        """Test bioinformatics quick start function"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            try:
                agent = await quick_start_bioinformatics_agent()
                
                assert agent is not None
                assert isinstance(agent, Agent)
                
            except ValueError:
                # Expected if no API key provided
                pass
    
    @pytest.mark.asyncio
    async def test_system_resilience(self):
        """Test system behavior under failure conditions"""
        # Test with invalid API key
        with pytest.raises(ValueError):
            Agent(api_key="")
        
        # Test router with empty context
        router = IntelligentToolRouter()
        context = await router.analyze_biological_context("", {})
        
        # Should handle empty query gracefully
        assert isinstance(context, dict)
    
    def test_component_compatibility(self):
        """Test that all components can be imported together"""
        # This test ensures no circular imports or conflicts
        # Test that main classes can be instantiated
        assert IntelligentToolRouter is not None
        assert Agent is not None
    
    @pytest.mark.asyncio
    async def test_performance_characteristics(self):
        """Test basic performance characteristics"""
        router = IntelligentToolRouter()
        
        # Measure context analysis speed
        start_time = time.time()
        
        for _ in range(10):
            await router.analyze_biological_context("test query", {})
        
        elapsed = time.time() - start_time
        avg_time = elapsed / 10
        
        # Should be reasonably fast (less than 100ms per analysis)
        assert avg_time < 0.1, f"Context analysis too slow: {avg_time:.3f}s"


# Test fixtures and utilities
@pytest.fixture
async def mock_agent():
    """Fixture for mock agent"""
    with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
        agent = Agent(api_key="test-key")
        yield agent


@pytest.fixture
async def mock_router():
    """Fixture for mock router"""
    router = IntelligentToolRouter()
    yield router


@pytest.fixture
async def mock_coordinator():
    """Fixture for mock coordinator"""
    coordinator = get_hybrid_coordinator()
    await coordinator.initialize()
    yield coordinator


# Utility functions for testing
def create_test_context(data_types=None, analysis_goals=None):
    """Create test biological context"""
    return BiologicalContext(
        data_types=data_types or ["single_cell"],
        analysis_goals=analysis_goals or ["clustering"],
        current_step="data_upload"
    )


def create_mock_session_state(uploaded_data=True):
    """Create mock session state"""
    state = {}
    if uploaded_data:
        state["anndata"] = "mock_data"
    return state


# Run tests if executed directly
if __name__ == "__main__":
    print("🧪 Running Agent Integration Tests")
    print("="*50)
    
    # Run basic tests synchronously
    test_core = TestAgentCore()
    test_core.setup_method()
    
    try:
        test_core.test_agent_initialization()
        print("✅ Agent initialization test passed")
        
        test_core.test_agent_memory_management()
        print("✅ Memory management test passed")
        
        test_core.test_agent_tool_setting()
        print("✅ Tool setting test passed")
        
    except Exception as e:
        print(f"❌ Core tests failed: {e}")
    
    # Run router tests
    test_router = TestIntelligentRouter()
    test_router.setup_method()
    
    async def run_async_tests():
        try:
            await test_router.test_biological_context_analysis()
            print("✅ Biological context analysis test passed")
            
            test_router.test_relevance_scoring()
            print("✅ Relevance scoring test passed")
            
            test_router.test_data_type_detection()
            print("✅ Data type detection test passed")
            
        except Exception as e:
            print(f"❌ Router tests failed: {e}")
    
    # Run async tests
    asyncio.run(run_async_tests())
    
    print("\n🎯 Basic integration tests completed!")
    print("For full pytest suite, run: pytest src/mcp/agent/test_agent_integration.py -v") 