"""
Domain Prompts System - Enhanced Command Line Interface

This module provides a command-line interface for managing and using
the domain prompts system with enhanced scalability, security, and Electron integration.

Usage:
    python -m domain_prompts --help
    python -m domain_prompts list --output json
    python -m domain_prompts info scrnaseq --format electron
    python -m domain_prompts validate --emit-events
    python -m domain_prompts batch-process config.json
"""

import argparse
import asyncio
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from . import (
    initialize_system, get_system_info, validate_system,
    list_techniques, get_expert, search_techniques,
    create_new_technique, export_system_data,
    get_techniques_by_category, __version__,
    emit_system_event, emit_ui_update, emit_error,
    get_event_emitter, get_performance_monitor,
    SecurityValidator, SecurityLevel,
    create_async_expert, async_timer
)

logger = logging.getLogger(__name__)

# Global state for Electron integration
_electron_mode = False
_emit_events = False
_output_format = "text"
_progress_callback = None


class ProgressReporter:
    """Progress reporting for long operations with Electron integration"""
    
    def __init__(self, total_steps: int, operation_name: str, emit_events: bool = False):
        self.total_steps = total_steps
        self.current_step = 0
        self.operation_name = operation_name
        self.emit_events = emit_events
        self.start_time = time.time()
    
    def update(self, step_name: str = "", increment: int = 1):
        """Update progress and emit events if needed"""
        self.current_step += increment
        progress_pct = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time
        
        if self.emit_events:
            emit_ui_update("cli_progress", "update", {
                "operation": self.operation_name,
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "progress_percent": progress_pct,
                "step_name": step_name,
                "elapsed_seconds": elapsed
            })
        else:
            if step_name:
                print(f"[{self.current_step}/{self.total_steps}] {step_name} ({progress_pct:.1f}%)")
    
    def complete(self, message: str = ""):
        """Mark operation as complete"""
        elapsed = time.time() - self.start_time
        if self.emit_events:
            emit_ui_update("cli_progress", "complete", {
                "operation": self.operation_name,
                "message": message,
                "total_time": elapsed
            })
        else:
            print(f"✓ {self.operation_name} completed in {elapsed:.2f}s - {message}")


def safe_output(data: Any, format_type: str = "text") -> str:
    """Safely format output with security validation"""
    try:
        if format_type.lower() == "json":
            # Validate and sanitize for JSON output
            if isinstance(data, dict):
                sanitized_data = SecurityValidator.validate_parameters(
                    {k: str(v) for k, v in data.items() if v is not None}
                )
            else:
                sanitized_data = SecurityValidator.validate_string(str(data), 10000, "output_data")
            
            return json.dumps(sanitized_data, indent=2, ensure_ascii=False)
        
        elif format_type.lower() == "electron":
            # Electron-friendly format with metadata
            electron_output = {
                "type": "cli_response",
                "timestamp": time.time(),
                "data": data,
                "format_version": "2.0"
            }
            return json.dumps(electron_output, indent=2, default=str)
        
        else:
            # Text format with basic sanitization
            return SecurityValidator.sanitize_for_logging(str(data), 5000)
            
    except Exception as e:
        error_msg = f"Output formatting error: {e}"
        if _emit_events:
            emit_error("output_error", error_msg, {"format_type": format_type})
        return error_msg


