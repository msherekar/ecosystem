"""
Test suite for training data collection system.
"""

__version__ = "1.0.0"

if __name__ == "__main__":
    import unittest
    import sys
    from pathlib import Path
    
    # Add parent directory to path for imports
    test_dir = Path(__file__).parent
    sys.path.insert(0, str(test_dir.parent))
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1) 