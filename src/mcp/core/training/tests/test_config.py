"""
Tests for training configuration.
"""

import unittest
import os
import json
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TrainingConfig, get_config, DEV_CONFIG, PROD_CONFIG, TEST_CONFIG

class TestTrainingConfig(unittest.TestCase):
    """Test TrainingConfig class"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = TrainingConfig()
        
        self.assertEqual(config.data_dir, "data/training")
        self.assertEqual(config.auto_save_interval, 10)
        self.assertEqual(config.max_file_size_mb, 100)
        self.assertTrue(config.anonymize_data)
        self.assertTrue(config.collect_enabled)
        self.assertEqual(config.max_age_days, 365)
        self.assertTrue(config.cleanup_enabled)
        self.assertEqual(config.default_export_format, "jsonl")
        self.assertEqual(config.min_success_rate, 0.8)
        self.assertEqual(config.log_level, "INFO")
        self.assertIsNone(config.log_file)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = TrainingConfig(
            data_dir="custom/path",
            auto_save_interval=5,
            anonymize_data=False,
            default_export_format="chat",
            min_success_rate=0.9
        )
        
        self.assertEqual(config.data_dir, "custom/path")
        self.assertEqual(config.auto_save_interval, 5)
        self.assertFalse(config.anonymize_data)
        self.assertEqual(config.default_export_format, "chat")
        self.assertEqual(config.min_success_rate, 0.9)
    
    def test_post_init_validation(self):
        """Test post-initialization validation"""
        # Test invalid export format
        with self.assertRaises(ValueError):
            TrainingConfig(default_export_format="invalid")
        
        # Test invalid success rate
        with self.assertRaises(ValueError):
            TrainingConfig(min_success_rate=1.5)
        
        with self.assertRaises(ValueError):
            TrainingConfig(min_success_rate=-0.1)
    
    def test_data_directory_creation(self):
        """Test that data directory is created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test_data")
            config = TrainingConfig(data_dir=test_path)
            
            self.assertTrue(os.path.exists(test_path))
            self.assertTrue(os.path.isdir(test_path))
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        config = TrainingConfig()
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict["data_dir"], "data/training")
        self.assertEqual(config_dict["auto_save_interval"], 10)
        self.assertTrue(config_dict["anonymize_data"])
        self.assertEqual(config_dict["default_export_format"], "jsonl")
    
    def test_save_and_load_file(self):
        """Test saving and loading configuration from file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            config = TrainingConfig(
                data_dir="test/path",
                auto_save_interval=15,
                anonymize_data=False
            )
            
            # Save to file
            config.save_to_file(temp_file.name)
            
            # Load from file
            loaded_config = TrainingConfig.from_file(temp_file.name)
            
            self.assertEqual(loaded_config.data_dir, "test/path")
            self.assertEqual(loaded_config.auto_save_interval, 15)
            self.assertFalse(loaded_config.anonymize_data)
            
            # Clean up
            os.unlink(temp_file.name)
    
    def test_from_env(self):
        """Test loading configuration from environment variables"""
        # Set environment variables
        env_vars = {
            "TRAINING_DATA_DIR": "env/data",
            "TRAINING_AUTO_SAVE_INTERVAL": "20",
            "TRAINING_ANONYMIZE_DATA": "false",
            "TRAINING_EXPORT_FORMAT": "chat",
            "TRAINING_MIN_SUCCESS_RATE": "0.9"
        }
        
        # Store original values
        original_values = {}
        for key in env_vars:
            original_values[key] = os.environ.get(key)
            os.environ[key] = env_vars[key]
        
        try:
            config = TrainingConfig.from_env()
            
            self.assertEqual(config.data_dir, "env/data")
            self.assertEqual(config.auto_save_interval, 20)
            self.assertFalse(config.anonymize_data)
            self.assertEqual(config.default_export_format, "chat")
            self.assertEqual(config.min_success_rate, 0.9)
        
        finally:
            # Restore original values
            for key, value in original_values.items():
                if value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = value
    
    def test_update(self):
        """Test configuration update"""
        config = TrainingConfig()
        original_data_dir = config.data_dir
        
        updated_config = config.update(
            data_dir="updated/path",
            auto_save_interval=25
        )
        
        # Original config should be unchanged
        self.assertEqual(config.data_dir, original_data_dir)
        
        # New config should have updated values
        self.assertEqual(updated_config.data_dir, "updated/path")
        self.assertEqual(updated_config.auto_save_interval, 25)
        # Other values should remain the same
        self.assertEqual(updated_config.max_file_size_mb, config.max_file_size_mb)

class TestPredefinedConfigs(unittest.TestCase):
    """Test predefined configuration instances"""
    
    def test_dev_config(self):
        """Test development configuration"""
        self.assertEqual(DEV_CONFIG.data_dir, "data/training/dev")
        self.assertEqual(DEV_CONFIG.auto_save_interval, 5)
        self.assertFalse(DEV_CONFIG.anonymize_data)
        self.assertEqual(DEV_CONFIG.log_level, "DEBUG")
    
    def test_prod_config(self):
        """Test production configuration"""
        self.assertEqual(PROD_CONFIG.data_dir, "data/training/prod")
        self.assertEqual(PROD_CONFIG.auto_save_interval, 10)
        self.assertTrue(PROD_CONFIG.anonymize_data)
        self.assertTrue(PROD_CONFIG.cleanup_enabled)
        self.assertEqual(PROD_CONFIG.log_level, "INFO")
    
    def test_test_config(self):
        """Test testing configuration"""
        self.assertEqual(TEST_CONFIG.data_dir, "data/training/test")
        self.assertEqual(TEST_CONFIG.auto_save_interval, 1)
        self.assertFalse(TEST_CONFIG.anonymize_data)
        self.assertEqual(TEST_CONFIG.max_age_days, 1)
        self.assertEqual(TEST_CONFIG.log_level, "DEBUG")
    
    def test_get_config(self):
        """Test get_config function"""
        dev_config = get_config("dev")
        self.assertEqual(dev_config.data_dir, DEV_CONFIG.data_dir)
        
        prod_config = get_config("prod")
        self.assertEqual(prod_config.data_dir, PROD_CONFIG.data_dir)
        
        test_config = get_config("test")
        self.assertEqual(test_config.data_dir, TEST_CONFIG.data_dir)
        
        default_config = get_config("default")
        self.assertEqual(default_config.data_dir, "data/training")
        
        # Test invalid environment returns default
        invalid_config = get_config("invalid")
        self.assertEqual(invalid_config.data_dir, "data/training")

if __name__ == "__main__":
    unittest.main(verbosity=2) 