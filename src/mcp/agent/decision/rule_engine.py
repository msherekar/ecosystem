"""
Dynamic Rule Engine
Configuration-driven selection rules for provider selection.
"""

import yaml
import json
import ast
import operator
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import structlog


@dataclass
class SelectionRule:
    """Configuration-driven selection rule."""
    name: str
    condition: str  # Python expression string
    action: str     # Provider to select or action to take
    priority: int = 0
    enabled: bool = True
    description: str = ""
    category: str = "general"


class SafeEvaluator:
    """Safe expression evaluator with limited operations."""
    
    # Allowed operators and functions
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: operator.and_,
        ast.Or: operator.or_,
        ast.Not: operator.not_,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
    }
    
    ALLOWED_FUNCTIONS = {
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'max': max,
        'min': min,
        'abs': abs,
        'round': round,
        'sum': sum,
        'any': any,
        'all': all,
    }
    
    def __init__(self):
        self.logger = structlog.get_logger("safe_evaluator")
    
    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """Safely evaluate expression with given context."""
        try:
            # Parse the expression
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate with context
            return self._eval_node(tree.body, context)
            
        except Exception as e:
            self.logger.warning("Expression evaluation failed", 
                              expression=expression, error=str(e))
            return False
    
    def _eval_node(self, node, context: Dict[str, Any]) -> Any:
        """Recursively evaluate AST node."""
        
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
            return node.n
        
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            return node.s
        
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            elif node.id in self.ALLOWED_FUNCTIONS:
                return self.ALLOWED_FUNCTIONS[node.id]
            else:
                raise NameError(f"Name '{node.id}' is not defined")
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if op_func:
                return op_func(left, right)
            else:
                raise TypeError(f"Operator {type(node.op)} is not allowed")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if op_func:
                return op_func(operand)
            else:
                raise TypeError(f"Unary operator {type(node.op)} is not allowed")
        
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_func = self.ALLOWED_OPERATORS.get(type(op))
                if op_func:
                    if not op_func(left, right):
                        return False
                    left = right
                else:
                    raise TypeError(f"Comparison operator {type(op)} is not allowed")
            return True
        
        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(value, context) for value in node.values]
            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if op_func:
                if isinstance(node.op, ast.And):
                    return all(values)
                elif isinstance(node.op, ast.Or):
                    return any(values)
            raise TypeError(f"Boolean operator {type(node.op)} is not allowed")
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in self.ALLOWED_FUNCTIONS:
                func = self.ALLOWED_FUNCTIONS[func_name]
                args = [self._eval_node(arg, context) for arg in node.args]
                return func(*args)
            else:
                raise NameError(f"Function '{func_name}' is not allowed")
        
        elif isinstance(node, ast.List):
            return [self._eval_node(element, context) for element in node.elts]
        
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(element, context) for element in node.elts)
        
        elif isinstance(node, ast.Dict):
            keys = [self._eval_node(k, context) for k in node.keys]
            values = [self._eval_node(v, context) for v in node.values]
            return dict(zip(keys, values))
        
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value, context)
            slice_val = self._eval_node(node.slice, context)
            return value[slice_val]
        
        elif isinstance(node, ast.Index):  # Python < 3.9 compatibility
            return self._eval_node(node.value, context)
        
        else:
            raise TypeError(f"AST node type {type(node)} is not supported")


