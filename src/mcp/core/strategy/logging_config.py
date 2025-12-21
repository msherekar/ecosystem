"""
Logging Configuration Module

Provides centralized logging configuration for the strategy system
with support for file rotation, different log levels, and structured logging.
"""

import logging
import logging.handlers
import json
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import traceback


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage']:
                log_data[key] = value
        
        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    COLOR_CODES = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        """Format with colors"""
        color = self.COLOR_CODES.get(record.levelname, self.COLOR_CODES['RESET'])
        reset = self.COLOR_CODES['RESET']
        
        # Create colored level name
        colored_levelname = f"{color}{record.levelname}{reset}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Format message
        message = record.getMessage()
        
        # Create formatted string
        formatted = f"{timestamp} | {colored_levelname:15} | {record.name:20} | {message}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class LoggingManager:
    """Centralized logging management"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: Dict[str, logging.Handler] = {}
        self.config = self._get_default_config()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "level": "INFO",
            "console": {
                "enabled": True,
                "level": "INFO",
                "format": "colored"
            },
            "file": {
                "enabled": True,
                "level": "DEBUG",
                "format": "structured",
                "filename": "strategy_system.log",
                "max_bytes": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5
            },
            "error_file": {
                "enabled": True,
                "level": "ERROR",
                "format": "structured",
                "filename": "errors.log",
                "max_bytes": 5 * 1024 * 1024,   # 5MB
                "backup_count": 3
            }
        }
    
    def setup_logging(self, debug: bool = False, config: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """Setup comprehensive logging configuration"""
        if config:
            self.config.update(config)
        
        # Adjust level for debug mode
        if debug:
            self.config["level"] = "DEBUG"
            self.config["console"]["level"] = "DEBUG"
        
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config["level"]))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Setup console handler
        if self.config["console"]["enabled"]:
            self._setup_console_handler(root_logger)
        
        # Setup file handler
        if self.config["file"]["enabled"]:
            self._setup_file_handler(root_logger)
        
        # Setup error file handler
        if self.config["error_file"]["enabled"]:
            self._setup_error_file_handler(root_logger)
        
        # Log startup message
        logger = logging.getLogger("strategy_system")
        logger.info("Logging system initialized")
        logger.debug(f"Logging configuration: {self.config}")
        
        return logger
    
    def _setup_console_handler(self, logger: logging.Logger):
        """Setup console logging handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.config["console"]["level"]))
        
        if self.config["console"]["format"] == "colored":
            formatter = ColoredConsoleFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        self.handlers["console"] = console_handler
    
    def _setup_file_handler(self, logger: logging.Logger):
        """Setup file logging handler"""
        log_file = self.log_dir / self.config["file"]["filename"]
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config["file"]["max_bytes"],
            backupCount=self.config["file"]["backup_count"]
        )
        file_handler.setLevel(getattr(logging, self.config["file"]["level"]))
        
        if self.config["file"]["format"] == "structured":
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        self.handlers["file"] = file_handler
    
    def _setup_error_file_handler(self, logger: logging.Logger):
        """Setup error-only file handler"""
        error_file = self.log_dir / self.config["error_file"]["filename"]
        
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=self.config["error_file"]["max_bytes"],
            backupCount=self.config["error_file"]["backup_count"]
        )
        error_handler.setLevel(getattr(logging, self.config["error_file"]["level"]))
        error_handler.setFormatter(StructuredFormatter())
        
        logger.addHandler(error_handler)
        self.handlers["error_file"] = error_handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a named logger"""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]
    
    def set_level(self, level: str, handler_name: Optional[str] = None):
        """Set logging level for specific handler or all"""
        log_level = getattr(logging, level.upper())
        
        if handler_name and handler_name in self.handlers:
            self.handlers[handler_name].setLevel(log_level)
        else:
            # Set for all handlers
            for handler in self.handlers.values():
                handler.setLevel(log_level)
        
        logging.getLogger().info(f"Logging level set to {level}")
    
    def add_context_filter(self, context: Dict[str, Any]):
        """Add context filter to enrich log records"""
        class ContextFilter(logging.Filter):
            def filter(self, record):
                for key, value in context.items():
                    setattr(record, key, value)
                return True
        
        context_filter = ContextFilter()
        for handler in self.handlers.values():
            handler.addFilter(context_filter)
    
    def get_log_files(self) -> List[Path]:
        """Get list of current log files"""
        return list(self.log_dir.glob("*.log*"))
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        import time
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        removed_count = 0
        for log_file in self.get_log_files():
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            logging.getLogger().info(f"Cleaned up {removed_count} old log files")


# Global logging manager instance
_logging_manager = LoggingManager()


def setup_logging(debug: bool = False, config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Setup logging configuration (convenience function)"""
    return _logging_manager.setup_logging(debug, config)


