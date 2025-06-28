"""
Core CLI functionality for training data management.
Handles argument parsing and command dispatch.
"""

import argparse
import asyncio
import sys
from typing import Dict, Any, Callable

from .config import TrainingConfig, get_config
from .cli_commands import CLICommands

class TrainingCLI:
    """Main CLI application for training data management"""
    
    def __init__(self):
        self.commands = CLICommands()
        self.parser = self._setup_parser()
    
    def _setup_parser(self) -> argparse.ArgumentParser:
        """Set up command-line argument parser"""
        parser = argparse.ArgumentParser(
            description="Training Data Management CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s stats --data-dir data/training --detailed
  %(prog)s export --format jsonl --analysis-type scrna_seq
  %(prog)s cleanup --max-age 30 --dry-run
  %(prog)s config --environment prod --save config.json
  %(prog)s server --port 8000 --host localhost
            """
        )
        
        # Global options
        parser.add_argument(
            "--data-dir", 
            default="data/training",
            help="Training data directory (default: data/training)"
        )
        
        parser.add_argument(
            "--config-file",
            help="Configuration file path"
        )
        
        parser.add_argument(
            "--environment",
            choices=["dev", "prod", "test", "default"],
            default="default",
            help="Configuration environment (default: default)"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Verbose output"
        )
        
        parser.add_argument(
            "--async-mode",
            action="store_true",
            help="Use async operations for better performance"
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        self._add_stats_command(subparsers)
        self._add_export_command(subparsers)
        self._add_list_command(subparsers)
        self._add_info_command(subparsers)
        self._add_cleanup_command(subparsers)
        self._add_merge_command(subparsers)
        self._add_config_command(subparsers)
        self._add_server_command(subparsers)
        
        return parser
    
    def _add_stats_command(self, subparsers):
        """Add stats command"""
        stats_parser = subparsers.add_parser("stats", help="Show training data statistics")
        stats_parser.add_argument(
            "--detailed",
            action="store_true",
            help="Show detailed statistics"
        )
        stats_parser.add_argument(
            "--format",
            choices=["table", "json", "csv"],
            default="table",
            help="Output format"
        )
    
    def _add_export_command(self, subparsers):
        """Add export command"""
        export_parser = subparsers.add_parser("export", help="Export training data")
        export_parser.add_argument(
            "--format",
            choices=["jsonl", "chat", "raw", "huggingface"],
            default="jsonl",
            help="Export format (default: jsonl)"
        )
        export_parser.add_argument(
            "--analysis-type",
            help="Filter by analysis type"
        )
        export_parser.add_argument(
            "--min-success-rate",
            type=float,
            default=0.8,
            help="Minimum success rate filter (default: 0.8)"
        )
        export_parser.add_argument(
            "--output",
            help="Output filename (auto-generated if not specified)"
        )
        export_parser.add_argument(
            "--compress",
            action="store_true",
            help="Compress output file"
        )
    
    def _add_list_command(self, subparsers):
        """Add list command"""
        list_parser = subparsers.add_parser("list", help="List available datasets")
        list_parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="Output format (default: table)"
        )
        list_parser.add_argument(
            "--sort-by",
            choices=["name", "size", "date"],
            default="date",
            help="Sort criteria"
        )
    
    def _add_info_command(self, subparsers):
        """Add info command"""
        info_parser = subparsers.add_parser("info", help="Show dataset information")
        info_parser.add_argument(
            "dataset",
            help="Dataset filename or path"
        )
    
    def _add_cleanup_command(self, subparsers):
        """Add cleanup command"""
        cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
        cleanup_parser.add_argument(
            "--max-age",
            type=int,
            default=365,
            help="Maximum age in days (default: 365)"
        )
        cleanup_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting"
        )
    
    def _add_merge_command(self, subparsers):
        """Add merge command"""
        merge_parser = subparsers.add_parser("merge", help="Merge datasets")
        merge_parser.add_argument(
            "datasets",
            nargs="+",
            help="Dataset files to merge"
        )
        merge_parser.add_argument(
            "--output",
            help="Output filename"
        )
    
    def _add_config_command(self, subparsers):
        """Add config command"""
        config_parser = subparsers.add_parser("config", help="Configuration management")
        config_parser.add_argument(
            "--show",
            action="store_true",
            help="Show current configuration"
        )
        config_parser.add_argument(
            "--save",
            help="Save current config to file"
        )
        config_parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate configuration"
        )
    
    def _add_server_command(self, subparsers):
        """Add server command"""
        server_parser = subparsers.add_parser("server", help="Start API server")
        server_parser.add_argument(
            "--host",
            default="localhost",
            help="Host to bind to (default: localhost)"
        )
        server_parser.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Port to bind to (default: 8000)"
        )
        server_parser.add_argument(
            "--reload",
            action="store_true",
            help="Enable auto-reload for development"
        )
    
    def load_config(self, args) -> TrainingConfig:
        """Load configuration based on arguments"""
        if args.config_file:
            return TrainingConfig.from_file(args.config_file)
        elif args.environment != "default":
            return get_config(args.environment)
        else:
            config = TrainingConfig(data_dir=args.data_dir)
            # Override with any command-line flags
            if hasattr(args, 'async_mode') and args.async_mode:
                config = config.update(use_async=True)
            return config
    
    async def run_async(self) -> int:
        """Run CLI with async support"""
        args = self.parser.parse_args()
        
        if not args.command:
            self.parser.print_help()
            return 0
        
        try:
            config = self.load_config(args)
            
            if args.verbose:
                print(f"Using data directory: {config.data_dir}")
                print(f"Command: {args.command}")
                print(f"Environment: {args.environment}")
            
            # Dispatch to command handlers
            command_method = getattr(self.commands, f"cmd_{args.command}", None)
            if not command_method:
                print(f"Unknown command: {args.command}")
                self.parser.print_help()
                return 1
            
            # Execute command
            result = await command_method(args, config)
            return 0 if result else 1
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return 130
        except Exception as e:
            print(f"Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def run(self) -> int:
        """Run CLI (blocking)"""
        return asyncio.run(self.run_async())




def main():
    """Test CLI setup"""
    print("Testing Training CLI")
    print("=" * 30)
    
    cli = TrainingCLI()
    
    # Test parser setup
    print(f"✓ Parser created with {len(cli.parser._subparsers._group_actions[0].choices)} commands")
    
    # Test help
    try:
        cli.parser.parse_args(["--help"])
    except SystemExit:
        print("✓ Help system working")
    
    # Test command parsing
    args = cli.parser.parse_args(["stats", "--detailed"])
    print(f"✓ Command parsing: {args.command}")
    
    # Test config loading
    config = cli.load_config(args)
    print(f"✓ Config loading: {config.data_dir}")
    
    print("✓ CLI core tests completed!")
    
if __name__ == "__main__":
    main()