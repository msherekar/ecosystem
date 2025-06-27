"""
Configuration management for training data collection.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import os
import json

@dataclass
class TrainingConfig:
    """Configuration for training data collection"""
    
    # Data storage
    data_dir: str = "data/training"
    auto_save_interval: int = 10  # Save every N conversations
    max_file_size_mb: int = 100  # Max size per file
    
    # Privacy settings
    anonymize_data: bool = True
    collect_enabled: bool = True
    
    # Data retention
    max_age_days: int = 365  # Keep data for 1 year
    cleanup_enabled: bool = True
    
    # Export settings
    default_export_format: str = "jsonl"  # jsonl, chat, raw
    min_success_rate: float = 0.8
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        # Ensure data directory exists
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Validate export format
        valid_formats = ["jsonl", "chat", "raw"]
        if self.default_export_format not in valid_formats:
            raise ValueError(f"Export format must be one of {valid_formats}")
        
        # Validate success rate
        if not 0 <= self.min_success_rate <= 1:
            raise ValueError("Success rate must be between 0 and 1")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'TrainingConfig':
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> 'TrainingConfig':
        """Load configuration from environment variables"""
        return cls(
            data_dir=os.getenv("TRAINING_DATA_DIR", "data/training"),
            auto_save_interval=int(os.getenv("TRAINING_AUTO_SAVE_INTERVAL", "10")),
            max_file_size_mb=int(os.getenv("TRAINING_MAX_FILE_SIZE_MB", "100")),
            anonymize_data=os.getenv("TRAINING_ANONYMIZE_DATA", "true").lower() == "true",
            collect_enabled=os.getenv("TRAINING_COLLECT_ENABLED", "true").lower() == "true",
            max_age_days=int(os.getenv("TRAINING_MAX_AGE_DAYS", "365")),
            cleanup_enabled=os.getenv("TRAINING_CLEANUP_ENABLED", "true").lower() == "true",
            default_export_format=os.getenv("TRAINING_EXPORT_FORMAT", "jsonl"),
            min_success_rate=float(os.getenv("TRAINING_MIN_SUCCESS_RATE", "0.8")),
            log_level=os.getenv("TRAINING_LOG_LEVEL", "INFO"),
            log_file=os.getenv("TRAINING_LOG_FILE")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "data_dir": self.data_dir,
            "auto_save_interval": self.auto_save_interval,
            "max_file_size_mb": self.max_file_size_mb,
            "anonymize_data": self.anonymize_data,
            "collect_enabled": self.collect_enabled,
            "max_age_days": self.max_age_days,
            "cleanup_enabled": self.cleanup_enabled,
            "default_export_format": self.default_export_format,
            "min_success_rate": self.min_success_rate,
            "log_level": self.log_level,
            "log_file": self.log_file
        }
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to JSON file"""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def update(self, **kwargs) -> 'TrainingConfig':
        """Create a new config with updated values"""
        current_dict = self.to_dict()
        current_dict.update(kwargs)
        return TrainingConfig(**current_dict)

# Default configurations for different environments
DEV_CONFIG = TrainingConfig(
    data_dir="data/training/dev",
    auto_save_interval=5,
    collect_enabled=True,
    anonymize_data=False,  # Don't anonymize in dev
    log_level="DEBUG"
)

PROD_CONFIG = TrainingConfig(
    data_dir="data/training/prod",
    auto_save_interval=10,
    collect_enabled=True,
    anonymize_data=True,
    cleanup_enabled=True,
    log_level="INFO"
)

TEST_CONFIG = TrainingConfig(
    data_dir="data/training/test",
    auto_save_interval=1,
    collect_enabled=True,
    anonymize_data=False,
    max_age_days=1,  # Short retention for tests
    log_level="DEBUG"
)

def get_config(environment: str = "default") -> TrainingConfig:
    """Get configuration for specific environment"""
    configs = {
        "dev": DEV_CONFIG,
        "prod": PROD_CONFIG,
        "test": TEST_CONFIG,
        "default": TrainingConfig()
    }
    
    return configs.get(environment, TrainingConfig())

if __name__ == "__main__":
    # Example usage and validation
    print("Training Configuration Examples:")
    
    # Default config
    config = TrainingConfig()
    print(f"Default config: {config.to_dict()}")
    
    # From environment
    env_config = TrainingConfig.from_env()
    print(f"Environment config: {env_config.to_dict()}")
    
    # Different environments
    for env in ["dev", "prod", "test"]:
        env_config = get_config(env)
        print(f"{env.upper()} config: {env_config.data_dir}")
    
    # Save and load example
    config.save_to_file("example_config.json")
    loaded_config = TrainingConfig.from_file("example_config.json")
    print(f"Loaded config matches: {config.to_dict() == loaded_config.to_dict()}")
    
    # Clean up
    os.remove("example_config.json") 