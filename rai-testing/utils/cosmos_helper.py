"""
Cosmos DB helper for querying agent telemetry in RAI testing.
Uses AgentActivityRepository for strongly-typed access to ProcessStatus objects.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

import sys
from pathlib import Path

# Add the parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from config import RAITestConfig
from utils.repositories import AgentActivityRepository, ProcessStatus


class CosmosDBHelper:
    """Helper class for Cosmos DB operations related to agent telemetry using ProcessStatus objects"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.logger = logging.getLogger(__name__)
    
    async def get_process_status(self, process_id: str) -> Optional[ProcessStatus]:
        """
        Get ProcessStatus object by process_id with strict typing
        
        Args:
            process_id: The process ID to look up in the agent_telemetry container
        
        Returns:
            ProcessStatus object or None if not found
        """
        try:
            async with AgentActivityRepository(self.config) as repository:
                process_status = await repository.get_async(process_id)
                if process_status:
                    self.logger.debug(f"Found ProcessStatus for process_id: {process_id}")
                    return process_status
                else:
                    self.logger.debug(f"No ProcessStatus found for process_id: {process_id}")
                    return None
            
        except Exception as e:
            self.logger.error(f"Error querying ProcessStatus for process_id {process_id}: {e}")
            return None
        
    async def get_final_outcome(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the final_outcome from ProcessStatus for a specific process_id
        
        Args:
            process_id: The process ID to look up
        
        Returns:
            Dictionary containing final_outcome with 'success' bool and 'error_message',
            or None if not found or no final_outcome available
        """
        process_status = await self.get_process_status(process_id)
        
        if not process_status:
            return None
        
        final_outcome = process_status.final_outcome
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
        Wait for a process to complete by polling ProcessStatus
        
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
                    "monitoring_status": "timeout"
                }
            
            # Query for final outcome using ProcessStatus
            final_outcome = await self.get_final_outcome(process_id)
            
            if final_outcome is not None:
                self.logger.info(f"Process completed for process_id: {process_id}, success: {final_outcome['success']}")
                return {
                    "process_id": process_id,
                    "success": final_outcome["success"],
                    "error_message": final_outcome["error_message"],
                    "monitoring_status": "completed",
                    "elapsed_time_seconds": elapsed_time
                }
            
            # Wait before next poll
            self.logger.debug(f"No final outcome yet for process_id: {process_id}, waiting {polling_interval_seconds}s...")
            await asyncio.sleep(polling_interval_seconds)


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
    return await helper.get_final_outcome(process_id)


# Additional convenience function for ProcessStatus
async def get_process_status(process_id: str, config: RAITestConfig = None) -> Optional[ProcessStatus]:
    """
    Convenience function to get ProcessStatus object for a single process_id
    
    Args:
        process_id: The process ID to look up
        config: RAI test configuration
    
    Returns:
        ProcessStatus object or None
    """
    helper = CosmosDBHelper(config)
    return await helper.get_process_status(process_id)