def format_expert_info(expert, output_format: str = "text") -> str:
    """Format expert information for display with enhanced security"""
    try:
        metadata = expert.get_metadata()
        prompts = expert.get_prompts()
        
        if output_format.lower() in ["json", "electron"]:
            # Structured data for programmatic consumption
            expert_data = {
                "name": metadata.name,
                "display_name": metadata.display_name,
                "category": metadata.category,
                "subcategory": metadata.subcategory,
                "description": metadata.description,
                "expertise_level": metadata.required_expertise.value,
                "aliases": metadata.aliases,
                "related_techniques": metadata.related_techniques,
                "applications": metadata.typical_applications,
                "prompts": {
                    name: {
                        "description": prompt.description,
                        "parameters": prompt.parameters,
                        "context": prompt.biological_context.value,
                        "expertise_level": prompt.expertise_level.value,
                        "tags": list(prompt.tags)
                    }
                    for name, prompt in prompts.items()
                },
                "prompt_count": len(prompts),
                "version": metadata.version,
                "author": metadata.author
            }
            return safe_output(expert_data, output_format)
        
        else:
            # Human-readable text format
            info = f"""
{metadata.display_name}
{'=' * len(metadata.display_name)}
Name: {metadata.name}
Category: {metadata.category}
{f"Subcategory: {metadata.subcategory}" if metadata.subcategory else ""}
Description: {metadata.description}
Expertise Level: {metadata.required_expertise.value}
Aliases: {', '.join(metadata.aliases) if metadata.aliases else 'None'}
Related Techniques: {', '.join(metadata.related_techniques) if metadata.related_techniques else 'None'}

Applications:
{chr(10).join(f"  - {app}" for app in metadata.typical_applications)}

Prompts Available: {len(prompts)}
{chr(10).join(f"  - {name}: {prompt.description}" for name, prompt in prompts.items())}
"""
            return SecurityValidator.sanitize_for_logging(info, 10000)
    
    except Exception as e:
        error_msg = f"Error formatting expert info: {e}"
        if _emit_events:
            emit_error("formatting_error", error_msg, {"expert": str(expert)})
        return error_msg


async def cmd_list_async(args) -> int:
    """Async version of list command with enhanced features"""
    progress = ProgressReporter(3, "list_techniques", _emit_events)
    
    try:
        progress.update("Retrieving techniques")
        techniques = list_techniques()
        
        if not techniques:
            result = {"error": "No techniques available. Try running initialization first."}
            print(safe_output(result, args.output))
            return 1
        
        progress.update("Filtering and organizing")
        
        if args.category:
            # Validate category input
            category = SecurityValidator.validate_string(args.category, 100, "category")
            category_techniques = get_techniques_by_category(category)
            result_data = {
                "category": category,
                "techniques": []
            }
            
            for technique in category_techniques:
                expert = get_expert(technique)
                if expert:
                    metadata = expert.get_metadata()
                    result_data["techniques"].append({
                        "name": technique,
                        "display_name": metadata.display_name,
                        "description": metadata.description
                    })
        else:
            result_data = {
                "total_count": len(techniques),
                "techniques": []
            }
            
            for technique in sorted(techniques):
                expert = get_expert(technique)
                if expert:
                    metadata = expert.get_metadata()
                    result_data["techniques"].append({
                        "name": technique,
                        "display_name": metadata.display_name,
                        "category": metadata.category,
                        "prompt_count": len(expert.get_prompts())
                    })
                else:
                    result_data["techniques"].append({
                        "name": technique,
                        "display_name": technique,
                        "category": "unknown",
                        "metadata_unavailable": True
                    })
        
        progress.update("Formatting output")
        
        if args.output.lower() in ["json", "electron"]:
            print(safe_output(result_data, args.output))
        else:
            # Text format
            if args.category:
                print(f"Techniques in category '{args.category}':")
                for tech in result_data["techniques"]:
                    print(f"  - {tech['name']}: {tech['display_name']}")
            else:
                print(f"Available techniques ({result_data['total_count']}):")
                for tech in result_data["techniques"]:
                    if tech.get("metadata_unavailable"):
                        print(f"  - {tech['name']}: (metadata unavailable)")
                    else:
                        print(f"  - {tech['name']}: {tech['display_name']} ({tech['category']})")
        
        progress.complete(f"Listed {len(result_data['techniques'])} techniques")
        return 0
        
    except Exception as e:
        error_msg = f"Failed to list techniques: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "list"})
        print(safe_output({"error": error_msg}, args.output))
        return 1


def cmd_list(args) -> int:
    """List all available techniques with enhanced output formats"""
    return asyncio.run(cmd_list_async(args))


