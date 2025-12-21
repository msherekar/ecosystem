"""
Data validation and sanitization for training data collection.
Ensures data quality, consistency, and security compliance.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    issues: List[Dict[str, Any]]
    sanitized_data: Optional[Dict[str, Any]] = None
    
    def add_issue(self, field: str, message: str, severity: ValidationSeverity,
                  suggestion: str = None) -> None:
        """Add validation issue"""
        self.issues.append({
            "field": field,
            "message": message,
            "severity": severity.value,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        })
        
        if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False

class ConversationValidator:
    """Validates conversation data for training"""
    
    def __init__(self):
        self.logger = logging.getLogger("conversation_validator")
        self.max_message_length = 50000  # Characters
        self.min_message_length = 1
        self.max_tools_per_conversation = 20
        self.allowed_analysis_types = {
            "scrna_seq", "rna_seq", "tabular", "general", "proteomics"
        }
        self.allowed_pipeline_steps = {
            "qc", "filtering", "normalization", "dimred", "clustering", 
            "dea", "pathway", "visualization", "unknown"
        }
    
    def validate_conversation_turn(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a conversation turn"""
        result = ValidationResult(is_valid=True, issues=[])
        sanitized = data.copy()
        
        # Validate required fields
        required_fields = ["user_message", "assistant_response", "timestamp"]
        for field in required_fields:
            if field not in data or data[field] is None:
                result.add_issue(
                    field, f"Required field '{field}' is missing",
                    ValidationSeverity.ERROR,
                    f"Provide a valid {field}"
                )
        
        # Validate user message
        if "user_message" in data:
            sanitized["user_message"] = self._validate_message(
                data["user_message"], "user_message", result
            )
        
        # Validate assistant response
        if "assistant_response" in data:
            sanitized["assistant_response"] = self._validate_message(
                data["assistant_response"], "assistant_response", result
            )
        
        # Validate timestamp
        if "timestamp" in data:
            sanitized["timestamp"] = self._validate_timestamp(
                data["timestamp"], result
            )
        
        # Validate analysis type
        if "analysis_type" in data:
            sanitized["analysis_type"] = self._validate_analysis_type(
                data["analysis_type"], result
            )
        
        # Validate pipeline step
        if "pipeline_step" in data:
            sanitized["pipeline_step"] = self._validate_pipeline_step(
                data["pipeline_step"], result
            )
        
        # Validate tools used
        if "tools_used" in data:
            sanitized["tools_used"] = self._validate_tools_used(
                data["tools_used"], result
            )
        
        # Validate context
        if "context" in data:
            sanitized["context"] = self._validate_context(
                data["context"], result
            )
        
        # Validate success flag
        if "success" in data:
            sanitized["success"] = self._validate_boolean(
                data["success"], "success", result
            )
        
        result.sanitized_data = sanitized
        return result
    
    def _validate_message(self, message: Any, field_name: str, 
                         result: ValidationResult) -> str:
        """Validate message content"""
        if not isinstance(message, str):
            result.add_issue(
                field_name, f"{field_name} must be a string",
                ValidationSeverity.ERROR,
                "Convert to string format"
            )
            return str(message) if message is not None else ""
        
        # Length validation
        if len(message) < self.min_message_length:
            result.add_issue(
                field_name, f"{field_name} is too short (min: {self.min_message_length})",
                ValidationSeverity.WARNING,
                "Provide more detailed content"
            )
        
        if len(message) > self.max_message_length:
            result.add_issue(
                field_name, f"{field_name} exceeds maximum length ({self.max_message_length})",
                ValidationSeverity.ERROR,
                "Truncate or split the message"
            )
            # Truncate with warning
            message = message[:self.max_message_length]
        
        # Content validation
        if message.strip() == "":
            result.add_issue(
                field_name, f"{field_name} cannot be empty or whitespace only",
                ValidationSeverity.ERROR,
                "Provide meaningful content"
            )
        
        # Sanitize content
        sanitized = self._sanitize_text(message)
        if sanitized != message:
            result.add_issue(
                field_name, f"{field_name} contained potentially harmful content",
                ValidationSeverity.WARNING,
                "Content was sanitized automatically"
            )
        
        return sanitized
    
    def _validate_timestamp(self, timestamp: Any, result: ValidationResult) -> datetime:
        """Validate timestamp"""
        if isinstance(timestamp, datetime):
            ts = timestamp
        elif isinstance(timestamp, str):
            try:
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                result.add_issue(
                    "timestamp", "Invalid timestamp format",
                    ValidationSeverity.ERROR,
                    "Use ISO format: YYYY-MM-DDTHH:MM:SS"
                )
                return datetime.now()
        else:
            result.add_issue(
                "timestamp", "Timestamp must be datetime or ISO string",
                ValidationSeverity.ERROR,
                "Provide valid timestamp"
            )
            return datetime.now()
        
        # Check if timestamp is reasonable
        now = datetime.now()
        if ts > now + timedelta(hours=1):
            result.add_issue(
                "timestamp", "Timestamp is in the future",
                ValidationSeverity.WARNING,
                "Check system clock"
            )
        
        if ts < now - timedelta(days=365):
            result.add_issue(
                "timestamp", "Timestamp is very old (>1 year)",
                ValidationSeverity.INFO,
                "Verify timestamp accuracy"
            )
        
        return ts
    
    def _validate_analysis_type(self, analysis_type: Any, 
                               result: ValidationResult) -> str:
        """Validate analysis type"""
        if not isinstance(analysis_type, str):
            result.add_issue(
                "analysis_type", "Analysis type must be a string",
                ValidationSeverity.ERROR
            )
            return "general"
        
        normalized = analysis_type.lower().strip()
        
        if normalized not in self.allowed_analysis_types:
            result.add_issue(
                "analysis_type", f"Unknown analysis type: {analysis_type}",
                ValidationSeverity.WARNING,
                f"Use one of: {', '.join(self.allowed_analysis_types)}"
            )
            # Try to map to closest match
            normalized = self._find_closest_match(normalized, self.allowed_analysis_types)
        
        return normalized
    
    def _validate_pipeline_step(self, pipeline_step: Any, 
                               result: ValidationResult) -> str:
        """Validate pipeline step"""
        if not isinstance(pipeline_step, str):
            result.add_issue(
                "pipeline_step", "Pipeline step must be a string",
                ValidationSeverity.ERROR
            )
            return "unknown"
        
        normalized = pipeline_step.lower().strip()
        
        if normalized not in self.allowed_pipeline_steps:
            result.add_issue(
                "pipeline_step", f"Unknown pipeline step: {pipeline_step}",
                ValidationSeverity.WARNING,
                f"Use one of: {', '.join(self.allowed_pipeline_steps)}"
            )
            normalized = self._find_closest_match(normalized, self.allowed_pipeline_steps)
        
        return normalized
    
    def _validate_tools_used(self, tools_used: Any, 
                            result: ValidationResult) -> List[Dict[str, Any]]:
        """Validate tools used list"""
        if not isinstance(tools_used, list):
            result.add_issue(
                "tools_used", "Tools used must be a list",
                ValidationSeverity.ERROR,
                "Provide list of tool objects"
            )
            return []
        
        if len(tools_used) > self.max_tools_per_conversation:
            result.add_issue(
                "tools_used", f"Too many tools ({len(tools_used)} > {self.max_tools_per_conversation})",
                ValidationSeverity.WARNING,
                "Consider breaking into multiple conversations"
            )
        
        validated_tools = []
        for i, tool in enumerate(tools_used):
            if isinstance(tool, dict):
                validated_tool = self._validate_tool_entry(tool, i, result)
                validated_tools.append(validated_tool)
            else:
                result.add_issue(
                    f"tools_used[{i}]", "Tool entry must be a dictionary",
                    ValidationSeverity.WARNING
                )
        
        return validated_tools
    
    def _validate_tool_entry(self, tool: Dict[str, Any], index: int, 
                            result: ValidationResult) -> Dict[str, Any]:
        """Validate individual tool entry"""
        validated = tool.copy()
        
        # Validate tool name
        if "name" not in tool or not tool["name"]:
            result.add_issue(
                f"tools_used[{index}].name", "Tool name is required",
                ValidationSeverity.WARNING
            )
            validated["name"] = "unknown"
        
        # Validate success flag
        if "success" in tool:
            validated["success"] = self._validate_boolean(
                tool["success"], f"tools_used[{index}].success", result
            )
        
        return validated
    
    def _validate_context(self, context: Any, result: ValidationResult) -> Dict[str, Any]:
        """Validate context dictionary"""
        if not isinstance(context, dict):
            result.add_issue(
                "context", "Context must be a dictionary",
                ValidationSeverity.ERROR,
                "Provide key-value pairs"
            )
            return {}
        
        validated = {}
        max_context_size = 100  # Max number of context keys
        
        if len(context) > max_context_size:
            result.add_issue(
                "context", f"Context too large ({len(context)} > {max_context_size} keys)",
                ValidationSeverity.WARNING,
                "Reduce context size or use nested structure"
            )
        
        for key, value in context.items():
            # Validate key
            if not isinstance(key, str):
                result.add_issue(
                    f"context.{key}", "Context keys must be strings",
                    ValidationSeverity.WARNING
                )
                continue
            
            # Sanitize key
            clean_key = re.sub(r'[^a-zA-Z0-9_-]', '_', key)
            if clean_key != key:
                result.add_issue(
                    f"context.{key}", "Context key contained invalid characters",
                    ValidationSeverity.INFO,
                    "Key was sanitized"
                )
            
            # Validate value (basic types only)
            if isinstance(value, (str, int, float, bool, list, dict)):
                validated[clean_key] = value
            else:
                result.add_issue(
                    f"context.{key}", "Context value has unsupported type",
                    ValidationSeverity.WARNING,
                    "Convert to supported type (str, int, float, bool, list, dict)"
                )
                validated[clean_key] = str(value)
        
        return validated
    
    def _validate_boolean(self, value: Any, field_name: str, 
                         result: ValidationResult) -> bool:
        """Validate boolean field"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ["true", "1", "yes", "on"]:
                return True
            elif lower_val in ["false", "0", "no", "off"]:
                return False
        
        result.add_issue(
            field_name, f"Invalid boolean value: {value}",
            ValidationSeverity.WARNING,
            "Use true/false"
        )
        return bool(value)
    
    def _sanitize_text(self, text: str) -> str:
        """Basic text sanitization"""
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def _find_closest_match(self, value: str, allowed_values: set) -> str:
        """Find closest match using simple string similarity"""
        if not value or not allowed_values:
            return "unknown"
        
        # Simple substring matching
        best_match = "unknown"
        best_score = 0
        
        for allowed in allowed_values:
            score = len(set(value) & set(allowed)) / len(set(value) | set(allowed))
            if score > best_score:
                best_score = score
                best_match = allowed
        
        return best_match if best_score > 0.3 else "unknown"

class DatasetValidator:
    """Validates complete training datasets"""
    
    def __init__(self):
        self.logger = logging.getLogger("dataset_validator")
        self.conversation_validator = ConversationValidator()
    
    def validate_dataset(self, dataset_data: Dict[str, Any]) -> ValidationResult:
        """Validate entire dataset"""
        result = ValidationResult(is_valid=True, issues=[])
        sanitized = dataset_data.copy()
        
        # Validate metadata
        if "metadata" not in dataset_data:
            result.add_issue(
                "metadata", "Dataset metadata is missing",
                ValidationSeverity.ERROR,
                "Add metadata section"
            )
        
        # Validate conversations
        if "conversations" not in dataset_data:
            result.add_issue(
                "conversations", "Conversations list is missing",
                ValidationSeverity.CRITICAL,
                "Add conversations array"
            )
            return result
        
        conversations = dataset_data["conversations"]
        if not isinstance(conversations, list):
            result.add_issue(
                "conversations", "Conversations must be a list",
                ValidationSeverity.CRITICAL
            )
            return result
        
        # Validate each conversation
        validated_conversations = []
        for i, conv in enumerate(conversations):
            conv_result = self.conversation_validator.validate_conversation_turn(conv)
            
            # Add conversation-specific issues to dataset result
            for issue in conv_result.issues:
                issue["field"] = f"conversations[{i}].{issue['field']}"
                result.issues.append(issue)
            
            if not conv_result.is_valid:
                result.is_valid = False
            
            if conv_result.sanitized_data:
                validated_conversations.append(conv_result.sanitized_data)
        
        sanitized["conversations"] = validated_conversations
        result.sanitized_data = sanitized
        
        return result


def main():
    """Test validation system"""
    print("Testing Training Data Validation")
if __name__ == "__main__":
    main()