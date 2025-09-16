"""
Test monitoring and reporting for RAI testing framework.
Monitors agent responses via Cosmos DB queries and generates compliance reports.
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
from .cosmos_helper import CosmosDBHelper


class TestMonitor:
    """Monitor test execution via Cosmos DB queries"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.logger = logging.getLogger(__name__)
        self.cosmos_helper = CosmosDBHelper(config)
    
    async def monitor_with_cosmos_db(
        self,
        process_id: str,
        timeout_minutes: int = None,
        polling_interval_seconds: int = None
    ) -> Dict[str, Any]:
        """
        Monitor test execution using Cosmos DB queries for agent telemetry
        
        Args:
            process_id: The process ID to monitor
            timeout_minutes: Maximum time to wait for completion
            polling_interval_seconds: How often to poll Cosmos DB
        
        Returns:
            Dictionary with monitoring results including final_outcome from agent
        """
        timeout_minutes = timeout_minutes or self.config.TEST_TIMEOUT_MINUTES
        polling_interval_seconds = polling_interval_seconds or self.config.COSMOS_POLLING_INTERVAL_SECONDS
        
        self.logger.info(f"Starting Cosmos DB monitoring for process_id: {process_id}")
        
        try:
            # Use the Cosmos DB helper to wait for completion
            result = await self.cosmos_helper.wait_for_completion(
                process_id=process_id,
                timeout_minutes=timeout_minutes,
                polling_interval_seconds=polling_interval_seconds
            )
            
            # Transform the result into the expected format
            if result["monitoring_status"] == "completed" and result["success"]:
                status = "passed"
            elif result["monitoring_status"] == "completed" and not result["success"]:
                status = "failed"
            elif result["monitoring_status"] == "timeout":
                status = "timeout"
            else:
                status = "error"
            
            return {
                "process_id": process_id,
                "result": status,
                "success": result["success"],
                "error_message": result["error_message"],
                "final_outcome": result.get("final_outcome"),
                "elapsed_time_seconds": result.get("elapsed_time_seconds"),
                "monitoring_status": result["monitoring_status"]
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring process_id {process_id} with Cosmos DB: {e}")
            return {
                "process_id": process_id,
                "result": "error",
                "success": False,
                "error_message": f"Monitoring error: {str(e)}",
                "final_outcome": None,
                "monitoring_status": "error"
            }
    
    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'cosmos_helper'):
            await self.cosmos_helper.close()