def get_logger(name: str) -> logging.Logger:
    """Get named logger (convenience function)"""
    return _logging_manager.get_logger(name)


class LogCapture:
    """Context manager for capturing log messages in tests"""
    
    def __init__(self, logger_name: str = None, level: str = "DEBUG"):
        self.logger_name = logger_name
        self.level = getattr(logging, level)
        self.handler = None
        self.records = []
    
    def __enter__(self):
        self.handler = logging.handlers.MemoryHandler(capacity=1000)
        self.handler.setLevel(self.level)
        
        if self.logger_name:
            logger = logging.getLogger(self.logger_name)
        else:
            logger = logging.getLogger()
        
        logger.addHandler(self.handler)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            self.records = self.handler.buffer[:]
            
            if self.logger_name:
                logger = logging.getLogger(self.logger_name)
            else:
                logger = logging.getLogger()
            
            logger.removeHandler(self.handler)
    
    def get_messages(self, level: str = None) -> List[str]:
        """Get captured log messages"""
        if level:
            level_num = getattr(logging, level.upper())
            return [record.getMessage() for record in self.records if record.levelno >= level_num]
        return [record.getMessage() for record in self.records]


def main():
    """Test logging configuration"""
    print("Testing Logging Configuration...")
    
    # Test basic setup
    logger = setup_logging(debug=True)
    logger.info("Testing info message")
    logger.warning("Testing warning message")
    logger.error("Testing error message")
    print("✅ Basic logging setup passed")
    
    # Test structured logging
    logger.info("Structured message", extra={"user_id": "123", "action": "test"})
    print("✅ Structured logging passed")
    
    # Test log capture
    with LogCapture("test_logger") as capture:
        test_logger = logging.getLogger("test_logger")
        test_logger.info("Captured message 1")
        test_logger.error("Captured message 2")
    
    messages = capture.get_messages()
    assert len(messages) == 2, "Should capture both messages"
    assert "Captured message 1" in messages[0], "Should capture info message"
    print("✅ Log capture passed")
    
    # Test exception logging
    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.exception("Exception occurred during test")
    print("✅ Exception logging passed")
    
    # Test context filter
    _logging_manager.add_context_filter({"session_id": "test_session"})
    logger.info("Message with context")
    print("✅ Context filter passed")
    
    # Test log file management
    log_files = _logging_manager.get_log_files()
    assert len(log_files) > 0, "Should have log files"
    print(f"✅ Log file management passed - Found {len(log_files)} log files")
    
    print("🎉 All logging tests passed!")


if __name__ == "__main__":
    def test_static_logging():
        """Static logging tests"""
        print("Running static logging tests...")
        
        manager = LoggingManager()
        config = manager._get_default_config()
        
        # Test default configuration
        assert "console" in config, "Should have console config"
        assert "file" in config, "Should have file config"
        assert config["level"] == "INFO", "Default level should be INFO"
        
        print("✅ Static logging tests passed!")
    
    def test_dynamic_logging():
        """Dynamic logging tests"""
        print("Running dynamic logging tests...")
        
        # Run main tests
        main()
        
        print("✅ Dynamic logging tests passed!")
    
    # Run tests
    test_static_logging()
    test_dynamic_logging()