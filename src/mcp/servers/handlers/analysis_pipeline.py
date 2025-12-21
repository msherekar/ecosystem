"""
Pipeline Management Mixin

Handles pipeline execution and orchestration for different analysis techniques.
Separated for better modularity and maintainability.
"""

import asyncio
from typing import Any, Dict, List
from datetime import datetime
from ...core.registry.tool_registry import mcp_tool


class PipelineMixin:
    """Mixin providing pipeline management functionality"""
    
    @mcp_tool(
        description="Execute the complete analysis pipeline including QC, normalization, clustering, and visualization",
        category="analysis"
    )
    async def run_pipeline(self, force_rerun: bool = False, 
                          custom_steps: List[str] = None,
                          save_intermediate: bool = True):
        """Execute the complete analysis pipeline"""
        try:
            # Get technique-specific pipeline configuration
            pipeline_config = self._get_pipeline_configuration()
            
            # Override with custom steps if provided
            if custom_steps:
                pipeline_config["steps"] = custom_steps
            
            # Validate pipeline configuration
            validation = self._validate_pipeline_configuration(pipeline_config)
            if not validation["valid"]:
                return self._create_error_response(
                    f"Invalid pipeline configuration: {', '.join(validation['errors'])}",
                    error_type="configuration_error"
                )
            
            # Check if pipeline can run
            prereq_check = self._check_pipeline_prerequisites(force_rerun)
            if not prereq_check["can_run"]:
                return self._create_error_response(
                    prereq_check["message"],
                    error_type="prerequisites_not_met",
                    suggestion=prereq_check.get("suggestion")
                )
            
            # Execute pipeline
            start_time = datetime.now()
            pipeline_result = await self._execute_pipeline(
                pipeline_config, 
                force_rerun, 
                save_intermediate
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return self._create_success_response(
                "Pipeline completed successfully",
                result=pipeline_result,
                execution_time=execution_time,
                steps_completed=pipeline_result.get("steps_completed", []),
                intermediate_saved=save_intermediate
            )
        except Exception as e:
            return self._create_error_response(f"Pipeline failed: {str(e)}")
    
    @mcp_tool(
        description="Get pipeline status and progress",
        category="analysis"
    )
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        try:
            status = await self._get_pipeline_status()
            
            return self._create_success_response(
                "Pipeline status retrieved",
                **status
            )
        except Exception as e:
            return self._create_error_response(f"Failed to get pipeline status: {str(e)}")
    
    @mcp_tool(
        description="Reset pipeline progress and clear intermediate results",
        category="analysis"
    )
    async def reset_pipeline(self, confirm: bool = False) -> Dict[str, Any]:
        """Reset pipeline progress"""
        if not confirm:
            return self._create_error_response(
                "Pipeline reset requires confirmation",
                error_type="confirmation_required",
                suggestion="Set confirm=True to reset pipeline"
            )
        
        try:
            await self._reset_pipeline_state()
            
            return self._create_success_response(
                "Pipeline reset successfully",
                reset_timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return self._create_error_response(f"Pipeline reset failed: {str(e)}")
    
    @mcp_tool(
        description="Validate pipeline configuration and prerequisites",
        category="analysis"
    )
    async def validate_pipeline(self) -> Dict[str, Any]:
        """Validate pipeline can run"""
        try:
            # Get pipeline configuration
            config = self._get_pipeline_configuration()
            
            # Validate configuration
            config_validation = self._validate_pipeline_configuration(config)
            
            # Check prerequisites
            prereq_check = self._check_pipeline_prerequisites(force_rerun=False)
            
            # Check data availability
            data_check = self._check_data_availability()
            
            validation_result = {
                "configuration_valid": config_validation["valid"],
                "configuration_errors": config_validation.get("errors", []),
                "prerequisites_met": prereq_check["can_run"],
                "prerequisite_message": prereq_check.get("message", ""),
                "data_available": data_check.get("available", False),
                "data_message": data_check.get("message", ""),
                "overall_valid": (
                    config_validation["valid"] and 
                    prereq_check["can_run"] and 
                    data_check.get("available", False)
                )
            }
            
            return self._create_success_response(
                "Pipeline validation completed",
                validation=validation_result
            )
        except Exception as e:
            return self._create_error_response(f"Pipeline validation failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _get_pipeline_function(self):
        """Get the pipeline function for this technique"""
        raise NotImplementedError("Subclasses must implement _get_pipeline_function")
    
    def _get_pipeline_configuration(self):
        """Get pipeline configuration for this technique"""
        raise NotImplementedError("Subclasses must implement _get_pipeline_configuration")
    
    async def _execute_pipeline(self, config, force_rerun, save_intermediate):
        """Execute technique-specific pipeline"""
        raise NotImplementedError("Subclasses must implement _execute_pipeline")
    
    async def _get_pipeline_status(self):
        """Get technique-specific pipeline status"""
        raise NotImplementedError("Subclasses must implement _get_pipeline_status")
    
    async def _reset_pipeline_state(self):
        """Reset technique-specific pipeline state"""
        raise NotImplementedError("Subclasses must implement _reset_pipeline_state")
    
    def _check_pipeline_prerequisites(self, force_rerun):
        """Check pipeline prerequisites"""
        # Default implementation - subclasses can override
        return {"can_run": True, "message": "Prerequisites met"}
    
    def _validate_pipeline_configuration(self, config):
        """Validate pipeline configuration"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(config, dict):
            validation_result["valid"] = False
            validation_result["errors"].append("Configuration must be a dictionary")
            return validation_result
        
        if "steps" not in config:
            validation_result["valid"] = False
            validation_result["errors"].append("Configuration must include 'steps'")
        
        if not isinstance(config.get("steps", []), list):
            validation_result["valid"] = False
            validation_result["errors"].append("Steps must be a list")
        
        # Validate individual steps
        valid_steps = [
            "qc", "filtering", "normalization", "dimensionality_reduction", 
            "clustering", "marker_analysis", "visualization"
        ]
        
        for step in config.get("steps", []):
            if step not in valid_steps:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Invalid step: {step}")
        
        return validation_result


def main():
    """Test pipeline mixin functionality"""
    import logging
    
    class TestPipelineHandler(PipelineMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown", suggestion=None):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        def _check_data_availability(self):
            return {"available": True}
            
        def _get_pipeline_function(self):
            return lambda x: {"completed": True}
            
        def _get_pipeline_configuration(self):
            return {"steps": ["qc", "normalization", "clustering"]}
            
        async def _execute_pipeline(self, config, force_rerun, save_intermediate):
            return {"steps_completed": config["steps"]}
            
        async def _get_pipeline_status(self):
            return {"current_step": "qc", "progress": 0.3}
            
        async def _reset_pipeline_state(self):
            pass
    
    # Test configuration validation
    handler = TestPipelineHandler()
    
    # Test valid configuration
    config = {"steps": ["qc", "normalization", "clustering"]}
    validation = handler._validate_pipeline_configuration(config)
    assert validation["valid"] is True
    
    # Test invalid configuration
    invalid_config = {"steps": ["invalid_step"]}
    validation = handler._validate_pipeline_configuration(invalid_config)
    assert validation["valid"] is False
    
    print("✅ Pipeline mixin tests passed")


if __name__ == "__main__":
    main()