async def cmd_info_async(args) -> int:
    """Async version of info command with enhanced security"""
    progress = ProgressReporter(4, "get_expert_info", _emit_events)
    
    try:
        # Validate technique name
        progress.update("Validating input")
        technique = SecurityValidator.validate_identifier(args.technique, "technique")
        
        progress.update("Retrieving expert")
        expert = get_expert(technique)
        
        if not expert:
            available = sorted(list_techniques())
            result = {
                "error": f"Technique '{technique}' not found",
                "available_techniques": available
            }
            print(safe_output(result, args.format))
            return 1
        
        progress.update("Formatting expert information")
        expert_info = format_expert_info(expert, args.format)
        print(expert_info)
        
        # Show validation status
        progress.update("Validating prompts")
        errors = expert.validate_prompts()
        
        validation_result = {
            "validation_passed": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors if errors else []
        }
        
        if args.format.lower() in ["json", "electron"]:
            print(safe_output(validation_result, args.format))
        else:
            if errors:
                print("\nValidation Issues:")
                for error in errors:
                    print(f"  ⚠ {error}")
            else:
                print("\n✓ All prompts validated successfully")
        
        progress.complete(f"Retrieved info for {technique}")
        return 0
        
    except Exception as e:
        error_msg = f"Failed to get expert info: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "info", "technique": args.technique})
        print(safe_output({"error": error_msg}, args.format))
        return 1


def cmd_info(args) -> int:
    """Show detailed information about a technique"""
    return asyncio.run(cmd_info_async(args))


async def cmd_search_async(args) -> int:
    """Async search with enhanced filtering and output"""
    progress = ProgressReporter(3, "search_techniques", _emit_events)
    
    try:
        # Validate search query
        progress.update("Validating search query")
        query = SecurityValidator.validate_string(args.query, 200, "search_query")
        
        progress.update("Searching techniques")
        experts = search_techniques(query)
        
        if not experts:
            result = {"error": f"No techniques found matching '{query}'", "query": query}
            print(safe_output(result, args.output))
            return 1
        
        progress.update("Formatting results")
        
        result_data = {
            "query": query,
            "match_count": len(experts),
            "results": []
        }
        
        for expert in experts:
            metadata = expert.get_metadata()
            expert_result = {
                "name": metadata.name,
                "display_name": metadata.display_name,
                "category": metadata.category,
                "description": metadata.description if args.verbose else metadata.description[:100] + "..."
            }
            
            if args.verbose:
                expert_result.update({
                    "aliases": metadata.aliases,
                    "applications": metadata.typical_applications,
                    "expertise_level": metadata.required_expertise.value,
                    "prompt_count": len(expert.get_prompts())
                })
            
            result_data["results"].append(expert_result)
        
        if args.output.lower() in ["json", "electron"]:
            print(safe_output(result_data, args.output))
        else:
            print(f"Techniques matching '{query}' ({len(experts)}):")
            for result in result_data["results"]:
                print(f"  - {result['name']}: {result['display_name']}")
                if args.verbose:
                    print(f"    Category: {result['category']}")
                    print(f"    Description: {result['description']}")
        
        progress.complete(f"Found {len(experts)} matches")
        return 0
        
    except Exception as e:
        error_msg = f"Search failed: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "search", "query": args.query})
        print(safe_output({"error": error_msg}, args.output))
        return 1


def cmd_search(args) -> int:
    """Search for techniques"""
    return asyncio.run(cmd_search_async(args))


