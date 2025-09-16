"""
Cosmos DB helper for querying agent telemetry in RAI testing.
Handles connections to the migration_db database and agent_telemetry container.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions

import sys
from pathlib import Path

# Add the parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from config import RAITestConfig


class CosmosDBHelper:
    """Helper class for Cosmos DB operations related to agent telemetry"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._database = None
        self._container = None
    
    async def _ensure_client(self):
        """Ensure Cosmos DB client is initialized"""
        if self._client is None:
            try:
                cosmos_config = self.config.get_cosmos_config()
                self._client = CosmosClient(
                    cosmos_config["endpoint"],
                    cosmos_config["key"]
                )
                self._database = self._client.get_database_client(cosmos_config["database_name"])
                self._container = self._database.get_container_client(cosmos_config["container_name"])
                self.logger.debug("Cosmos DB client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Cosmos DB client: {e}")
                raise
    
    async def get_agent_telemetry(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Query agent telemetry by process_id
        
        Args:
            process_id: The process ID to look up in the agent_telemetry container
        
        Returns:
            Dictionary containing the agent telemetry document, or None if not found
        """
        await self._ensure_client()
        
        try:
            # Query the document by id (which should be the process_id)
            response = await self._container.read_item(
                item=process_id,
                partition_key=process_id  # Assuming process_id is also the partition key
            )
            
            self.logger.debug(f"Found agent telemetry for process_id: {process_id}")
            return response
            
        except exceptions.CosmosResourceNotFoundError:
            self.logger.debug(f"No agent telemetry found for process_id: {process_id}")
            return None
        except exceptions.CosmosHttpResponseError as e:
            self.logger.error(f"Cosmos DB HTTP error querying process_id {process_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error querying agent telemetry for process_id {process_id}: {e}")
            return None
    
    async def get_final_outcome(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the final_outcome from agent telemetry for a specific process_id
        
        Args:
            process_id: The process ID to look up
        
        Returns:
            Dictionary containing final_outcome with 'success' bool and 'error_message',
            or None if not found or no final_outcome available
        """
        telemetry = await self.get_agent_telemetry(process_id)
        
        if not telemetry:
            return None
        
        final_outcome = telemetry.get("final_outcome")
        if not final_outcome:
            self.logger.debug(f"No final_outcome found for process_id: {process_id}")
            return None
        
        # Validate the final_outcome structure
        if not isinstance(final_outcome, dict):
            self.logger.warning(f"Invalid final_outcome format for process_id {process_id}: {final_outcome}")
            return None
        
        # Ensure required fields are present
        success = final_outcome.get("success")
        error_message = final_outcome.get("error_message")
        
        if success is None:
            self.logger.warning(f"Missing 'success' field in final_outcome for process_id {process_id}")
            return None
        
        return {
            "success": bool(success),
            "error_message": error_message or ""
        }
    
    async def wait_for_completion(
        self,
        process_id: str,
        timeout_minutes: int = 30,
        polling_interval_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for a process to complete by polling Cosmos DB
        
        Args:
            process_id: The process ID to monitor
            timeout_minutes: Maximum time to wait for completion
            polling_interval_seconds: How often to poll Cosmos DB
        
        Returns:
            Dictionary with monitoring results including final_outcome
        """
        start_time = asyncio.get_event_loop().time()
        timeout_seconds = timeout_minutes * 60
        
        self.logger.info(f"Starting to monitor process_id: {process_id}")
        
        while True:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            
            if elapsed_time >= timeout_seconds:
                self.logger.warning(f"Timeout reached for process_id: {process_id}")
                return {
                    "process_id": process_id,
                    "success": False,
                    "error_message": f"Timeout after {timeout_minutes} minutes",
                    "final_outcome": None,
                    "monitoring_status": "timeout"
                }
            
            # Query for final outcome
            final_outcome = await self.get_final_outcome(process_id)
            
            if final_outcome is not None:
                self.logger.info(f"Process completed for process_id: {process_id}, success: {final_outcome['success']}")
                return {
                    "process_id": process_id,
                    "success": final_outcome["success"],
                    "error_message": final_outcome["error_message"],
                    "final_outcome": final_outcome,
                    "monitoring_status": "completed",
                    "elapsed_time_seconds": elapsed_time
                }
            
            # Wait before next poll
            self.logger.debug(f"No final outcome yet for process_id: {process_id}, waiting {polling_interval_seconds}s...")
            await asyncio.sleep(polling_interval_seconds)
    
    async def close(self):
        """Close the Cosmos DB client connection"""
        if self._client:
            await self._client.close()
            self.logger.debug("Cosmos DB client closed")


# Convenience function for single queries
async def query_agent_telemetry(process_id: str, config: RAITestConfig = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to query agent telemetry for a single process_id
    
    Args:
        process_id: The process ID to look up
        config: RAI test configuration
    
    Returns:
        Final outcome dictionary or None
    """
    helper = CosmosDBHelper(config)
    try:
        return await helper.get_final_outcome(process_id)
    finally:
        await helper.close()