class RuleEngine:
    """
    Dynamic rule engine for provider selection.
    
    Features:
    - YAML/JSON configuration support
    - Safe expression evaluation
    - Priority-based rule ordering
    - Rule categories and grouping
    - Runtime rule modification
    - Comprehensive logging
    """
    
    def __init__(self, config_path: str = None):
        self.logger = structlog.get_logger("rule_engine")
        
        # Rule storage
        self.rules: List[SelectionRule] = []
        self.rule_categories: Dict[str, List[SelectionRule]] = {}
        
        # Evaluation engine
        self.evaluator = SafeEvaluator()
        
        # Custom functions that can be used in rules
        self.custom_functions: Dict[str, Callable] = {
            'contains': lambda text, substring: substring.lower() in text.lower(),
            'starts_with': lambda text, prefix: text.lower().startswith(prefix.lower()),
            'ends_with': lambda text, suffix: text.lower().endswith(suffix.lower()),
            'word_count': lambda text: len(text.split()),
            'char_count': lambda text: len(text),
            'is_empty': lambda value: not value or (isinstance(value, str) and not value.strip()),
            'get_nested': lambda obj, key, default=None: obj.get(key, default) if isinstance(obj, dict) else default,
        }
        
        # Load rules from configuration if provided
        if config_path:
            self.load_rules_from_config(config_path)
    
    def load_rules_from_config(self, config_path: str):
        """Load selection rules from configuration file."""
        try:
            config_file = Path(config_path)
            
            if not config_file.exists():
                self.logger.warning("Config file not found", path=config_path)
                return
            
            # Determine file format
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                self.logger.error("Unsupported config file format", path=config_path)
                return
            
            # Parse rules
            self._parse_rules_config(config)
            
            self.logger.info("Rules loaded from config", 
                           path=config_path, count=len(self.rules))
            
        except Exception as e:
            self.logger.error("Failed to load rules from config", 
                            path=config_path, error=str(e))
    
    def _parse_rules_config(self, config: Dict[str, Any]):
        """Parse rules from configuration dictionary."""
        rules_config = config.get('selection_rules', [])
        
        for rule_config in rules_config:
            try:
                rule = SelectionRule(
                    name=rule_config['name'],
                    condition=rule_config['condition'],
                    action=rule_config['action'],
                    priority=rule_config.get('priority', 0),
                    enabled=rule_config.get('enabled', True),
                    description=rule_config.get('description', ''),
                    category=rule_config.get('category', 'general')
                )
                
                self.add_rule(rule)
                
            except KeyError as e:
                self.logger.error("Invalid rule configuration", 
                                rule=rule_config, missing_key=str(e))
            except Exception as e:
                self.logger.error("Failed to parse rule", 
                                rule=rule_config, error=str(e))
    
    def add_rule(self, rule: SelectionRule):
        """Add a rule to the engine."""
        self.rules.append(rule)
        
        # Add to category
        if rule.category not in self.rule_categories:
            self.rule_categories[rule.category] = []
        self.rule_categories[rule.category].append(rule)
        
        # Sort rules by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self.rule_categories[rule.category].sort(key=lambda r: r.priority, reverse=True)
        
        self.logger.debug("Rule added", name=rule.name, priority=rule.priority)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                removed_rule = self.rules.pop(i)
                
                # Remove from category
                if removed_rule.category in self.rule_categories:
                    self.rule_categories[removed_rule.category].remove(removed_rule)
                
                self.logger.info("Rule removed", name=rule_name)
                return True
        
        self.logger.warning("Rule not found for removal", name=rule_name)
        return False
    
    def evaluate_rules(
        self, 
        context: 'SelectionContext', 
        available_providers: Dict[str, Any]
    ) -> Optional[str]:
        """Evaluate rules against context and return provider selection."""
        
        # Prepare evaluation context
        eval_context = self._prepare_evaluation_context(context, available_providers)
        
        # Evaluate rules in priority order
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Evaluate rule condition
                if self.evaluator.evaluate(rule.condition, eval_context):
                    self.logger.info("Rule matched", 
                                   name=rule.name, 
                                   action=rule.action,
                                   priority=rule.priority)
                    
                    # Handle different action types
                    return self._execute_rule_action(rule.action, eval_context)
                    
            except Exception as e:
                self.logger.warning("Rule evaluation failed", 
                                  name=rule.name, 
                                  condition=rule.condition,
                                  error=str(e))
        
        # No rule matched
        return None
    
    def _prepare_evaluation_context(
        self, 
        context: 'SelectionContext', 
        available_providers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for rule evaluation."""
        
        eval_context = {
            # Message context
            'message': context.user_message,
            'message_length': len(context.user_message),
            'word_count': len(context.user_message.split()),
            'char_count': len(context.user_message),
            
            # Usage statistics
            'external_calls': context.usage_stats.get('external_calls', 0),
            'local_calls': context.usage_stats.get('local_calls', 0),
            'total_calls': sum(context.usage_stats.values()),
            
            # Budget and constraints
            'cost_budget': context.cost_budget,
            'quality_threshold': context.quality_threshold,
            'latency_requirement': context.latency_requirement,
            
            # Session context
            'session_type': context.session_context.get('type', 'interactive'),
            'user_id': context.user_id,
            'session_id': context.session_id,
            
            # Provider context
            'available_providers': list(available_providers.keys()),
            'provider_count': len(available_providers),
            'has_external': any('external' in name.lower() for name in available_providers.keys()),
            'has_local': any('local' in name.lower() for name in available_providers.keys()),
            
            # Security context
            'security_level': context.security_context.get('level', 'standard'),
            'user_role': context.security_context.get('user_role', 'user'),
            
            # Custom functions
            **self.custom_functions
        }
        
        return eval_context
    
    def _execute_rule_action(self, action: str, context: Dict[str, Any]) -> Optional[str]:
        """Execute rule action and return result."""
        
        # Direct provider name
        if action in context.get('available_providers', []):
            return action
        
        # Conditional action (simple evaluation)
        if action.startswith('if '):
            # Parse conditional action: "if condition then provider1 else provider2"
            try:
                parts = action.split(' then ')
                if len(parts) == 2:
                    condition = parts[0][3:].strip()  # Remove "if "
                    then_else = parts[1].split(' else ')
                    
                    if self.evaluator.evaluate(condition, context):
                        return then_else[0].strip()
                    elif len(then_else) > 1:
                        return then_else[1].strip()
                        
            except Exception as e:
                self.logger.warning("Failed to execute conditional action", 
                                  action=action, error=str(e))
        
        # Fallback: try to evaluate as expression
        try:
            result = self.evaluator.evaluate(action, context)
            if isinstance(result, str) and result in context.get('available_providers', []):
                return result
        except Exception:
            pass
        
        self.logger.warning("Unable to execute rule action", action=action)
        return None
    
    def get_rules_by_category(self, category: str) -> List[SelectionRule]:
        """Get all rules in a specific category."""
        return self.rule_categories.get(category, [])
    
    def get_active_rules(self) -> List[SelectionRule]:
        """Get all enabled rules."""
        return [rule for rule in self.rules if rule.enabled]
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a rule by name."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                self.logger.info("Rule enabled", name=rule_name)
                return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a rule by name."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                self.logger.info("Rule disabled", name=rule_name)
                return True
        return False
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        total_rules = len(self.rules)
        enabled_rules = len(self.get_active_rules())
        categories = list(self.rule_categories.keys())
        
        return {
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'disabled_rules': total_rules - enabled_rules,
            'categories': categories,
            'rules_by_category': {cat: len(rules) for cat, rules in self.rule_categories.items()}
        }


def main():
    """Main function for testing rule engine."""
    
    def test_rule_engine():
        print("🧪 Testing Rule Engine...")
        
        # Create rule engine
        engine = RuleEngine()
        
        # Add test rules
        test_rules = [
            SelectionRule(
                name="emergency_fallback",
                condition="provider_count == 1",
                action="available_providers[0]",
                priority=100,
                description="Use any available provider when only one exists"
            ),
            SelectionRule(
                name="cost_budget_exceeded",
                condition="cost_budget is not None and cost_budget < 0.10",
                action="'local'",
                priority=90,
                description="Use local provider when budget is low"
            ),
            SelectionRule(
                name="complex_bioinformatics",
                condition="contains(message, 'differential expression') or contains(message, 'pathway analysis')",
                action="'external'",
                priority=80,
                description="Use external provider for complex bioinformatics queries"
            ),
            SelectionRule(
                name="simple_query",
                condition="starts_with(message, 'what is') and word_count < 10",
                action="'local'",
                priority=70,
                description="Use local provider for simple informational queries"
            ),
            SelectionRule(
                name="external_call_limit",
                condition="external_calls >= 10",
                action="'local'",
                priority=60,
                description="Use local provider when external call limit reached"
            )
        ]
        
        for rule in test_rules:
            engine.add_rule(rule)
        
        print(f"✅ Added {len(test_rules)} test rules")
        
        # Test rule statistics
        stats = engine.get_rule_stats()
        print(f"📊 Rule stats: {stats}")
        
        # Create mock context for testing
        from dataclasses import dataclass
        from typing import Dict, Any
        
        @dataclass
        class MockContext:
            user_message: str
            user_id: str = "test_user"
            session_id: str = "test_session"
            usage_stats: Dict[str, int] = None
            cost_budget: float = None
            quality_threshold: float = None
            latency_requirement: float = None
            session_context: Dict[str, Any] = None
            security_context: Dict[str, Any] = None
            
            def __post_init__(self):
                if self.usage_stats is None:
                    self.usage_stats = {}
                if self.session_context is None:
                    self.session_context = {}
                if self.security_context is None:
                    self.security_context = {}
        
        # Test cases
        test_cases = [
            {
                "context": MockContext(
                    user_message="what is RNA-seq?",
                    usage_stats={"external_calls": 2}
                ),
                "providers": {"external": None, "local": None},
                "expected": "local"
            },
            {
                "context": MockContext(
                    user_message="help me with differential expression analysis",
                    usage_stats={"external_calls": 5}
                ),
                "providers": {"external": None, "local": None},
                "expected": "external"
            },
            {
                "context": MockContext(
                    user_message="analyze my data",
                    usage_stats={"external_calls": 12}
                ),
                "providers": {"external": None, "local": None},
                "expected": "local"
            },
            {
                "context": MockContext(
                    user_message="test query",
                    cost_budget=0.05
                ),
                "providers": {"external": None, "local": None},
                "expected": "local"
            }
        ]
        
        print("\n🔍 Testing rule evaluation:")
        for i, case in enumerate(test_cases, 1):
            result = engine.evaluate_rules(case["context"], case["providers"])
            expected = case["expected"]
            status = "✅" if result == expected else "❌"
            
            print(f"   Test {i}: '{case['context'].user_message[:30]}...' → {result} {status}")
            if result != expected:
                print(f"      Expected: {expected}, Got: {result}")
        
        # Test rule management
        print("\n⚙️  Testing rule management:")
        
        # Disable a rule
        engine.disable_rule("simple_query")
        print("   ✅ Disabled 'simple_query' rule")
        
        # Re-test with disabled rule
        result = engine.evaluate_rules(test_cases[0]["context"], test_cases[0]["providers"])
        print(f"   After disabling rule: {result}")
        
        # Re-enable rule
        engine.enable_rule("simple_query")
        print("   ✅ Re-enabled 'simple_query' rule")
        
        print("\n🎉 Rule engine tests completed!")
    
    test_rule_engine()


if __name__ == "__main__":
    main() 