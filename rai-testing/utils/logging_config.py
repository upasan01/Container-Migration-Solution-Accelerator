import logging
import sys
from typing import Optional, List
from pathlib import Path


def setup_logging(
    debug: bool = False,
    log_to_console: bool = True,
    log_to_file: Optional[str] = None,
    log_level: Optional[int] = None
) -> None:
    """
    Configure logging for RAI testing framework
    
    Args:
        debug: Enable debug logging if True, otherwise use INFO level
        log_to_console: Enable logging to console (default: True)
        log_to_file: Optional file path for logging to file
        log_level: Override log level (takes precedence over debug flag)
    """
    
    # Determine log level
    if log_level is not None:
        level = log_level
    elif debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Create handlers list
    handlers = []
    
    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = '%(levelname)s: %(message)s'
        console_handler.setFormatter(logging.Formatter(console_format))
        handlers.append(console_handler)
    
    # Add file handler if requested
    if log_to_file:
        # Ensure the directory exists
        log_file_path = Path(log_to_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_to_file, mode='a', encoding='utf-8')
        file_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
        file_handler.setFormatter(logging.Formatter(file_format))
        handlers.append(file_handler)
    
    # Configure basic logging
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
     # Configure repository logging based on debug mode
    repo_level = logging.INFO if debug else logging.WARNING
    logging.getLogger('sas.cosmosdb.sql.repository').setLevel(repo_level)
    
    # Azure SDK logging
    logging.getLogger('azure').setLevel(logging.ERROR)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
    logging.getLogger('azure.storage').setLevel(logging.ERROR)
    logging.getLogger('azure.cosmos').setLevel(logging.ERROR)
    
    # HTTP and connection logging
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('requests').setLevel(logging.ERROR)
    
    # UI library logging
    logging.getLogger('rich').setLevel(logging.WARNING)
    
   


