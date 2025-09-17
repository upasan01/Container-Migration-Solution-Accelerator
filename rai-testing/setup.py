#!/usr/bin/env python3
"""
Setup script for RAI Testing Framework

This script helps set up the environment and validates the configuration.
Run this before executing RAI tests for the first time.
"""

import os
import sys
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel


#!/usr/bin/env python3
"""
Setup script for RAI Testing Framework

This script helps set up the environment and validates the configuration.
Run this before executing RAI tests for the first time.
"""

import os
import sys
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel


def check_azure_storage_config(console):
    """Check Azure Storage configuration and return status"""
    storage_account = os.getenv("STORAGE_ACCOUNT_NAME")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not storage_account and not connection_string:
        console.print("[yellow]⚠️  Azure Storage configuration not found[/yellow]")
        return False
    elif storage_account:
        console.print(f"✅ Storage account configured: {storage_account}")
        return True
    else:
        console.print("✅ Connection string configured")
        return True


def check_cosmos_db_config(console):
    """Check Cosmos DB configuration and return status"""
    cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    cosmos_key = os.getenv("COSMOS_DB_KEY")
    cosmos_db_name = os.getenv("RAI_COSMOS_DB_NAME", "migration_db")
    cosmos_container_name = os.getenv("RAI_COSMOS_CONTAINER_NAME", "agent_telemetry")
    
    if not cosmos_endpoint or not cosmos_key:
        console.print("[yellow]⚠️  Cosmos DB configuration not found[/yellow]")
        console.print("Required environment variables:")
        console.print("  • COSMOS_DB_ENDPOINT")
        console.print("  • COSMOS_DB_KEY")
        return False
    else:
        console.print(f"✅ Cosmos DB endpoint configured: {cosmos_endpoint}")
        console.print(f"✅ Database: {cosmos_db_name}, Container: {cosmos_container_name}")
        return True


def setup_environment():
    """Set up the RAI testing environment"""
    console = Console()
    console.print(Panel("[bold blue]RAI Testing Framework Setup[/bold blue]", expand=False))
    
    # Check Python version
    if sys.version_info < (3, 8):
        console.print("[red]❌ Python 3.8 or higher is required[/red]")
        return False
    
    console.print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check configurations
    storage_configured = check_azure_storage_config(console)
    cosmos_configured = check_cosmos_db_config(console)
    
    # Check required directories
    directories = ["temp_test_files"]
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            console.print(f"✅ Created directory: {dir_name}")
    
    # Check Azure CLI (optional but recommended)
    if shutil.which("az"):
        console.print("✅ Azure CLI found")
    else:
        console.print("[yellow]⚠️  Azure CLI not found (optional but recommended)[/yellow]")
    
    # Check dependencies
    try:
        import azure.storage.blob
        import azure.cosmos
        import rich
        console.print("✅ Required Python packages found")
    except ImportError as e:
        console.print(f"[yellow]⚠️  Missing Python package: {str(e).split()[-1]}[/yellow]")
    
    console.print("\n[bold green]Setup complete![/bold green]")
    
    # Show next steps based on configuration status
    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    
    if not storage_configured:
        console.print("1. [yellow]Set Azure Storage environment variables:[/yellow]")
        console.print("   PowerShell: $env:STORAGE_ACCOUNT_NAME=\"your_storage_account\"")
        console.print("   Bash: export STORAGE_ACCOUNT_NAME=\"your_storage_account\"")
        console.print("   [dim]# OR use connection string for development[/dim]")
        console.print("   PowerShell: $env:AZURE_STORAGE_CONNECTION_STRING=\"DefaultEndpoints...\"")
        console.print("   Bash: export AZURE_STORAGE_CONNECTION_STRING=\"DefaultEndpoints...\"")
    
    if not cosmos_configured:
        console.print("2. [yellow]Set Cosmos DB environment variables:[/yellow]")
        console.print("   PowerShell: $env:COSMOS_DB_ENDPOINT=\"https://your-cosmos.documents.azure.com:443/\"")
        console.print("   PowerShell: $env:COSMOS_DB_KEY=\"your-cosmos-key\"")
        console.print("   Bash: export COSMOS_DB_ENDPOINT=\"https://your-cosmos.documents.azure.com:443/\"")
        console.print("   Bash: export COSMOS_DB_KEY=\"your-cosmos-key\"")
    
    step_num = 3 if not storage_configured or not cosmos_configured else 1
    
    console.print(f"{step_num}. [cyan]Ensure you're authenticated with Azure:[/cyan]")
    console.print("   az login")
    
    console.print(f"{step_num + 1}. [cyan]Install dependencies (if not already done):[/cyan]")
    console.print("   pip install -r requirements.txt")
    
    console.print(f"{step_num + 2}. [cyan]Choose how to run tests:[/cyan]")
    console.print("   [bold]Single Test:[/bold]")
    console.print("     python run_single_test.py \"Your test content here\"")
    console.print("   [bold]CSV Batch Tests:[/bold]")
    console.print("     python run_batch_tests.py --csv-file your_test_cases.csv")
    console.print("   [bold]Interactive CSV Selection:[/bold]")
    console.print("     python run_batch_tests.py")
    
    # Show validation status
    if storage_configured and cosmos_configured:
        console.print("\n[bold green]✅ All configurations are ready![/bold green]")
        console.print("You can proceed with running tests immediately.")
    else:
        console.print("\n[bold yellow]⚠️  Configuration incomplete[/bold yellow]")
        console.print("Please complete the configuration steps above before running tests.")
    
    return True


@click.command()
def main():
    """Set up the RAI testing framework environment"""
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        if setup_environment():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        console = Console()
        console.print(f"[red]Setup failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