async def cmd_validate_async(args) -> int:
    """Async validation with detailed reporting"""
    progress = ProgressReporter(4, "system_validation", _emit_events)
    
    try:
        progress.update("Starting system validation")
        print("Validating domain prompts system...")
        
        progress.update("Running validation checks")
        validation_results = validate_system()
        
        progress.update("Analyzing results")
        
        result_data = {
            "validation_summary": {
                "total_experts": validation_results['total_experts'],
                "experts_with_errors": validation_results['experts_with_errors'],
                "total_errors": validation_results['total_errors'],
                "system_healthy": validation_results['system_healthy']
            },
            "detailed_results": validation_results['validation_results'] if args.verbose else {},
            "timestamp": time.time()
        }
        
        if args.output.lower() in ["json", "electron"]:
            print(safe_output(result_data, args.output))
        else:
            print(f"\nValidation Results:")
            print(f"  Total experts: {validation_results['total_experts']}")
            print(f"  Experts with errors: {validation_results['experts_with_errors']}")
            print(f"  Total errors: {validation_results['total_errors']}")
            print(f"  System healthy: {'✓ Yes' if validation_results['system_healthy'] else '✗ No'}")
            
            if validation_results['total_errors'] > 0 and args.verbose:
                print(f"\nDetailed Error Report:")
                for expert_name, errors in validation_results['validation_results'].items():
                    if errors:
                        print(f"\n{expert_name}:")
                        for error in errors:
                            print(f"  ✗ {error}")
        
        # Export validation results if requested
        if args.export:
            progress.update("Exporting validation results")
            export_path = SecurityValidator.validate_file_path(Path(args.export), "write")
            
            validation_data = {
                "timestamp": time.time(),
                "version": __version__,
                "validation_results": validation_results,
                "system_info": get_system_info()
            }
            
            with open(export_path, 'w') as f:
                json.dump(validation_data, f, indent=2, default=str)
            
            print(f"\nValidation results exported to: {export_path}")
        
        progress.complete("Validation completed")
        return 0 if validation_results['system_healthy'] else 1
        
    except Exception as e:
        error_msg = f"Validation failed: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "validate"})
        print(safe_output({"error": error_msg}, args.output))
        return 1


def cmd_validate(args) -> int:
    """Validate the system"""
    return asyncio.run(cmd_validate_async(args))


async def cmd_create_async(args) -> int:
    """Async create with enhanced validation"""
    progress = ProgressReporter(5, "create_technique", _emit_events)
    
    try:
        # Validate all inputs
        progress.update("Validating inputs")
        technique_name = SecurityValidator.validate_identifier(args.name, "technique_name")
        display_name = SecurityValidator.validate_string(args.display_name or args.name, 200, "display_name")
        description = SecurityValidator.validate_string(
            args.description or f"Analysis technique for {args.name}", 2000, "description"
        )
        category = SecurityValidator.validate_string(args.category, 100, "category")
        
        progress.update("Checking for conflicts")
        existing_techniques = list_techniques()
        if technique_name in existing_techniques:
            error_msg = f"Technique '{technique_name}' already exists"
            print(safe_output({"error": error_msg}, args.output))
            return 1
        
        progress.update("Creating technique")
        output_dir = None
        if args.output_dir:
            output_dir = SecurityValidator.validate_file_path(Path(args.output_dir), "write")
        
        output_path = create_new_technique(
            technique_name=technique_name,
            display_name=display_name,
            description=description,
            category=category,
            output_dir=output_dir
        )
        
        progress.update("Validating created technique")
        
        result_data = {
            "technique_name": technique_name,
            "display_name": display_name,
            "output_path": str(output_path),
            "category": category,
            "next_steps": [
                "Edit the file to add custom prompts and metadata",
                "Run validation to check for issues",
                "Test the new technique"
            ]
        }
        
        if args.output.lower() in ["json", "electron"]:
            print(safe_output(result_data, args.output))
        else:
            print(f"✓ Created new technique module: {output_path}")
            print(f"  Edit the file to add custom prompts and metadata.")
            print(f"  Run 'python -m domain_prompts validate' to check for issues.")
        
        progress.complete(f"Created technique: {technique_name}")
        return 0
        
    except Exception as e:
        error_msg = f"Failed to create technique: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "create", "technique": args.name})
        print(safe_output({"error": error_msg}, args.output))
        return 1


def cmd_create(args) -> int:
    """Create a new technique"""
    return asyncio.run(cmd_create_async(args))


