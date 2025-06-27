"""
Techniques Package

This package contains individual domain expert modules for different biological techniques.
Each technique gets its own module for better organization and scalability.
"""

# Automatically import all technique modules when package is imported
from pathlib import Path
import importlib
import logging

logger = logging.getLogger(__name__)

def load_all_techniques():
    """Load all technique modules in this package"""
    techniques_dir = Path(__file__).parent
    loaded_count = 0
    
    for module_file in techniques_dir.glob("*.py"):
        if module_file.name.startswith("_"):
            continue
            
        module_name = module_file.stem
        try:
            importlib.import_module(f".{module_name}", package=__name__)
            loaded_count += 1
            logger.debug(f"Loaded technique module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load technique module {module_name}: {e}")
    
    return loaded_count

# Auto-load all techniques when package is imported
load_all_techniques() 