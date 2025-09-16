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


def setup_environment():
    """Set up the RAI testing environment"""
    console = Console()
    console.print(Panel("[bold blue]RAI Testing Framework Setup[/bold blue]", expand=False))
    
    # Check Python version
    if sys.version_info < (3, 8):
        console.print("[red]❌ Python 3.8 or higher is required[/red]")
        return False
    
    console.print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check environment variables
    storage_account = os.getenv("STORAGE_ACCOUNT_NAME")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not storage_account and not connection_string:
        console.print("[yellow]⚠️  Azure Storage configuration not found[/yellow]")
        console.print("Please set one of the following environment variables:")
        console.print("  • STORAGE_ACCOUNT_NAME (recommended for production)")
        console.print("  • AZURE_STORAGE_CONNECTION_STRING (for development)")
    elif storage_account:
        console.print(f"✅ Storage account configured: {storage_account}")
    else:
        console.print("✅ Connection string configured")
    
    # Check required directories
    directories = ["results", "temp_test_files"]
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
    
    console.print("\\n[bold green]Setup complete![/bold green]")
    console.print("\\nNext steps:")
    console.print("1. Set Azure Storage environment variables:")
    console.print("   export STORAGE_ACCOUNT_NAME=your_storage_account")
    console.print("   # OR")
    console.print("   export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpoints...'")
    console.print("2. Ensure you're authenticated with Azure (az login)")
    console.print("3. Install dependencies: pip install -r requirements.txt")
    console.print("4. Run tests: python run_rai_tests.py")
    
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