async def cmd_export_async(args) -> int:
    """Async export with progress tracking"""
    progress = ProgressReporter(4, "export_system_data", _emit_events)
    
    try:
        progress.update("Validating export path")
        output_path = SecurityValidator.validate_file_path(Path(args.output), "write")
        
        progress.update("Gathering system data")
        
        # Use enhanced export with performance data if requested
        include_performance = getattr(args, 'include_performance', False)
        
        progress.update("Exporting data")
        export_system_data(
            output_path, 
            include_prompts=args.include_prompts,
            include_performance=include_performance
        )
        
        progress.update("Finalizing export")
        
        result_data = {
            "export_path": str(output_path),
            "include_prompts": args.include_prompts,
            "include_performance": include_performance,
            "file_size": output_path.stat().st_size if output_path.exists() else 0,
            "timestamp": time.time()
        }
        
        if args.output_format.lower() in ["json", "electron"]:
            print(safe_output(result_data, args.output_format))
        else:
            print(f"✓ System data exported to: {output_path}")
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"  File size: {size_mb:.2f} MB")
        
        progress.complete("Export completed")
        return 0
        
    except Exception as e:
        error_msg = f"Failed to export data: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "export"})
        print(safe_output({"error": error_msg}, getattr(args, 'output_format', 'text')))
        return 1


def cmd_export(args) -> int:
    """Export system data"""
    return asyncio.run(cmd_export_async(args))


async def cmd_batch_process_async(args) -> int:
    """Batch process multiple commands from configuration file"""
    progress = ProgressReporter(5, "batch_process", _emit_events)
    
    try:
        progress.update("Loading batch configuration")
        config_path = SecurityValidator.validate_file_path(Path(args.config_file), "read")
        
        with open(config_path) as f:
            batch_config = json.load(f)
        
        # Validate configuration structure
        if "commands" not in batch_config:
            raise ValueError("Batch config must contain 'commands' array")
        
        commands = batch_config["commands"]
        progress.total_steps = len(commands) + 2
        
        results = []
        
        progress.update("Processing batch commands")
        
        # Process commands concurrently if requested
        max_concurrent = batch_config.get("max_concurrent", 1)
        
        if max_concurrent > 1:
            # Concurrent processing
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_command(cmd_config):
                async with semaphore:
                    return await _execute_batch_command(cmd_config)
            
            tasks = [process_command(cmd) for cmd in commands]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Sequential processing
            for cmd_config in commands:
                result = await _execute_batch_command(cmd_config)
                results.append(result)
                progress.update(f"Completed: {cmd_config.get('name', 'unnamed')}")
        
        progress.update("Compiling results")
        
        batch_results = {
            "batch_name": batch_config.get("name", "unnamed_batch"),
            "total_commands": len(commands),
            "successful": sum(1 for r in results if not isinstance(r, Exception) and r.get("success", False)),
            "failed": sum(1 for r in results if isinstance(r, Exception) or not r.get("success", True)),
            "results": results,
            "timestamp": time.time()
        }
        
        if args.output.lower() in ["json", "electron"]:
            print(safe_output(batch_results, args.output))
        else:
            print(f"Batch processing completed:")
            print(f"  Total commands: {batch_results['total_commands']}")
            print(f"  Successful: {batch_results['successful']}")
            print(f"  Failed: {batch_results['failed']}")
        
        progress.complete("Batch processing completed")
        return 0 if batch_results['failed'] == 0 else 1
        
    except Exception as e:
        error_msg = f"Batch processing failed: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "batch_process"})
        print(safe_output({"error": error_msg}, getattr(args, 'output', 'text')))
        return 1


