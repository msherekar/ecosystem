"""
Demo Core Infrastructure for Domain Prompts System

Provides core demo infrastructure with Electron integration, security validation,
and scalable demo execution framework.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from .security import SecurityValidator, SecurityLevel
from .events import get_event_emitter, emit_system_event, emit_ui_update, emit_error
from .performance import get_performance_monitor, time_it

logger = logging.getLogger(__name__)


@dataclass
class DemoResult:
    """Structured demo execution result"""
    demo_name: str
    success: bool
    duration: float
    data: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Electron IPC"""
        return {
            "demo_name": self.demo_name,
            "success": self.success,
            "duration": self.duration,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "format_version": "2.0"
        }


@dataclass
class DemoConfig:
    """Demo execution configuration"""
    enable_events: bool = True
    enable_security: bool = True
    output_format: str = "electron"  # text, json, electron
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    emit_progress: bool = True
    validate_inputs: bool = True
    max_execution_time: float = 60.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "enable_events": self.enable_events,
            "enable_security": self.enable_security,
            "output_format": self.output_format,
            "security_level": self.security_level.value,
            "emit_progress": self.emit_progress,
            "validate_inputs": self.validate_inputs,
            "max_execution_time": self.max_execution_time
        }


class DemoProgressReporter:
    """Progress reporting for demo execution with Electron integration"""
    
    def __init__(self, demo_name: str, total_steps: int, config: DemoConfig):
        self.demo_name = demo_name
        self.total_steps = total_steps
        self.current_step = 0
        self.config = config
        self.start_time = time.time()
        self._events = get_event_emitter() if config.enable_events else None
    
    def update(self, step_name: str = "", increment: int = 1, data: Any = None):
        """Update progress with Electron event emission"""
        self.current_step += increment
        progress_pct = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time
        
        progress_data = {
            "demo_name": self.demo_name,
            "step_name": step_name,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percent": progress_pct,
            "elapsed_seconds": elapsed,
            "data": data
        }
        
        if self.config.emit_progress and self._events:
            emit_ui_update("demo_progress", "update", progress_data)
        
        # Console output for non-Electron mode
        if self.config.output_format == "text":
            print(f"[{self.current_step}/{self.total_steps}] {step_name} ({progress_pct:.1f}%)")
    
    def complete(self, success: bool = True, message: str = ""):
        """Mark demo as complete"""
        duration = time.time() - self.start_time
        
        completion_data = {
            "demo_name": self.demo_name,
            "success": success,
            "message": message,
            "total_duration": duration
        }
        
        if self._events:
            emit_ui_update("demo_progress", "complete", completion_data)
        
        if self.config.output_format == "text":
            status = "✓" if success else "✗"
            print(f"{status} {self.demo_name} completed in {duration:.2f}s - {message}")


