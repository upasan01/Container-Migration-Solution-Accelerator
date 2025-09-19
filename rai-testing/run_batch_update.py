#!/usr/bin/env python3
"""
Update Batch Results Script

Updates CSV file with final test results from Cosmos DB after batch tests with --no-wait have completed.
Reads CSV file, finds process IDs, queries Cosmos DB once for final outcomes, and updates the CSV.

Usage:
    python run_batch_update.py --csv-file test_cases.csv
    python run_batch_update.py --csv-file test_cases.csv --include-full-response --debug
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from config import RAITestConfig
from utils.test_manager import TestManager, TestCase
from utils.cosmos_helper import CosmosDBHelper
from utils.queue_helper import QueueTestHelper
from utils.logging_config import setup_logging
from utils.environment_validator import validate_environment
from utils.test_formatter import extract_error_reason


class BatchResultsUpdater:
    """Updates CSV files with final test results from Cosmos DB"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        self.cosmos_helper = CosmosDBHelper(self.config)
        self.queue_helper = QueueTestHelper(self.config)
        
        # Test manager will be initialized when CSV file is provided
        self.test_manager: Optional[TestManager] = None

    async def update_results(self, csv_file: str, include_full_response: bool = False, debug: bool = False) -> Dict[str, Any]:
        """
        Update CSV file with final test results from Cosmos DB
        
        Args:
            csv_file: Path to CSV file with test cases that have process_ids
            include_full_response: Whether to include full error response in results
            debug: Enable debug logging
        
        Returns:
            Dictionary containing update results and summary
        """
        # Validate environment configuration before proceeding
        if not validate_environment():
            exit(1)
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = Path(__file__).parent / "logs" / f"run_batch_update_{today}_{str(uuid.uuid4())[:8]}.log"
        setup_logging(debug=debug, log_to_console=False, log_to_file=str(log_path))
            
        try:
            start_time = asyncio.get_event_loop().time()

            # Load test cases from CSV
            self.test_manager = TestManager(csv_file)
            test_cases = self.test_manager.load_test_cases()
            
            # Filter for test cases that have process_ids (were queued)
            queued_test_cases = [
                tc for tc in test_cases 
                if tc.process_id and tc.process_id.strip()
            ]
            
            if not queued_test_cases:
                self.console.print("❌ No test cases requiring updates found in CSV file", style="red")
                self.console.print("   (Looking for tests with process_ids and result status: empty, unknown, or queued)", style="dim")
                return {
                    "success": False,
                    "error": "No updateable test cases found",
                    "total_tests": len(test_cases),
                    "updated": 0
                }
            
            self.console.print(f"✅ CSV file loaded: {len(test_cases)} total test cases, {len(queued_test_cases)} requiring updates")
                
            # Display update configuration
            config_table = Table()
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="white")
            config_table.add_row("CSV File", str(csv_file))
            config_table.add_row("Total Test Cases", str(len(test_cases)))
            config_table.add_row("Queued Test Cases", str(len(queued_test_cases)))
            config_table.add_row("Include Full Response", "Yes" if include_full_response else "No")
            
            self.console.print(Panel(config_table, title="📊 Update Configuration"))
            
            results = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description} ({task.completed}/{task.total})"),
                BarColumn(),
                TaskProgressColumn(text_format="[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                task = progress.add_task("Querying results", total=len(queued_test_cases))
                
                for test_case in queued_test_cases:
                    try:
                        # only query for test cases that do not have results
                        if (test_case.result is None or test_case.result.strip().lower() in {"", None, "unknown", "queued"}):
                            
                            process_final_outcome = await self.cosmos_helper.get_final_outcome(test_case.process_id)

                            if process_final_outcome is not None:
                                self.logger.info(f"Process completed for process_id: {test_case.process_id}, success: {process_final_outcome['success']}")

                                # test succeed if final outcome of process was not successful
                                test_result = "failed" if process_final_outcome["success"] else "passed"
                                error_reason = extract_error_reason(process_final_outcome["error_message"] or "")

                                # Update the test case
                                self.test_manager.update_test_result(
                                    row_id=test_case.row_id,
                                    process_id=test_case.process_id,
                                    blob_path=test_case.blob_path or "",
                                    result=test_result,
                                    reason=error_reason,
                                    full_response=process_final_outcome["error_message"] or ""
                                )
                                
                                results.append({
                                    "row_id": test_case.row_id,
                                    "process_id": test_case.process_id,
                                    "test_result": test_result,
                                    "error_reason": error_reason,
                                    "found_in_cosmos": True
                                })
                            else:
                                # Process not found in Cosmos DB yet
                                results.append({
                                    "row_id": test_case.row_id,
                                    "process_id": test_case.process_id,
                                    "test_result": "pending",
                                    "error_reason": "Not found in results / unfinished",
                                    "found_in_cosmos": False
                                })
                        else:
                            # include the previously completed test in the results for summary
                            results.append({
                                "row_id": test_case.row_id,
                                "process_id": test_case.process_id,
                                "test_result": test_case.result,
                                "error_reason": test_case.reason,
                                "found_in_cosmos": True
                            })
                            
                    except Exception as e:
                        self.logger.error(f"Error querying process_id {test_case.process_id}: {e}")
                        results.append({
                            "row_id": test_case.row_id,
                            "process_id": test_case.process_id,
                            "test_result": "error",
                            "error_reason": f"Query error: {str(e)}",
                            "found_in_cosmos": False
                        })
                    
                    progress.advance(task, 1)
            
            # Save updated CSV
            self.test_manager.save_updated_csv(output_path=csv_file, include_full_response=include_full_response)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Generate summary
            summary = self._generate_summary(results, test_cases, total_time=elapsed_time)
            
            # Display results
            self._display_results(summary)
            
            return summary
            
        except Exception as e:
            error_msg = f"Update failed: {e}"
            self.console.print(f"❌ {error_msg}", style="red")
            return {
                "success": False,
                "error": error_msg,
                "total_tests": 0,
                "updated": 0,
                "errors": 1
            }
    
    def _generate_summary(self, results: List[Dict[str, Any]], test_cases: List[TestCase], total_time: float) -> Dict[str, Any]:
        """Generate update results summary"""
        found_in_cosmos = sum(1 for r in results if r.get("found_in_cosmos", False))
        passed = sum(1 for r in results if r.get("test_result") == "passed")
        failed = sum(1 for r in results if r.get("test_result") == "failed")
        pending = sum(1 for r in results if r.get("test_result") == "pending")
        errors = sum(1 for r in results if r.get("test_result") == "error")
        
        # Get current queue message count
        queue_message_count = self.queue_helper.get_message_count()
        
        # Format total time
        total_minutes = int(total_time // 60)
        if total_minutes >= 60:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            total_time_formatted = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:
            total_time_formatted = f"{total_minutes}m"
        
        return {
            "success": True,
            "total_tests": len(test_cases),
            "queued_tests": len(results),
            "found_in_cosmos": found_in_cosmos,
            "passed": passed,
            "failed": failed,
            "pending": pending,
            "errors": errors,
            "completion_rate": f"{(found_in_cosmos / len(results) * 100):.1f}%" if results else "0%",
            "queue_message_count": queue_message_count,
            "total_execution_time": total_time_formatted,
            "results": results,
            "csv_file": str(self.test_manager.csv_file_path),
            "timestamp": datetime.now().isoformat()
        }
    
    def _display_results(self, summary: Dict[str, Any]) -> None:
        """Display update results in a formatted table"""
        results_table = Table()
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="white")
        
        results_table.add_row("Total Tests in CSV", str(summary["total_tests"]))
        results_table.add_row("Queued Tests Found", str(summary["queued_tests"]))
        results_table.add_row("Results Found in Cosmos", f"[green]{summary['found_in_cosmos']}[/green]")
        results_table.add_row("Completion Rate", summary["completion_rate"])
        results_table.add_row("Passed", f"[green]{summary['passed']}[/green]")
        results_table.add_row("Failed", f"[red]{summary['failed']}[/red]")
        results_table.add_row("Pending", f"[yellow]{summary['pending']}[/yellow]")
        results_table.add_row("Errors", f"[red]{summary['errors']}[/red]")
        
        # Display queue message count with appropriate styling
        queue_count = summary["queue_message_count"]
        if queue_count >= 0:
            queue_display = f"[cyan]{queue_count}[/cyan]" if queue_count > 0 else f"[green]{queue_count}[/green]"
        else:
            queue_display = "[red]Error[/red]"
        results_table.add_row("Current Queue Messages", queue_display)
        
        results_table.add_row("Update Time", summary["total_execution_time"])
        
        self.console.print(Panel(results_table, title="📊 Update Results"))
        self.console.print(f"✅ Results updated in: {summary['csv_file']}")
        
        if summary["pending"] > 0:
            self.console.print(f"⚠️  {summary['pending']} tests are still pending. Run this script again later to check for completion.", style="yellow")


@click.command()
@click.option('--csv-file', required=True, help='Path to CSV file containing test cases with process_ids')
@click.option('--include-full-response', is_flag=True, help='Include full error response in CSV results')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def main(csv_file: str, include_full_response: bool, debug: bool):
    """Update CSV file with final test results from Cosmos DB"""
    asyncio.run(run_async_main(csv_file, include_full_response, debug))


async def run_async_main(csv_file: str, include_full_response: bool, debug: bool):
    """Async main function for updating batch results"""
    updater = BatchResultsUpdater()
    result = await updater.update_results(csv_file, include_full_response, debug)
    
    # Exit with appropriate code
    if result.get("success", False):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()