async def _execute_batch_command(cmd_config: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single batch command"""
    try:
        cmd_type = cmd_config["type"]
        cmd_args = cmd_config.get("args", {})
        
        # Create mock args object for existing command functions
        class MockArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        # Map command types to functions
        command_map = {
            "list": cmd_list_async,
            "info": cmd_info_async,
            "search": cmd_search_async,
            "validate": cmd_validate_async,
            "create": cmd_create_async,
            "export": cmd_export_async
        }
        
        if cmd_type not in command_map:
            return {"success": False, "error": f"Unknown command type: {cmd_type}"}
        
        # Execute command
        mock_args = MockArgs(output="json", **cmd_args)
        result_code = await command_map[cmd_type](mock_args)
        
        return {
            "success": result_code == 0,
            "command": cmd_type,
            "args": cmd_args,
            "exit_code": result_code
        }
        
    except Exception as e:
        return {"success": False, "error": str(e), "command": cmd_config}


def cmd_batch_process(args) -> int:
    """Process multiple commands from configuration file"""
    return asyncio.run(cmd_batch_process_async(args))


def cmd_system_info(args) -> int:
    """Show system information with enhanced details"""
    try:
        info = get_system_info()
        
        # Add performance data
        perf_monitor = get_performance_monitor()
        perf_stats = perf_monitor.get_stats()
        
        # Add event system data
        event_emitter = get_event_emitter()
        event_stats = event_emitter.get_stats()
        
        enhanced_info = {
            "system_info": info,
            "performance": perf_stats,
            "events": event_stats,
            "security": {
                "current_level": "PUBLIC",  # Could be configurable
                "validation_enabled": True,
                "safe_operations": True
            }
        }
        
        if args.output.lower() in ["json", "electron"]:
            print(safe_output(enhanced_info, args.output))
        else:
            print(f"Domain Prompts System Information")
            print(f"=" * 40)
            print(f"Version: {info['version']}")
            print(f"Author: {info['author']}")
            print(f"Description: {info['description']}")
            
            stats = info['registry_stats']
            print(f"\nRegistry Statistics:")
            print(f"  Total experts: {stats['total_experts']}")
            print(f"  Discovery paths: {stats.get('discovery_paths', 0)}")
            print(f"  Loaded modules: {stats.get('loaded_modules', 0)}")
            
            if stats['categories']:
                print(f"\nCategories:")
                for category, count in sorted(stats['categories'].items()):
                    print(f"  - {category}: {count} technique(s)")
            
            print(f"\nPerformance:")
            print(f"  Uptime: {perf_stats['system']['uptime_seconds']:.2f}s")
            print(f"  Tracked operations: {perf_stats['system']['tracked_operations']}")
            
            print(f"\nEvent System:")
            print(f"  Events emitted: {event_stats['events_emitted']}")
            print(f"  Active handlers: {event_stats['active_handlers']}")
        
        return 0
        
    except Exception as e:
        error_msg = f"Failed to get system info: {e}"
        if _emit_events:
            emit_error("command_error", error_msg, {"command": "sysinfo"})
        print(safe_output({"error": error_msg}, getattr(args, 'output', 'text')))
        return 1


def setup_global_args(args):
    """Setup global configuration from arguments"""
    global _electron_mode, _emit_events, _output_format
    
    _electron_mode = getattr(args, 'electron_mode', False)
    _emit_events = getattr(args, 'emit_events', False) or _electron_mode
    _output_format = getattr(args, 'output', 'text')
    
    # Configure logging for Electron integration
    if _electron_mode:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )


def main():
    """Enhanced main entry point with security and Electron integration"""
    parser = argparse.ArgumentParser(
        description="Domain Prompts System - Enhanced Biological Analysis Expert System",
        prog="python -m domain_prompts"
    )
    
    parser.add_argument(
        "--version", action="version",
        version=f"Domain Prompts System v{__version__}"
    )
    
    # Global options for Electron integration
    parser.add_argument(
        "--electron-mode", action="store_true",
        help="Enable Electron integration mode"
    )
    parser.add_argument(
        "--emit-events", action="store_true", 
        help="Emit events for real-time updates"
    )
    parser.add_argument(
        "--security-level", choices=["public", "internal", "restricted"],
        default="public", help="Set security level"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command with enhanced options
    list_parser = subparsers.add_parser("list", help="List available techniques")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument(
        "--output", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    list_parser.set_defaults(func=cmd_list)
    
    # Info command with enhanced formatting
    info_parser = subparsers.add_parser("info", help="Show technique information")
    info_parser.add_argument("technique", help="Technique name")
    info_parser.add_argument(
        "--format", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    info_parser.set_defaults(func=cmd_info)
    
    # Search command with enhanced output
    search_parser = subparsers.add_parser("search", help="Search techniques")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed information"
    )
    search_parser.add_argument(
        "--output", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    search_parser.set_defaults(func=cmd_search)
    
    # Validate command with enhanced reporting
    validate_parser = subparsers.add_parser("validate", help="Validate system")
    validate_parser.add_argument(
        "--export", help="Export validation results to file"
    )
    validate_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed validation results"
    )
    validate_parser.add_argument(
        "--output", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    validate_parser.set_defaults(func=cmd_validate)
    
    # Create command with enhanced validation
    create_parser = subparsers.add_parser("create", help="Create new technique")
    create_parser.add_argument("name", help="Technique name")
    create_parser.add_argument("--display-name", help="Display name")
    create_parser.add_argument("--description", help="Description")
    create_parser.add_argument(
        "--category", required=True, help="Category (required)"
    )
    create_parser.add_argument(
        "--output-dir", help="Output directory for the new module"
    )
    create_parser.add_argument(
        "--output", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    create_parser.set_defaults(func=cmd_create)
    
    # Export command with enhanced options
    export_parser = subparsers.add_parser("export", help="Export system data")
    export_parser.add_argument("output", help="Output file path")
    export_parser.add_argument(
        "--include-prompts", action="store_true",
        help="Include full prompt definitions"
    )
    export_parser.add_argument(
        "--include-performance", action="store_true",
        help="Include performance data"
    )
    export_parser.add_argument(
        "--output-format", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    export_parser.set_defaults(func=cmd_export)
    
    # Batch processing command
    batch_parser = subparsers.add_parser("batch", help="Process batch commands")
    batch_parser.add_argument("config_file", help="Batch configuration file")
    batch_parser.add_argument(
        "--output", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    batch_parser.set_defaults(func=cmd_batch_process)
    
    # Enhanced system info command
    sysinfo_parser = subparsers.add_parser("sysinfo", help="Show enhanced system information")
    sysinfo_parser.add_argument(
        "--output", choices=["text", "json", "electron"], default="text",
        help="Output format"
    )
    sysinfo_parser.set_defaults(func=cmd_system_info)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup global configuration
    setup_global_args(args)
    
    # Initialize system with enhanced configuration
    try:
        security_level = SecurityLevel(args.security_level.upper())
        init_result = initialize_system(
            enable_events=_emit_events,
            enable_performance_monitoring=True,
            security_level=security_level
        )
        
        if not init_result["initialization_success"]:
            error_msg = "System initialization had issues, some features may not work"
            if _emit_events:
                emit_error("initialization_warning", error_msg)
            print(f"⚠ {error_msg}")
            
    except Exception as e:
        error_msg = f"System initialization failed: {e}"
        if _emit_events:
            emit_error("initialization_error", error_msg)
        print(f"⚠ {error_msg}")
        print("Some features may not work properly")
    
    # Execute command with error handling
    try:
        if _emit_events:
            emit_system_event("cli_command_started", {
                "command": args.command,
                "args": vars(args),
                "electron_mode": _electron_mode
            })
        
        result_code = args.func(args)
        
        if _emit_events:
            emit_system_event("cli_command_completed", {
                "command": args.command,
                "exit_code": result_code,
                "success": result_code == 0
            })
        
        return result_code
        
    except KeyboardInterrupt:
        if _emit_events:
            emit_system_event("cli_command_cancelled", {"command": args.command})
        print("\n\nOperation cancelled by user")
        return 130
        
    except Exception as e:
        error_msg = f"Command failed: {e}"
        if _emit_events:
            emit_error("cli_command_error", error_msg, {
                "command": args.command,
                "args": vars(args)
            })
        print(f"✗ {error_msg}")
        
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        
        return 1


if __name__ == "__main__":
    sys.exit(main()) 