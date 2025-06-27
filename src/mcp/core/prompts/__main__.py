"""
Domain Prompts System - Command Line Interface

This module provides a command-line interface for managing and using
the domain prompts system.

Usage:
    python -m domain_prompts --help
    python -m domain_prompts list
    python -m domain_prompts info scrnaseq
    python -m domain_prompts validate
    python -m domain_prompts create "New Technique" --category "Genomics"
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any

from . import (
    initialize_system, get_system_info, validate_system,
    list_techniques, get_expert, search_techniques,
    create_new_technique, export_system_data,
    get_techniques_by_category, __version__
)


def format_expert_info(expert) -> str:
    """Format expert information for display"""
    metadata = expert.get_metadata()
    prompts = expert.get_prompts()
    
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
    return info


def cmd_list(args) -> int:
    """List all available techniques"""
    techniques = list_techniques()
    
    if not techniques:
        print("No techniques available. Try running initialization first.")
        return 1
    
    if args.category:
        category_techniques = get_techniques_by_category(args.category)
        print(f"Techniques in category '{args.category}':")
        for technique in category_techniques:
            print(f"  - {technique}")
    else:
        print(f"Available techniques ({len(techniques)}):")
        for technique in sorted(techniques):
            expert = get_expert(technique)
            if expert:
                metadata = expert.get_metadata()
                print(f"  - {technique}: {metadata.display_name} ({metadata.category})")
            else:
                print(f"  - {technique}: (metadata unavailable)")
    
    return 0


def cmd_info(args) -> int:
    """Show detailed information about a technique"""
    expert = get_expert(args.technique)
    
    if not expert:
        print(f"Technique '{args.technique}' not found.")
        print("Available techniques:")
        for technique in sorted(list_techniques()):
            print(f"  - {technique}")
        return 1
    
    print(format_expert_info(expert))
    
    # Show validation status
    errors = expert.validate_prompts()
    if errors:
        print("\nValidation Issues:")
        for error in errors:
            print(f"  ⚠ {error}")
    else:
        print("\n✓ All prompts validated successfully")
    
    return 0


def cmd_search(args) -> int:
    """Search for techniques"""
    experts = search_techniques(args.query)
    
    if not experts:
        print(f"No techniques found matching '{args.query}'")
        return 1
    
    print(f"Techniques matching '{args.query}' ({len(experts)}):")
    for expert in experts:
        metadata = expert.get_metadata()
        print(f"  - {metadata.name}: {metadata.display_name}")
        if args.verbose:
            print(f"    Category: {metadata.category}")
            print(f"    Description: {metadata.description}")
    
    return 0


def cmd_validate(args) -> int:
    """Validate the system"""
    print("Validating domain prompts system...")
    
    validation_results = validate_system()
    
    print(f"\nValidation Results:")
    print(f"  Total experts: {validation_results['total_experts']}")
    print(f"  Experts with errors: {validation_results['experts_with_errors']}")
    print(f"  Total errors: {validation_results['total_errors']}")
    print(f"  System healthy: {'✓ Yes' if validation_results['system_healthy'] else '✗ No'}")
    
    if validation_results['total_errors'] > 0:
        print(f"\nDetailed Error Report:")
        for expert_name, errors in validation_results['validation_results'].items():
            if errors:
                print(f"\n{expert_name}:")
                for error in errors:
                    print(f"  ✗ {error}")
    
    if args.export:
        export_path = Path(args.export)
        validation_data = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "validation_results": validation_results
        }
        
        with open(export_path, 'w') as f:
            json.dump(validation_data, f, indent=2)
        
        print(f"\nValidation results exported to: {export_path}")
    
    return 0 if validation_results['system_healthy'] else 1


def cmd_create(args) -> int:
    """Create a new technique"""
    try:
        output_path = create_new_technique(
            technique_name=args.name,
            display_name=args.display_name or args.name,
            description=args.description or f"Analysis technique for {args.name}",
            category=args.category,
            output_dir=Path(args.output_dir) if args.output_dir else None
        )
        
        print(f"✓ Created new technique module: {output_path}")
        print(f"  Edit the file to add custom prompts and metadata.")
        print(f"  Run 'python -m domain_prompts validate' to check for issues.")
        
        return 0
        
    except Exception as e:
        print(f"✗ Failed to create technique: {e}")
        return 1


def cmd_export(args) -> int:
    """Export system data"""
    try:
        output_path = Path(args.output)
        export_system_data(output_path, include_prompts=args.include_prompts)
        
        print(f"✓ System data exported to: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Failed to export data: {e}")
        return 1


def cmd_system_info(args) -> int:
    """Show system information"""
    info = get_system_info()
    
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
    
    if stats['expertise_levels']:
        print(f"\nExpertise Levels:")
        for level, count in sorted(stats['expertise_levels'].items()):
            print(f"  - {level}: {count} technique(s)")
    
    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Domain Prompts System - Biological Analysis Expert System",
        prog="python -m domain_prompts"
    )
    
    parser.add_argument(
        "--version", action="version",
        version=f"Domain Prompts System v{__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available techniques")
    list_parser.add_argument(
        "--category", help="Filter by category"
    )
    list_parser.set_defaults(func=cmd_list)
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show technique information")
    info_parser.add_argument("technique", help="Technique name")
    info_parser.set_defaults(func=cmd_info)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search techniques")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed information"
    )
    search_parser.set_defaults(func=cmd_search)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate system")
    validate_parser.add_argument(
        "--export", help="Export validation results to file"
    )
    validate_parser.set_defaults(func=cmd_validate)
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create new technique")
    create_parser.add_argument("name", help="Technique name")
    create_parser.add_argument("--display-name", help="Display name")
    create_parser.add_argument("--description", help="Description")
    create_parser.add_argument(
        "--category", required=True,
        help="Category (required)"
    )
    create_parser.add_argument(
        "--output-dir", help="Output directory for the new module"
    )
    create_parser.set_defaults(func=cmd_create)
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export system data")
    export_parser.add_argument("output", help="Output file path")
    export_parser.add_argument(
        "--include-prompts", action="store_true",
        help="Include full prompt definitions"
    )
    export_parser.set_defaults(func=cmd_export)
    
    # System info command
    sysinfo_parser = subparsers.add_parser("sysinfo", help="Show system information")
    sysinfo_parser.set_defaults(func=cmd_system_info)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize system
    try:
        init_result = initialize_system()
        if not init_result["initialization_success"]:
            print("⚠ System initialization had issues, some features may not work")
    except Exception as e:
        print(f"⚠ System initialization failed: {e}")
        print("Some features may not work properly")
    
    # Execute command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"✗ Command failed: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 