"""
Command-line interface for training data management.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import TrainingConfig, get_config
from .storage import TrainingDataStorage
from .exporters import TrainingDataExporter
from .collectors import create_collector

def setup_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Training Data Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s stats --data-dir data/training
  %(prog)s export --format jsonl --analysis-type scrna_seq
  %(prog)s cleanup --max-age 30
  %(prog)s config --environment prod
        """
    )
    
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
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show training data statistics")
    stats_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed statistics"
    )
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export training data")
    export_parser.add_argument(
        "--format",
        choices=["jsonl", "chat", "raw"],
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
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available datasets")
    list_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)"
    )
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show dataset information")
    info_parser.add_argument(
        "dataset",
        help="Dataset filename"
    )
    
    # Cleanup command
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
    
    # Merge command
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
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
    config_parser.add_argument(
        "--save",
        help="Save current config to file"
    )
    
    return parser

def load_config(args) -> TrainingConfig:
    """Load configuration based on arguments"""
    if args.config_file:
        return TrainingConfig.from_file(args.config_file)
    elif args.environment != "default":
        return get_config(args.environment)
    else:
        return TrainingConfig(data_dir=args.data_dir)

def print_table(headers, rows):
    """Print a simple table"""
    if not rows:
        print("No data to display")
        return
    
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print header
    header_row = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        print(" | ".join(f"{str(cell):<{w}}" for cell, w in zip(row, col_widths)))

async def cmd_stats(args, config: TrainingConfig):
    """Show training data statistics"""
    storage = TrainingDataStorage(config.data_dir, config)
    collector = create_collector(config.data_dir, config)
    
    if args.detailed:
        stats = collector.get_training_statistics()
        print(json.dumps(stats, indent=2, default=str))
    else:
        storage_stats = storage.get_storage_statistics()
        
        print("Training Data Statistics")
        print("=" * 40)
        print(f"Data Directory: {storage_stats.get('data_directory', 'N/A')}")
        print(f"Total Files: {storage_stats.get('total_files', 0)}")
        print(f"Total Size: {storage_stats.get('total_size_mb', 0):.2f} MB")
        print(f"Average File Size: {storage_stats.get('average_file_size_mb', 0):.2f} MB")
        
        if storage_stats.get('oldest_file'):
            oldest = datetime.fromtimestamp(storage_stats['oldest_file'])
            print(f"Oldest File: {oldest.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if storage_stats.get('newest_file'):
            newest = datetime.fromtimestamp(storage_stats['newest_file'])
            print(f"Newest File: {newest.strftime('%Y-%m-%d %H:%M:%S')}")

async def cmd_export(args, config: TrainingConfig):
    """Export training data"""
    storage = TrainingDataStorage(config.data_dir, config)
    exporter = TrainingDataExporter(storage, config)
    
    print(f"Exporting training data in {args.format} format...")
    
    output_file = exporter.export_for_training(
        output_format=args.format,
        filter_analysis_type=args.analysis_type,
        min_success_rate=args.min_success_rate,
        output_filename=args.output
    )
    
    if output_file:
        print(f"Exported to: {output_file}")
        
        # Show export statistics
        stats = exporter.export_statistics()
        print(f"Total conversations: {stats.get('total_conversations', 0)}")
        print(f"Success rate: {stats.get('success_rate', 0):.2%}")
    else:
        print("Export failed or no data to export")

async def cmd_list(args, config: TrainingConfig):
    """List available datasets"""
    storage = TrainingDataStorage(config.data_dir, config)
    datasets = storage.list_datasets()
    
    if args.format == "json":
        print(json.dumps(datasets, indent=2, default=str))
    else:
        headers = ["Filename", "Size (MB)", "Modified"]
        rows = []
        
        for dataset in datasets:
            rows.append([
                dataset['filename'],
                f"{dataset['size_mb']:.2f}",
                dataset['modified'].strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        print_table(headers, rows)

async def cmd_info(args, config: TrainingConfig):
    """Show dataset information"""
    storage = TrainingDataStorage(config.data_dir, config)
    
    dataset_path = Path(config.data_dir) / args.dataset
    if not dataset_path.exists():
        print(f"Dataset not found: {args.dataset}")
        return
    
    info = storage.get_dataset_info(str(dataset_path))
    
    if not info:
        print("Failed to get dataset information")
        return
    
    print(f"Dataset: {info['filename']}")
    print("=" * 40)
    print(f"Total Conversations: {info['total_conversations']}")
    print(f"Success Rate: {info['success_rate']:.2%}")
    print(f"Created: {info['created_at']}")
    print(f"Version: {info['version']}")
    
    if info['date_range']['earliest']:
        print(f"Date Range: {info['date_range']['earliest']} to {info['date_range']['latest']}")
    
    print("\nAnalysis Types:")
    for analysis_type, count in info['analysis_types'].items():
        print(f"  {analysis_type}: {count}")
    
    print("\nPipeline Steps:")
    for step, count in info['pipeline_steps'].items():
        print(f"  {step}: {count}")

async def cmd_cleanup(args, config: TrainingConfig):
    """Clean up old data"""
    storage = TrainingDataStorage(config.data_dir, config)
    
    if args.dry_run:
        print(f"Would clean up files older than {args.max_age} days")
        # TODO: Implement dry run functionality
        print("Dry run not yet implemented")
    else:
        removed_count = storage.cleanup_old_files(args.max_age)
        print(f"Removed {removed_count} old files")

async def cmd_merge(args, config: TrainingConfig):
    """Merge datasets"""
    storage = TrainingDataStorage(config.data_dir, config)
    
    # Validate input files
    dataset_paths = []
    for dataset in args.datasets:
        path = Path(config.data_dir) / dataset
        if not path.exists():
            print(f"Dataset not found: {dataset}")
            return
        dataset_paths.append(str(path))
    
    print(f"Merging {len(dataset_paths)} datasets...")
    
    try:
        output_file = storage.merge_datasets(dataset_paths, args.output)
        print(f"Merged datasets saved to: {output_file}")
    except Exception as e:
        print(f"Failed to merge datasets: {e}")

async def cmd_config(args, config: TrainingConfig):
    """Show configuration"""
    config_dict = config.to_dict()
    
    print("Current Configuration:")
    print("=" * 40)
    print(json.dumps(config_dict, indent=2))
    
    if args.save:
        config.save_to_file(args.save)
        print(f"\nConfiguration saved to: {args.save}")

async def main():
    """Main CLI entry point"""
    parser = setup_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        config = load_config(args)
        
        if args.verbose:
            print(f"Using data directory: {config.data_dir}")
            print(f"Command: {args.command}")
        
        # Dispatch to command handlers
        if args.command == "stats":
            await cmd_stats(args, config)
        elif args.command == "export":
            await cmd_export(args, config)
        elif args.command == "list":
            await cmd_list(args, config)
        elif args.command == "info":
            await cmd_info(args, config)
        elif args.command == "cleanup":
            await cmd_cleanup(args, config)
        elif args.command == "merge":
            await cmd_merge(args, config)
        elif args.command == "config":
            await cmd_config(args, config)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 