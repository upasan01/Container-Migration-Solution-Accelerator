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
    
    def create_test_folder(self, process_id: str = None) -> str:
        """Create a new test folder with unique GUID"""
        if process_id is None:
            process_id = str(uuid.uuid4())
        
        # Create folder structure matching main application
        folder_path = f"{process_id}/{self.config.SOURCE_FOLDER}"
        
        # Create a marker file to establish the folder structure
        marker_blob_name = f"{folder_path}/.keep"
        
        try:
            blob_client = self.blob_client.get_blob_client(
                container=self.config.BLOB_CONTAINER_NAME,
                blob=marker_blob_name
            )
            
            blob_client.upload_blob(
                data="# Folder marker for RAI testing\n",
                overwrite=True
            )
            
            self.logger.info(f"Created test folder: {folder_path}")
            return process_id
            
        except Exception as e:
            self.logger.error(f"Failed to create test folder {folder_path}: {e}")
            raise
    
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
    
    def upload_test_content(
        self,
        process_id: str,
        content: str,
        blob_name: str,
        folder_type: str = "source"
    ) -> str:
        """Upload test content directly as a blob"""
        
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
            
            blob_client.upload_blob(content.encode('utf-8'), overwrite=True)
            
            self.logger.info(f"Uploaded test content: {full_blob_name}")
            return full_blob_name
            
        except Exception as e:
            self.logger.error(f"Failed to upload test content to {full_blob_name}: {e}")
            raise
    
    def upload_multiple_files(
        self,
        process_id: str,
        file_paths: List[str],
        folder_type: str = "source"
    ) -> List[str]:
        """Upload multiple test files to the same process folder"""
        
        uploaded_blobs = []
        
        for file_path in file_paths:
            try:
                blob_name = self.upload_test_file(
                    process_id=process_id,
                    file_path=file_path,
                    folder_type=folder_type
                )
                uploaded_blobs.append(blob_name)
            except Exception as e:
                self.logger.error(f"Failed to upload {file_path}: {e}")
        
        return uploaded_blobs
    
    def list_test_files(self, process_id: str, folder_type: str = "source") -> List[str]:
        """List files in a test folder"""
        
        if folder_type == "source":
            folder = self.config.SOURCE_FOLDER
        elif folder_type == "workspace":
            folder = self.config.WORKSPACE_FOLDER  
        elif folder_type == "output":
            folder = self.config.OUTPUT_FOLDER
        else:
            raise ValueError(f"Invalid folder type: {folder_type}")
        
        prefix = f"{process_id}/{folder}/"
        
        try:
            container_client = self.blob_client.get_container_client(
                self.config.BLOB_CONTAINER_NAME
            )
            
            blobs = []
            for blob in container_client.list_blobs(name_starts_with=prefix):
                if not blob.name.endswith('/.keep'):  # Skip marker files
                    blobs.append(blob.name)
            
            return blobs
            
        except Exception as e:
            self.logger.error(f"Failed to list files in {prefix}: {e}")
            raise
    
    def download_test_file(
        self,
        process_id: str,
        blob_name: str,
        local_path: str,
        folder_type: str = "output"
    ) -> bool:
        """Download a test file from blob storage"""
        
        if folder_type == "source":
            folder = self.config.SOURCE_FOLDER
        elif folder_type == "workspace":
            folder = self.config.WORKSPACE_FOLDER
        elif folder_type == "output":
            folder = self.config.OUTPUT_FOLDER
        else:
            raise ValueError(f"Invalid folder type: {folder_type}")
        
        full_blob_name = f"{process_id}/{folder}/{blob_name}"
        
        try:
            blob_client = self.blob_client.get_blob_client(
                container=self.config.BLOB_CONTAINER_NAME,
                blob=full_blob_name
            )
            
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())
            
            self.logger.info(f"Downloaded test file: {full_blob_name} -> {local_path}")
            return True
            
        except ResourceNotFoundError:
            self.logger.warning(f"Test file not found: {full_blob_name}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to download test file {full_blob_name}: {e}")
            return False
    
    def cleanup_test_folder(self, process_id: str) -> bool:
        """Clean up all files in a test folder"""
        
        try:
            container_client = self.blob_client.get_container_client(
                self.config.BLOB_CONTAINER_NAME
            )
            
            # List all blobs with the process_id prefix
            prefix = f"{process_id}/"
            blobs_to_delete = []
            
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blobs_to_delete.append(blob.name)
            
            # Delete all blobs
            for blob_name in blobs_to_delete:
                try:
                    blob_client = self.blob_client.get_blob_client(
                        container=self.config.BLOB_CONTAINER_NAME,
                        blob=blob_name
                    )
                    blob_client.delete_blob()
                    self.logger.debug(f"Deleted blob: {blob_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete blob {blob_name}: {e}")
            
            self.logger.info(f"Cleaned up test folder: {process_id} ({len(blobs_to_delete)} files)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup test folder {process_id}: {e}")
            return False
    
    def check_container_exists(self) -> bool:
        """Check if the test container exists"""
        try:
            container_client = self.blob_client.get_container_client(
                self.config.BLOB_CONTAINER_NAME
            )
            container_client.get_container_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            self.logger.error(f"Error checking container existence: {e}")
            return False
    
    def ensure_container_exists(self) -> bool:
        """Ensure the test container exists, create if needed"""
        if self.check_container_exists():
            return True
        
        try:
            container_client = self.blob_client.get_container_client(
                self.config.BLOB_CONTAINER_NAME
            )
            container_client.create_container()
            self.logger.info(f"Created container: {self.config.BLOB_CONTAINER_NAME}")
            return True
        except ResourceExistsError:
            # Container was created by another process
            return True
        except Exception as e:
            self.logger.error(f"Failed to create container: {e}")
            return False
    
    def get_test_folder_info(self, process_id: str) -> Dict[str, Any]:
        """Get information about a test folder"""
        info = {
            "process_id": process_id,
            "folders": {},
            "total_files": 0,
            "total_size": 0
        }
        
        try:
            container_client = self.blob_client.get_container_client(
                self.config.BLOB_CONTAINER_NAME
            )
            
            prefix = f"{process_id}/"
            
            for blob in container_client.list_blobs(name_starts_with=prefix):
                if blob.name.endswith('/.keep'):
                    continue
                
                # Determine folder type
                parts = blob.name.split('/')
                if len(parts) >= 2:
                    folder_type = parts[1]
                    if folder_type not in info["folders"]:
                        info["folders"][folder_type] = {
                            "files": [],
                            "count": 0,
                            "size": 0
                        }
                    
                    info["folders"][folder_type]["files"].append({
                        "name": blob.name,
                        "size": blob.size,
                        "last_modified": blob.last_modified
                    })
                    info["folders"][folder_type]["count"] += 1
                    info["folders"][folder_type]["size"] += blob.size
                    
                info["total_files"] += 1
                info["total_size"] += blob.size
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get folder info for {process_id}: {e}")
            return info
