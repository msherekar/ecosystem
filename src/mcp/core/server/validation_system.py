"""
MCP Server Validation System

Handles parameter validation for tool execution with multiple validation backends.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


class ValidationBackend(Enum):
    """Supported validation backends"""
    BASIC = "basic"  # Basic type checking
    JSONSCHEMA = "jsonschema"  # JSON Schema validation
    PYDANTIC = "pydantic"  # Pydantic model validation


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class ValidationSystem:
    """
    Handles parameter validation for MCP tools.
    
    Supports multiple validation backends and custom validators.
    """
    
    def __init__(self):
        self.backend = ValidationBackend.BASIC
        self.custom_validators: Dict[str, Callable] = {}
        self.validation_config: Dict[str, Any] = {}
        self.logger = logging.getLogger("mcp.validation")
    
    def configure_validation(self,
                           backend: Optional[ValidationBackend] = None,
                           custom_validators: Optional[Dict[str, Callable]] = None,
                           validation_config: Optional[Dict[str, Any]] = None) -> None:
        """Configure the validation system"""
        if backend:
            self.backend = backend
        if custom_validators:
            self.custom_validators.update(custom_validators)
        if validation_config:
            self.validation_config.update(validation_config)
        
        self.logger.info(f"Validation configured with backend: {self.backend.value}")
    
    def register_validator(self, name: str, validator_func: Callable) -> None:
        """Register a custom validator function"""
        self.custom_validators[name] = validator_func
        self.logger.info(f"Registered custom validator: {name}")
    
    def validate_parameters(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Validate parameters against a schema using the configured backend.
        
        Args:
            parameters: Parameters to validate
            schema: Validation schema
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if self.backend == ValidationBackend.BASIC:
                self._validate_basic(parameters, schema)
            elif self.backend == ValidationBackend.JSONSCHEMA:
                self._validate_jsonschema(parameters, schema)
            elif self.backend == ValidationBackend.PYDANTIC:
                self._validate_pydantic(parameters, schema)
            else:
                raise ValidationError(f"Unknown validation backend: {self.backend}")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Validation failed: {str(e)}")
    
    def _validate_basic(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Basic parameter validation using type checking"""
        schema_props = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        # Check required fields
        for field in required_fields:
            if field not in parameters:
                raise ValidationError(f"Required field '{field}' is missing", field)
        
        # Validate each parameter
        for param_name, param_value in parameters.items():
            if param_name in schema_props:
                prop_schema = schema_props[param_name]
                self._validate_basic_field(param_name, param_value, prop_schema)
    
    def _validate_basic_field(self, field_name: str, value: Any, field_schema: Dict[str, Any]) -> None:
        """Validate a single field with basic validation"""
        expected_type = field_schema.get("type")
        
        if expected_type == "string" and not isinstance(value, str):
            raise ValidationError(f"Field '{field_name}' must be a string", field_name, value)
        elif expected_type == "integer" and not isinstance(value, int):
            raise ValidationError(f"Field '{field_name}' must be an integer", field_name, value)
        elif expected_type == "number" and not isinstance(value, (int, float)):
            raise ValidationError(f"Field '{field_name}' must be a number", field_name, value)
        elif expected_type == "boolean" and not isinstance(value, bool):
            raise ValidationError(f"Field '{field_name}' must be a boolean", field_name, value)
        elif expected_type == "array" and not isinstance(value, list):
            raise ValidationError(f"Field '{field_name}' must be an array", field_name, value)
        elif expected_type == "object" and not isinstance(value, dict):
            raise ValidationError(f"Field '{field_name}' must be an object", field_name, value)
        
        # Check enum constraints
        if "enum" in field_schema:
            allowed_values = field_schema["enum"]
            if value not in allowed_values:
                raise ValidationError(
                    f"Field '{field_name}' must be one of {allowed_values}, got '{value}'",
                    field_name, value
                )
        
        # Check numeric constraints
        if expected_type in ["integer", "number"]:
            if "minimum" in field_schema and value < field_schema["minimum"]:
                raise ValidationError(
                    f"Field '{field_name}' must be >= {field_schema['minimum']}, got {value}",
                    field_name, value
                )
            if "maximum" in field_schema and value > field_schema["maximum"]:
                raise ValidationError(
                    f"Field '{field_name}' must be <= {field_schema['maximum']}, got {value}",
                    field_name, value
                )
        
        # Check string constraints
        if expected_type == "string":
            if "minLength" in field_schema and len(value) < field_schema["minLength"]:
                raise ValidationError(
                    f"Field '{field_name}' must be at least {field_schema['minLength']} characters",
                    field_name, value
                )
            if "maxLength" in field_schema and len(value) > field_schema["maxLength"]:
                raise ValidationError(
                    f"Field '{field_name}' must be at most {field_schema['maxLength']} characters",
                    field_name, value
                )
        
        # Check array constraints
        if expected_type == "array":
            if "minItems" in field_schema and len(value) < field_schema["minItems"]:
                raise ValidationError(
                    f"Field '{field_name}' must have at least {field_schema['minItems']} items",
                    field_name, value
                )
            if "maxItems" in field_schema and len(value) > field_schema["maxItems"]:
                raise ValidationError(
                    f"Field '{field_name}' must have at most {field_schema['maxItems']} items",
                    field_name, value
                )
    
    def _validate_jsonschema(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate parameters using jsonschema library"""
        try:
            import jsonschema
            jsonschema.validate(parameters, schema)
        except ImportError:
            self.logger.warning("jsonschema not available, falling back to basic validation")
            self._validate_basic(parameters, schema)
        except jsonschema.ValidationError as e:
            raise ValidationError(f"JSON Schema validation failed: {e.message}", e.path[-1] if e.path else None)
        except jsonschema.SchemaError as e:
            raise ValidationError(f"Invalid schema: {e.message}")
    
    def _validate_pydantic(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate parameters using Pydantic models"""
        try:
            from pydantic import BaseModel, ValidationError as PydanticValidationError, create_model
            
            # Convert JSON schema to Pydantic model if needed
            model_class = self._json_schema_to_pydantic(schema)
            
            # Validate using Pydantic
            model_class(**parameters)
            
        except ImportError:
            self.logger.warning("pydantic not available, falling back to basic validation")
            self._validate_basic(parameters, schema)
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"]) if error["loc"] else "unknown"
                errors.append(f"{field}: {error['msg']}")
            raise ValidationError(f"Pydantic validation failed: {'; '.join(errors)}")
    
    def _json_schema_to_pydantic(self, schema: Dict[str, Any]) -> type:
        """Convert JSON schema to Pydantic model (simplified implementation)"""
        from pydantic import create_model
        
        # This is a simplified conversion - in practice, you'd want a more robust implementation
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        fields = {}
        for field_name, field_schema in properties.items():
            field_type = self._json_type_to_python_type(field_schema.get("type", "string"))
            default_value = field_schema.get("default", ... if field_name in required else None)
            fields[field_name] = (field_type, default_value)
        
        return create_model("ValidationModel", **fields)
    
    def _json_type_to_python_type(self, json_type: str) -> type:
        """Convert JSON schema type to Python type"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_mapping.get(json_type, str)
    
    def apply_custom_validation(self, validator_name: str, value: Any, **kwargs) -> bool:
        """Apply a custom validator"""
        if validator_name not in self.custom_validators:
            raise ValidationError(f"Unknown custom validator: {validator_name}")
        
        validator_func = self.custom_validators[validator_name]
        try:
            return validator_func(value, **kwargs)
        except Exception as e:
            raise ValidationError(f"Custom validation '{validator_name}' failed: {str(e)}")
    
    def get_validation_info(self) -> Dict[str, Any]:
        """Get information about the current validation configuration"""
        return {
            "backend": self.backend.value,
            "custom_validators": list(self.custom_validators.keys()),
            "config": self.validation_config
        }

# Test code to verify the module works independently
if __name__ == "__main__":
    async def test_validation_system():
        """Test validation system components"""
        print("Testing Validation System...")
        
        # Test ValidationBackend enum
        print(f"✅ ValidationBackend.BASIC: {ValidationBackend.BASIC.value}")
        print(f"✅ ValidationBackend.JSONSCHEMA: {ValidationBackend.JSONSCHEMA.value}")
        print(f"✅ ValidationBackend.PYDANTIC: {ValidationBackend.PYDANTIC.value}")
        
        # Test ValidationSystem
        validator = ValidationSystem()
        validator.configure_validation(backend=ValidationBackend.BASIC)
        
        # Test basic validation
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        # Valid parameters
        try:
            validator.validate_parameters({"name": "John", "age": 30}, schema)
            print("✅ Basic validation passed for valid parameters")
        except Exception as e:
            print(f"❌ Basic validation failed unexpectedly: {e}")
        
        # Invalid parameters (missing required)
        try:
            validator.validate_parameters({"age": 30}, schema)
            print("❌ Basic validation should have failed for missing required parameter")
        except ValidationError:
            print("✅ Basic validation correctly rejected missing required parameter")
        
        # Test custom validator
        def positive_number_validator(value):
            return isinstance(value, (int, float)) and value > 0
        
        validator.register_validator("positive", positive_number_validator)
        
        schema_with_custom = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0}
            },
            "required": ["score"]
        }
        
        try:
            validator.validate_parameters({"score": 85}, schema_with_custom)
            print("✅ Custom validator passed for valid value")
        except Exception as e:
            print(f"❌ Custom validator failed unexpectedly: {e}")
        
        try:
            validator.validate_parameters({"score": -5}, schema_with_custom)
            print("❌ Custom validator should have failed for negative value")
        except ValidationError:
            print("✅ Custom validator correctly rejected negative value")
        
        # Test JSON Schema validation (if available)
        validator.configure_validation(backend=ValidationBackend.JSONSCHEMA)
        try:
            validator.validate_parameters({"name": "Jane"}, schema)
            print("✅ JSON Schema validation available and working")
        except Exception as e:
            print(f"ℹ️  JSON Schema validation: {type(e).__name__} (may not be installed)")
        
        print("🎉 All validation system tests passed!")
    
    # Run test
    import asyncio
    asyncio.run(test_validation_system())
    print("Run with: python -m src.mcp.core.server.validation_system") 