class BaseDemoScenario(ABC):
    """Base class for demo scenarios with enhanced security and monitoring"""
    
    def __init__(self, name: str, description: str):
        self.name = SecurityValidator.validate_string(name, 100, "demo_name")
        self.description = SecurityValidator.validate_string(description, 500, "demo_description")
        self._perf = get_performance_monitor()
        self._events = get_event_emitter()
    
    @abstractmethod
    async def execute_async(self, config: DemoConfig) -> DemoResult:
        """Execute the demo scenario asynchronously"""
        pass
    
    @abstractmethod
    def get_estimated_steps(self) -> int:
        """Get estimated number of steps for progress reporting"""
        pass
    
    def validate_prerequisites(self, config: DemoConfig) -> List[str]:
        """Validate demo prerequisites - override in subclasses"""
        return []
    
    async def safe_execute(self, config: DemoConfig) -> DemoResult:
        """Execute demo with comprehensive error handling and monitoring"""
        start_time = time.time()
        
        # Emit start event
        if config.enable_events:
            emit_system_event("demo_started", {
                "demo_name": self.name,
                "description": self.description,
                "config": config.to_dict()
            })
        
        try:
            # Validate prerequisites
            if config.validate_inputs:
                prerequisite_errors = self.validate_prerequisites(config)
                if prerequisite_errors:
                    return DemoResult(
                        demo_name=self.name,
                        success=False,
                        duration=time.time() - start_time,
                        errors=prerequisite_errors
                    )
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self.execute_async(config), 
                    timeout=config.max_execution_time
                )
                result.duration = time.time() - start_time
                
                # Emit success event
                if config.enable_events:
                    emit_system_event("demo_completed", {
                        "demo_name": self.name,
                        "success": result.success,
                        "duration": result.duration
                    })
                
                return result
                
            except asyncio.TimeoutError:
                return DemoResult(
                    demo_name=self.name,
                    success=False,
                    duration=time.time() - start_time,
                    errors=[f"Demo timed out after {config.max_execution_time}s"]
                )
            
        except Exception as e:
            error_msg = f"Demo execution failed: {e}"
            logger.error(error_msg)
            
            if config.enable_events:
                emit_error("demo_execution_error", error_msg, {
                    "demo_name": self.name
                })
            
            return DemoResult(
                demo_name=self.name,
                success=False,
                duration=time.time() - start_time,
                errors=[error_msg]
            )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get demo metadata for UI display"""
        return {
            "name": self.name,
            "description": self.description,
            "estimated_steps": self.get_estimated_steps(),
            "category": getattr(self, "category", "general"),
            "difficulty": getattr(self, "difficulty", "intermediate"),
            "duration_estimate": getattr(self, "duration_estimate", "< 1 minute")
        }


class DemoRunner:
    """Enhanced demo runner with Electron integration and security"""
    
    def __init__(self, config: Optional[DemoConfig] = None):
        self.config = config or DemoConfig()
        self._scenarios: Dict[str, BaseDemoScenario] = {}
        self._execution_history: List[DemoResult] = []
        self._perf = get_performance_monitor()
        self._events = get_event_emitter()
    
    def register_scenario(self, scenario: BaseDemoScenario):
        """Register a demo scenario with validation"""
        validated_name = SecurityValidator.validate_identifier(scenario.name, "scenario_name")
        self._scenarios[validated_name] = scenario
        
        logger.info(f"Registered demo scenario: {validated_name}")
        
        if self.config.enable_events:
            emit_system_event("demo_scenario_registered", {
                "scenario_name": validated_name,
                "description": scenario.description,
                "total_scenarios": len(self._scenarios)
            })
    
    async def run_scenario_async(self, scenario_name: str) -> DemoResult:
        """Run a specific demo scenario"""
        validated_name = SecurityValidator.validate_identifier(scenario_name, "scenario_name")
        
        if validated_name not in self._scenarios:
            return DemoResult(
                demo_name=validated_name,
                success=False,
                duration=0.0,
                errors=[f"Scenario '{validated_name}' not found"]
            )
        
        scenario = self._scenarios[validated_name]
        result = await scenario.safe_execute(self.config)
        
        # Store in history
        self._execution_history.append(result)
        
        # Limit history size
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]
        
        return result
    
    async def run_all_scenarios_async(self) -> List[DemoResult]:
        """Run all registered scenarios"""
        results = []
        
        for scenario_name in self._scenarios:
            result = await self.run_scenario_async(scenario_name)
            results.append(result)
        
        return results
    
    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """Get list of available scenarios for UI"""
        return [scenario.get_metadata() for scenario in self._scenarios.values()]
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history for UI"""
        recent_history = self._execution_history[-limit:]
        return [result.to_dict() for result in recent_history]


if __name__ == "__main__":
    # Test demo core infrastructure
    async def test_demo_core():
        print("Testing Demo Core Infrastructure")
        
        # Test demo config
        config = DemoConfig(
            enable_events=True,
            output_format="electron",
            security_level=SecurityLevel.PUBLIC
        )
        print(f"✓ Demo config: {config.output_format} format")
        
        # Test progress reporter
        progress = DemoProgressReporter("test_demo", 3, config)
        progress.update("Step 1")
        progress.update("Step 2")
        progress.complete(True, "Test completed")
        print("✓ Progress reporter tested")
        
        # Test demo runner
        runner = DemoRunner(config)
        scenarios = runner.get_available_scenarios()
        print(f"✓ Demo runner: {len(scenarios)} scenarios available")
        
        print("\n✅ Demo core infrastructure test completed!")
    
    # Run test
    try:
        asyncio.run(test_demo_core())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 