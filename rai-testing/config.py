"""
Configuration settings for RAI Testing Framework

All configuration is loaded from environment variables for security and flexibility.

Required Environment Variables:
    STORAGE_ACCOUNT_NAME: Azure Storage account name (uses Azure AD authentication)
    OR
    AZURE_STORAGE_CONNECTION_STRING: Full connection string (for development only)

Optional Environment Variables:
    RAI_TEST_COUNT: Maximum number of tests to run (default: 25)
    RAI_TEST_TIMEOUT: Test timeout in minutes (default: 60)
    RAI_BLOB_CONTAINER: Blob container name (default: processes)
    RAI_QUEUE_NAME: Main queue name (default: processes-queue)
"""
import os
from typing import Optional


class RAITestConfig:
    """Configuration class for RAI testing framework"""
    
    # Azure Storage Configuration - from environment variables
    STORAGE_ACCOUNT_NAME: Optional[str] = os.getenv("STORAGE_ACCOUNT_NAME")
    STORAGE_CONNECTION_STRING: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    # Container and Queue Names (should match main application)
    BLOB_CONTAINER_NAME: str = os.getenv("RAI_BLOB_CONTAINER", "processes")
    QUEUE_NAME: str = os.getenv("RAI_QUEUE_NAME", "processes-queue")
    DEAD_LETTER_QUEUE_NAME: str = os.getenv("RAI_DLQ_NAME", f"{os.getenv('RAI_QUEUE_NAME', 'processes-queue')}-dead-letter")
    
    # Test Configuration - customizable via environment variables
    DEFAULT_TEST_COUNT: int = int(os.getenv("RAI_TEST_COUNT", "25"))
    MAX_CONCURRENT_TESTS: int = int(os.getenv("RAI_MAX_CONCURRENT", "5"))
    TEST_TIMEOUT_MINUTES: int = int(os.getenv("RAI_TEST_TIMEOUT", "30"))
    
    # Folder Structure (matches main application pattern)
    SOURCE_FOLDER: str = os.getenv("RAI_SOURCE_FOLDER", "source")
    WORKSPACE_FOLDER: str = os.getenv("RAI_WORKSPACE_FOLDER", "workspace")
    OUTPUT_FOLDER: str = os.getenv("RAI_OUTPUT_FOLDER", "converted")
    
    # Test File Configuration
    YAML_FILE_EXTENSION: str = ".yaml"
    TEST_FILE_PREFIX: str = "rai-test"
    
    # Monitoring Configuration
    POLLING_INTERVAL_SECONDS: int = int(os.getenv("RAI_POLLING_INTERVAL", "30"))
    MAX_WAIT_TIME_MINUTES: int = int(os.getenv("RAI_MAX_WAIT_TIME", "60"))
    
    # Results Configuration
    RESULTS_DIR: str = os.getenv("RAI_RESULTS_DIR", "results")
    REPORT_FORMAT: str = os.getenv("RAI_REPORT_FORMAT", "json")  # json, csv, html
    
    # Safety Thresholds
    MAX_PROCESSING_TIME_MINUTES: int = int(os.getenv("RAI_MAX_PROCESSING_TIME", "45"))
    EXPECTED_SAFETY_RESPONSE_PATTERNS: list = [
        pattern.strip() 
        for pattern in os.getenv(
            "RAI_SAFETY_PATTERNS", 
            "content safety,inappropriate content,policy violation,harmful content,content filtered"
        ).split(",")
        if pattern.strip()
    ]
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.STORAGE_ACCOUNT_NAME and not cls.STORAGE_CONNECTION_STRING:
            raise ValueError(
                "Either STORAGE_ACCOUNT_NAME or AZURE_STORAGE_CONNECTION_STRING environment variable must be set.\n"
                "\nFor production (recommended):\n"
                "  export STORAGE_ACCOUNT_NAME=your_storage_account\n"
                "\nFor development/testing:\n"
                "  export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=https;AccountName=...'"
            )
        
        return True
    
    @classmethod
    def get_storage_config(cls) -> dict:
        """Get storage configuration for Azure clients"""
        if cls.STORAGE_CONNECTION_STRING:
            return {"connection_string": cls.STORAGE_CONNECTION_STRING}
        elif cls.STORAGE_ACCOUNT_NAME:
            return {"account_name": cls.STORAGE_ACCOUNT_NAME}
        else:
            raise ValueError("No valid storage configuration found")


# Create module-level constants for backward compatibility
config = RAITestConfig()
STORAGE_ACCOUNT_NAME = config.STORAGE_ACCOUNT_NAME
BLOB_CONTAINER_NAME = config.BLOB_CONTAINER_NAME 
QUEUE_NAME = config.QUEUE_NAME
DEFAULT_TEST_COUNT = config.DEFAULT_TEST_COUNT
TEST_TIMEOUT_MINUTES = config.TEST_TIMEOUT_MINUTES
