"""
Azure Blob Storage helper for RAI testing.
Handles uploading test files to blob storage with unique GUID folder structure.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

import sys
from pathlib import Path

# Add the parent directory to sys.path to import config
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from config import RAITestConfig

class BlobStorageTestHelper:
    """Helper class for managing test files in Azure Blob Storage"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.logger = logging.getLogger(__name__)
        self._blob_client = None
        
    @property  
    def blob_client(self) -> BlobServiceClient:
        """Get or create blob service client"""
        if self._blob_client is None:
            storage_config = self.config.get_storage_config()
            
            if "connection_string" in storage_config:
                self._blob_client = BlobServiceClient.from_connection_string(
                    storage_config["connection_string"]
                )
            elif "account_name" in storage_config:
                account_url = f"https://{storage_config['account_name']}.blob.core.windows.net"
                self._blob_client = BlobServiceClient(
                    account_url=account_url,
                    credential=DefaultAzureCredential()
                )
            else:
                raise ValueError("Invalid storage configuration")
                
        return self._blob_client
    
    def upload_test_file(
        self,
        process_id: str,
        file_path: str,
        blob_name: str = None,
        folder_type: str = "source"
    ) -> str:
        """Upload a test file to the specified process folder"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test file not found: {file_path}")
        
        if blob_name is None:
            blob_name = os.path.basename(file_path)
        
        # Determine folder based on type
        if folder_type == "source":
            folder = self.config.SOURCE_FOLDER
        elif folder_type == "workspace":
            folder = self.config.WORKSPACE_FOLDER
        elif folder_type == "output":
            folder = self.config.OUTPUT_FOLDER
        else:
            raise ValueError(f"Invalid folder type: {folder_type}")
        
        # Build full blob path
        full_blob_name = f"{process_id}/{folder}/{blob_name}"
        
        try:
            blob_client = self.blob_client.get_blob_client(
                container=self.config.BLOB_CONTAINER_NAME,
                blob=full_blob_name
            )
            
            with open(file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True)
            
            self.logger.info(f"Uploaded test file: {full_blob_name}")
            return full_blob_name
            
        except Exception as e:
            self.logger.error(f"Failed to upload test file {file_path}: {e}")
            raise