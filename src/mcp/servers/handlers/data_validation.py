"""
Data Validation Mixin

Handles data validation operations for different analysis techniques.
Separated for better modularity and maintainability.
"""

from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool


class DataValidationMixin:
    """Mixin providing data validation functionality"""
    
    @mcp_tool(
        description="Validate uploaded data",
        category="data"
    )
    async def validate_data(self) -> Dict[str, Any]:
        """Validate uploaded data"""
        validation_results = {
            "data_valid": False,
            "data_type": None,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            # Get technique-specific data validation
            data_check = self._check_data_availability()
            
            if data_check["available"]:
                validation_results["data_valid"] = True
                validation_results.update(data_check)
                
                # Perform additional validation
                additional_validation = self._perform_additional_validation()
                validation_results.update(additional_validation)
                
                # Check data quality
                quality_check = await self._check_data_quality()
                validation_results.update(quality_check)
                
                # Generate recommendations
                recommendations = self._generate_validation_recommendations(validation_results)
                validation_results["recommendations"] = recommendations
            else:
                validation_results["issues"].append(data_check["message"])
            
            return self._create_success_response(
                "Data validation completed",
                validation=validation_results
            )
        except Exception as e:
            return self._create_error_response(f"Data validation failed: {str(e)}")
    
    @mcp_tool(
        description="Check data integrity and consistency",
        category="data"
    )
    async def check_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity"""
        try:
            # Check data availability
            data_check = self._check_data_availability()
            if not data_check["available"]:
                return self._create_error_response(
                    data_check["message"],
                    error_type="no_data"
                )
            
            integrity_results = await self._perform_integrity_checks()
            
            return self._create_success_response(
                "Data integrity check completed",
                integrity=integrity_results
            )
        except Exception as e:
            return self._create_error_response(f"Data integrity check failed: {str(e)}")
    
    @mcp_tool(
        description="Detect and report data anomalies",
        category="data"
    )
    async def detect_anomalies(self, sensitivity: float = 0.95) -> Dict[str, Any]:
        """Detect data anomalies"""
        self._log_operation("Anomaly detection", sensitivity=sensitivity)
        
        # Validate sensitivity parameter
        if not isinstance(sensitivity, (int, float)) or not 0.5 <= sensitivity <= 1.0:
            return self._create_error_response(
                "Sensitivity must be between 0.5 and 1.0",
                error_type="parameter_validation"
            )
        
        try:
            anomalies = await self._detect_data_anomalies(sensitivity)
            
            return self._create_success_response(
                f"Anomaly detection completed, found {len(anomalies.get('anomalies', []))} anomalies",
                **anomalies
            )
        except Exception as e:
            return self._create_error_response(f"Anomaly detection failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _perform_additional_validation(self) -> Dict[str, Any]:
        """Perform technique-specific additional validation"""
        return {}  # Default implementation returns empty dict
    
    async def _check_data_quality(self) -> Dict[str, Any]:
        """Check technique-specific data quality"""
        return {}  # Default implementation returns empty dict
    
    async def _perform_integrity_checks(self) -> Dict[str, Any]:
        """Perform technique-specific integrity checks"""
        raise NotImplementedError("Subclasses must implement _perform_integrity_checks")
    
    async def _detect_data_anomalies(self, sensitivity: float) -> Dict[str, Any]:
        """Detect technique-specific data anomalies"""
        raise NotImplementedError("Subclasses must implement _detect_data_anomalies")
    
    def _generate_validation_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate validation recommendations based on results"""
        recommendations = []
        
        # Check for common issues and generate recommendations
        if validation_results.get("issues"):
            for issue in validation_results["issues"]:
                if "few cells" in issue.lower():
                    recommendations.append("Consider uploading a larger dataset with more cells")
                elif "few genes" in issue.lower():
                    recommendations.append("Check data preprocessing - very few genes detected")
        
        if validation_results.get("warnings"):
            for warning in validation_results["warnings"]:
                if "quality" in warning.lower():
                    recommendations.append("Review data quality metrics before proceeding")
                elif "missing" in warning.lower():
                    recommendations.append("Check for missing values and handle appropriately")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("Data validation passed - you can proceed with analysis")
        
        return recommendations


def main():
    """Test data validation mixin functionality"""
    import logging
    
    class TestDataValidationHandler(DataValidationMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown"):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        def _check_data_availability(self):
            return {"available": True, "data_type": "test"}
            
        async def _perform_integrity_checks(self):
            return {"checks_passed": 5, "checks_failed": 0}
            
        async def _detect_data_anomalies(self, sensitivity):
            return {"anomalies": [], "total_checked": 1000}
    
    # Test functionality
    handler = TestDataValidationHandler()
    
    # Test recommendation generation
    validation_results = {
        "issues": ["Very few cells (50), consider uploading more data"],
        "warnings": ["Data quality metrics below threshold"]
    }
    recommendations = handler._generate_validation_recommendations(validation_results)
    assert len(recommendations) >= 2
    
    print("✅ Data validation mixin tests passed")


if __name__ == "__main__":
    main()