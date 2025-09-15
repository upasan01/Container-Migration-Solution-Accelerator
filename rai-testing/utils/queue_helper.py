"""
Azure Storage Queue helper for RAI testing.
Handles sending test messages to trigger agent processing.
"""

import json
import logging
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime

from azure.storage.queue import QueueServiceClient, QueueClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

import sys
from pathlib import Path

# Add the parent directory to sys.path to import config
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from config import RAITestConfig


class QueueTestHelper:
    """Helper class for managing test messages in Azure Storage Queue"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.logger = logging.getLogger(__name__)
        self._queue_client = None
        self._dlq_client = None
    
    @property
    def queue_client(self) -> QueueClient:
        """Get or create main queue client"""
        if self._queue_client is None:
            storage_config = self.config.get_storage_config()
            
            if "connection_string" in storage_config:
                service_client = QueueServiceClient.from_connection_string(
                    storage_config["connection_string"]
                )
            elif "account_name" in storage_config:
                account_url = f"https://{storage_config['account_name']}.queue.core.windows.net"
                service_client = QueueServiceClient(
                    account_url=account_url,
                    credential=DefaultAzureCredential()
                )
            else:
                raise ValueError("Invalid storage configuration")
            
            self._queue_client = service_client.get_queue_client(self.config.QUEUE_NAME)
                
        return self._queue_client
    
    @property
    def dlq_client(self) -> QueueClient:
        """Get or create dead letter queue client"""
        if self._dlq_client is None:
            storage_config = self.config.get_storage_config()
            
            if "connection_string" in storage_config:
                service_client = QueueServiceClient.from_connection_string(
                    storage_config["connection_string"]
                )
            elif "account_name" in storage_config:
                account_url = f"https://{storage_config['account_name']}.queue.core.windows.net"
                service_client = QueueServiceClient(
                    account_url=account_url,
                    credential=DefaultAzureCredential()
                )
            else:
                raise ValueError("Invalid storage configuration")
            
            self._dlq_client = service_client.get_queue_client(self.config.DEAD_LETTER_QUEUE_NAME)
                
        return self._dlq_client
    
    def send_test_message(
        self,
        process_id: str,
        user_id: str = "rai-test-user",
        additional_data: Dict[str, Any] = None,
        visibility_timeout: int = None,
        time_to_live: int = None
    ) -> str:
        """Send a test message to trigger processing"""
        
        # Create message matching the expected format from the main application
        message_data = {
            "process_id": process_id,
            "user_id": user_id,
            "migration_request": self._create_default_migration_request(process_id, user_id),
            "retry_count": 0,
            "created_time": datetime.utcnow().isoformat(),
            "priority": "normal"
        }
        
        # Add any additional data
        if additional_data:
            message_data.update(additional_data)
        
        # Convert to JSON
        message_json = json.dumps(message_data)
        
        try:
            # Send message to queue
            result = self.queue_client.send_message(
                message_json,
                visibility_timeout=visibility_timeout,
                time_to_live=time_to_live
            )
            
            self.logger.info(f"Sent test message for process_id: {process_id}")
            return result.id
            
        except Exception as e:
            self.logger.error(f"Failed to send test message for {process_id}: {e}")
            raise
    
    def send_batch_test_messages(
        self,
        process_ids: List[str], 
        user_id: str = "rai-test-user",
        additional_data: Dict[str, Any] = None,
        batch_size: int = 10
    ) -> List[str]:
        """Send multiple test messages in batches"""
        
        message_ids = []
        
        for i in range(0, len(process_ids), batch_size):
            batch = process_ids[i:i + batch_size]
            
            for process_id in batch:
                try:
                    message_id = self.send_test_message(
                        process_id=process_id,
                        user_id=user_id,
                        additional_data=additional_data
                    )
                    message_ids.append(message_id)
                    
                except Exception as e:
                    self.logger.error(f"Failed to send message for {process_id}: {e}")
        
        return message_ids
    
    def _create_default_migration_request(
        self,
        process_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Create default migration request matching main application format"""
        
        return {
            "process_id": process_id,
            "user_id": user_id,
            "container_name": self.config.BLOB_CONTAINER_NAME,
            "source_file_folder": self.config.SOURCE_FOLDER,
            "workspace_file_folder": self.config.WORKSPACE_FOLDER,
            "output_file_folder": self.config.OUTPUT_FOLDER,
            "migration_type": "rai-test",
            "source_platform": "test",
            "target_platform": "aks",
            "test_execution": True,
            "rai_test_case": True
        }
    
    def peek_queue_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Peek at messages in the queue without removing them"""
        
        try:
            messages = []
            peeked = self.queue_client.peek_messages(max_messages=max_messages)
            
            for message in peeked:
                try:
                    # Try to decode and parse message content
                    content = message.content
                    
                    # Handle base64 encoded content
                    if self._is_base64_encoded(content):
                        content = base64.b64decode(content).decode('utf-8')
                    
                    parsed_content = json.loads(content)
                    
                    messages.append({
                        "id": message.id,
                        "inserted_on": message.inserted_on,
                        "expires_on": message.expires_on,
                        "dequeue_count": message.dequeue_count,
                        "content": parsed_content
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse message {message.id}: {e}")
                    messages.append({
                        "id": message.id,
                        "raw_content": message.content,
                        "parse_error": str(e)
                    })
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to peek queue messages: {e}")
            return []
    
    def get_queue_properties(self) -> Dict[str, Any]:
        """Get queue properties including message count"""
        
        try:
            properties = self.queue_client.get_queue_properties()
            
            return {
                "name": self.config.QUEUE_NAME,
                "approximate_message_count": properties.approximate_message_count,
                "metadata": properties.metadata or {}
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get queue properties: {e}")
            return {"name": self.config.QUEUE_NAME, "error": str(e)}
    
    def get_dlq_properties(self) -> Dict[str, Any]:
        """Get dead letter queue properties"""
        
        try:
            properties = self.dlq_client.get_queue_properties()
            
            return {
                "name": self.config.DEAD_LETTER_QUEUE_NAME,
                "approximate_message_count": properties.approximate_message_count,
                "metadata": properties.metadata or {}
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get DLQ properties: {e}")
            return {"name": self.config.DEAD_LETTER_QUEUE_NAME, "error": str(e)}
    
    def peek_dlq_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Peek at messages in the dead letter queue"""
        
        try:
            messages = []
            peeked = self.dlq_client.peek_messages(max_messages=max_messages)
            
            for message in peeked:
                try:
                    # Try to decode and parse message content
                    content = message.content
                    
                    # Handle base64 encoded content
                    if self._is_base64_encoded(content):
                        content = base64.b64decode(content).decode('utf-8')
                    
                    parsed_content = json.loads(content)
                    
                    messages.append({
                        "id": message.id,
                        "inserted_on": message.inserted_on,
                        "expires_on": message.expires_on,
                        "dequeue_count": message.dequeue_count,
                        "content": parsed_content
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse DLQ message {message.id}: {e}")
                    messages.append({
                        "id": message.id,
                        "raw_content": message.content,
                        "parse_error": str(e)
                    })
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to peek DLQ messages: {e}")
            return []
    
    def clear_test_messages(self, confirm: bool = False) -> Dict[str, int]:
        """Clear all messages from both queues (use with caution!)"""
        
        if not confirm:
            raise ValueError("Must set confirm=True to clear messages")
        
        cleared = {"main_queue": 0, "dlq": 0}
        
        try:
            # Clear main queue
            self.queue_client.clear_messages()
            main_props = self.get_queue_properties()
            cleared["main_queue"] = main_props.get("approximate_message_count", 0)
            
            self.logger.info(f"Cleared main queue: {self.config.QUEUE_NAME}")
            
        except Exception as e:
            self.logger.error(f"Failed to clear main queue: {e}")
        
        try:
            # Clear dead letter queue
            self.dlq_client.clear_messages()
            dlq_props = self.get_dlq_properties()
            cleared["dlq"] = dlq_props.get("approximate_message_count", 0)
            
            self.logger.info(f"Cleared DLQ: {self.config.DEAD_LETTER_QUEUE_NAME}")
            
        except Exception as e:
            self.logger.error(f"Failed to clear DLQ: {e}")
        
        return cleared
    
    def check_queues_exist(self) -> Dict[str, bool]:
        """Check if both queues exist"""
        
        result = {}
        
        try:
            self.queue_client.get_queue_properties()
            result["main_queue"] = True
        except ResourceNotFoundError:
            result["main_queue"] = False
        except Exception as e:
            self.logger.error(f"Error checking main queue: {e}")
            result["main_queue"] = False
        
        try:
            self.dlq_client.get_queue_properties()
            result["dlq"] = True
        except ResourceNotFoundError:
            result["dlq"] = False
        except Exception as e:
            self.logger.error(f"Error checking DLQ: {e}")
            result["dlq"] = False
        
        return result
    
    def ensure_queues_exist(self) -> Dict[str, bool]:
        """Ensure both queues exist, create if needed"""
        
        result = {"main_queue": False, "dlq": False}
        
        # Main queue
        try:
            self.queue_client.create_queue()
            result["main_queue"] = True
            self.logger.info(f"Created main queue: {self.config.QUEUE_NAME}")
        except ResourceExistsError:
            result["main_queue"] = True
        except Exception as e:
            self.logger.error(f"Failed to create main queue: {e}")
        
        # Dead letter queue
        try:
            self.dlq_client.create_queue()
            result["dlq"] = True
            self.logger.info(f"Created DLQ: {self.config.DEAD_LETTER_QUEUE_NAME}")
        except ResourceExistsError:
            result["dlq"] = True
        except Exception as e:
            self.logger.error(f"Failed to create DLQ: {e}")
        
        return result
    
    def _is_base64_encoded(self, data: str) -> bool:
        """Check if string is base64 encoded"""
        try:
            if isinstance(data, str):
                encoded = data.encode('utf-8')
            else:
                encoded = data
            
            decoded = base64.b64decode(encoded, validate=True)
            # Try to decode as UTF-8 to see if it's text
            decoded.decode('utf-8')
            return True
        except Exception:
            return False
