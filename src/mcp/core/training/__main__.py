"""
Main entry point for the training data collection system.
Run with: python -m src.mcp.core.training
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import TrainingConfig
from utils import main as utils_main

def main():
    """Main entry point for training system"""
    print("MCP Training Data Collection System")
    print("=" * 40)
    print("Version: 1.0.0")
    print()
    print("Available modules:")
    print("  - Conversation Collection")
    print("  - Data Storage")
    print("  - Export System")
    print("  - Configuration Management")
    print("  - Data Validation")
    print("  - Security & Privacy")
    print()
    print("To use the system:")
    print("  from src.mcp.core.training import create_training_system")
    print("  system = create_training_system()")
    print()
    
    # Test basic functionality
    try:
        print("Testing basic functionality...")
        config = TrainingConfig()
        print(f"✓ Configuration loaded: {config.data_dir}")
        
        # Run utils tests
        print("\nRunning utility tests...")
        utils_main()
        
        print("\n✓ Training system is ready!")
        
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())