"""
Logging configuration with daily rotation
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(log_filename: str, log_level: str):
    """
    Setup logging with daily rotation
    
    Args:
        log_filename: Full path to log file
        log_level: Log level (trace, warning, error)
    """
    # Map log levels
    level_map = {
        "trace": logging.DEBUG,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }
    
    level = level_map.get(log_level.lower(), logging.INFO)
    
    # Create log directory if needed
    log_path = Path(log_filename)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup file handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,
        when='midnight',
        interval=1,
        backupCount=0,  # Keep all log files indefinitely
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "-%Y%m%d"
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    
    # Also capture stderr to log
    class StderrToLogger:
        """Redirect stderr to logger"""
        def __init__(self, logger, level):
            self.logger = logger
            self.level = level
            self.linebuf = ''
        
        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.level, line.rstrip())
        
        def flush(self):
            pass
    
    # Redirect stderr to logger
    sys.stderr = StderrToLogger(logging.getLogger('STDERR'), logging.ERROR)
    
    return logging.getLogger('llmserver')
