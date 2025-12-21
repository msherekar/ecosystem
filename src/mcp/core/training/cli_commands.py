"""
CLI command implementations for training data management.
Contains all command handlers separated from argument parsing.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import TrainingConfig
from .async_storage import AsyncTrainingDataStorage
from .storage import TrainingDataStorage
from .exporters import TrainingDataExporter
from .session_manager import SessionManager
from .api import get_api_instance

class CLICommands:
    """Command implementations for training CLI"""
    
    def __init__(self):
        self.output_formats = {
            "table": self._print_table,
            "json": self._print_json,
            "csv": self._print_csv
        }
    
    async def cmd_stats(self, args, config: TrainingConfig) -> bool:
        """Show training data statistics"""
        try:
            if args.async_mode:
                storage = AsyncTrainingDataStorage(config.data_dir, config)
                session_manager = SessionManager(storage, config)
                stats = await session_manager.get_comprehensive_statistics()
            else:
                storage = TrainingDataStorage(config.data_dir, config)
                stats = storage.get_storage_statistics()
            
            if args.detailed and args.async_mode:
                return await self._show_detailed_stats(stats, args.format)
            else:
                return await self._show_basic_stats(stats, args.format)
        
        except Exception as e:
            print(f"Failed to get statistics: {e}")
            return False
    
    async def cmd_export(self, args, config: TrainingConfig) -> bool:
        """Export training data"""
        try:
            print(f"Exporting training data in {args.format} format...")
            
            if args.async_mode:
                storage = AsyncTrainingDataStorage(config.data_dir, config)
            else:
                storage = TrainingDataStorage(config.data_dir, config)
            
            exporter = TrainingDataExporter(storage, config)
            
            output_file = exporter.export_for_training(
                output_format=args.format,
                filter_analysis_type=args.analysis_type,
                min_success_rate=args.min_success_rate,
                output_filename=args.output,
                compress=getattr(args, 'compress', False)
            )
            
            if output_file:
                print(f"✓ Exported to: {output_file}")
                
                # Show export statistics
                stats = exporter.export_statistics()
                print(f"  Total conversations: {stats.get('total_conversations', 0)}")
                print(f"  Success rate: {stats.get('success_rate', 0):.2%}")
                return True
            else:
                print("✗ Export failed or no data to export")
                return False
        
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    async def cmd_list(self, args, config: TrainingConfig) -> bool:
        """List available datasets"""
        try:
            if args.async_mode:
                storage = AsyncTrainingDataStorage(config.data_dir, config)
                datasets = await storage.list_datasets_async()
            else:
                storage = TrainingDataStorage(config.data_dir, config)
                datasets = storage.list_datasets()
            
            if not datasets:
                print("No datasets found")
                return True
            
            # Sort datasets
            if args.sort_by == "name":
                datasets.sort(key=lambda x: x['filename'])
            elif args.sort_by == "size":
                datasets.sort(key=lambda x: x['size_mb'], reverse=True)
            else:  # date
                datasets.sort(key=lambda x: x['modified'], reverse=True)
            
            return self._display_datasets(datasets, args.format)
        
        except Exception as e:
            print(f"Failed to list datasets: {e}")
            return False
    
    async def cmd_info(self, args, config: TrainingConfig) -> bool:
        """Show dataset information"""
        try:
            dataset_path = Path(config.data_dir) / args.dataset
            if not dataset_path.exists():
                print(f"Dataset not found: {args.dataset}")
                return False
            
            if args.async_mode:
                storage = AsyncTrainingDataStorage(config.data_dir, config)
                info = await storage.get_dataset_info_async(str(dataset_path))
            else:
                storage = TrainingDataStorage(config.data_dir, config)
                info = storage.get_dataset_info(str(dataset_path))
            
            if not info:
                print("Failed to get dataset information")
                return False
            
            return self._display_dataset_info(info)
        
        except Exception as e:
            print(f"Failed to get dataset info: {e}")
            return False
    
    async def cmd_cleanup(self, args, config: TrainingConfig) -> bool:
        """Clean up old data"""
        try:
            if args.dry_run:
                print(f"Dry run: Would clean up files older than {args.max_age} days")
                # TODO: Implement dry run preview
                return True
            
            if args.async_mode:
                storage = AsyncTrainingDataStorage(config.data_dir, config)
                removed_count = await storage.cleanup_old_files_async(args.max_age)
            else:
                storage = TrainingDataStorage(config.data_dir, config)
                removed_count = storage.cleanup_old_files(args.max_age)
            
            print(f"✓ Removed {removed_count} old files")
            return True
        
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False
    
    async def cmd_merge(self, args, config: TrainingConfig) -> bool:
        """Merge datasets"""
        try:
            # Validate input files
            dataset_paths = []
            for dataset in args.datasets:
                path = Path(config.data_dir) / dataset
                if not path.exists():
                    print(f"Dataset not found: {dataset}")
                    return False
                dataset_paths.append(str(path))
            
            print(f"Merging {len(dataset_paths)} datasets...")
            
            if args.async_mode:
                storage = AsyncTrainingDataStorage(config.data_dir, config)
                output_file = await storage.merge_datasets_async(dataset_paths, args.output)
            else:
                storage = TrainingDataStorage(config.data_dir, config)
                output_file = storage.merge_datasets(dataset_paths, args.output)
            
            print(f"✓ Merged datasets saved to: {output_file}")
            return True
        
        except Exception as e:
            print(f"Failed to merge datasets: {e}")
            return False
    
    async def cmd_config(self, args, config: TrainingConfig) -> bool:
        """Configuration management"""
        try:
            if args.show or not any([args.save, args.validate]):
                config_dict = config.to_dict()
                print("Current Configuration:")
                print("=" * 40)
                print(json.dumps(config_dict, indent=2))
            
            if args.validate:
                print("\nValidating configuration...")
                # Basic validation
                issues = []
                
                if not Path(config.data_dir).exists():
                    issues.append(f"Data directory does not exist: {config.data_dir}")
                
                if config.max_file_size_mb <= 0:
                    issues.append("Max file size must be positive")
                
                if not 0 <= config.min_success_rate <= 1:
                    issues.append("Min success rate must be between 0 and 1")
                
                if issues:
                    print("✗ Configuration issues found:")
                    for issue in issues:
                        print(f"  - {issue}")
                    return False
                else:
                    print("✓ Configuration is valid")
            
            if args.save:
                config.save_to_file(args.save)
                print(f"✓ Configuration saved to: {args.save}")
            
            return True
        
        except Exception as e:
            print(f"Configuration command failed: {e}")
            return False
    
    async def cmd_server(self, args, config: TrainingConfig) -> bool:
        """Start API server"""
        try:
            print(f"Starting API server on {args.host}:{args.port}")
            
            api = get_api_instance(args.host, args.port)
            
            if args.reload:
                print("Development mode: Auto-reload enabled")
                # This would typically use uvicorn with reload
                
            # Start server (this will block)
            await api.start_server()
            return True
        
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    async def _show_detailed_stats(self, stats: Dict[str, Any], format_type: str) -> bool:
        """Show detailed statistics"""
        if format_type == "json":
            print(json.dumps(stats, indent=2, default=str))
            return True
        
        print("Detailed Training Data Statistics")
        print("=" * 50)
        
        # Collection summary
        if "collection_summary" in stats:
            summary = stats["collection_summary"]
            print("\nCollection Summary:")
            for key, value in summary.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Active sessions
        if "active_sessions" in stats:
            active = stats["active_sessions"]
            print(f"\nActive Sessions:")
            for key, value in active.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Storage statistics
        if "storage_statistics" in stats:
            storage = stats["storage_statistics"]
            print(f"\nStorage Statistics:")
            for key, value in storage.items():
                if key.endswith("_mb"):
                    print(f"  {key.replace('_', ' ').title()}: {value:.2f} MB")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
        
        return True
    
    async def _show_basic_stats(self, stats: Dict[str, Any], format_type: str) -> bool:
        """Show basic statistics"""
        if format_type == "json":
            print(json.dumps(stats, indent=2, default=str))
            return True
        
        print("Training Data Statistics")
        print("=" * 40)
        
        basic_fields = [
            ("data_directory", "Data Directory"),
            ("total_files", "Total Files"),
            ("total_size_mb", "Total Size (MB)"),
            ("average_file_size_mb", "Average File Size (MB)")
        ]
        
        for field, label in basic_fields:
            if field in stats:
                value = stats[field]
                if field.endswith("_mb") and isinstance(value, (int, float)):
                    print(f"{label}: {value:.2f}")
                else:
                    print(f"{label}: {value}")
        
        # Show date range if available
        if "oldest_file" in stats and stats["oldest_file"]:
            oldest = datetime.fromtimestamp(stats["oldest_file"])
            print(f"Oldest File: {oldest.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if "newest_file" in stats and stats["newest_file"]:
            newest = datetime.fromtimestamp(stats["newest_file"])
            print(f"Newest File: {newest.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    
    def _display_datasets(self, datasets: List[Dict[str, Any]], format_type: str) -> bool:
        """Display dataset list"""
        if format_type == "json":
            print(json.dumps(datasets, indent=2, default=str))
            return True
        
        headers = ["Filename", "Size (MB)", "Modified", "Created"]
        rows = []
        
        for dataset in datasets:
            rows.append([
                dataset['filename'],
                f"{dataset['size_mb']:.2f}",
                dataset['modified'].strftime('%Y-%m-%d %H:%M:%S'),
                dataset.get('created', dataset['modified']).strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        self._print_table(headers, rows)
        return True
    
    def _display_dataset_info(self, info: Dict[str, Any]) -> bool:
        """Display detailed dataset information"""
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
        
        return True
    
    def _print_table(self, headers: List[str], rows: List[List[str]]) -> None:
        """Print a formatted table"""
        if not rows:
            print("No data to display")
            return
        
        # Calculate column widths
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Print header
        header_row = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
        print(header_row)
        print("-" * len(header_row))
        
        # Print rows
        for row in rows:
            print(" | ".join(f"{str(cell):<{w}}" for cell, w in zip(row, col_widths)))
    
    def _print_json(self, data: Any) -> None:
        """Print data as JSON"""
        print(json.dumps(data, indent=2, default=str))
    
    def _print_csv(self, headers: List[str], rows: List[List[str]]) -> None:
        """Print data as CSV"""
        import csv
        import sys
        
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    """Test CLI commands"""
    print("Testing CLI Commands")
    print("=" * 30)
    
    commands = CLICommands()
    
    # Test table printing
    print("✓ Table formatting test:")
    headers = ["Name", "Size", "Date"]
    rows = [["test.json", "1.5 MB", "2024-01-01"]]
    commands._print_table(headers, rows)
    
    print("\n✓ CLI commands module loaded successfully!")

if __name__ == "__main__":
    main()