#!/usr/bin/env python3
"""
Centralized environment validation for RAI Testing Framework

This module provides a single function to validate Azure Storage and Cosmos DB
configuration across all RAI testing scripts.
"""

import os
from pathlib import Path
from rich.console import Console

def check_azure_storage_config(console: Console, printSuccess: bool):
    """Check Azure Storage configuration and return status"""
    storage_account = os.getenv("STORAGE_ACCOUNT_NAME")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not storage_account and not connection_string:
        console.print("[yellow]⚠️  Azure Storage configuration not found[/yellow]")
        return False
    elif storage_account:
        if printSuccess:
            console.print(f"✅ Storage account configured: {storage_account}")
        return True
    else:
        if printSuccess:
            console.print("✅ Connection string configured")
        return True


def check_cosmos_db_config(console: Console, printSuccess: bool):
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
        if printSuccess:
            console.print(f"✅ Cosmos DB endpoint configured: {cosmos_endpoint}")
            console.print(f"✅ Database: {cosmos_db_name}, Container: {cosmos_container_name}")
        return True

def validate_environment(print: bool = False) -> bool:
    """
    Validate environment configuration for RAI testing scripts.
    
    Checks both Azure Storage and Cosmos DB configuration and displays
    results to the console with rich formatting.
    
    Returns:
        bool: True if both Azure Storage and Cosmos DB are configured, False otherwise
    """
    console = Console()
    
    # Display validation header
    if (print):
        console.print("🔍 Validating environment configuration...")
    
    # Check configurations
    storage_ok = check_azure_storage_config(console, print)
    cosmos_ok = check_cosmos_db_config(console, print)
    
    # Display results and guidance
    if not storage_ok or not cosmos_ok:
        console.print("\n❌ [red]Environment configuration incomplete![/red]")
        return False
    
    if print:
        console.print("✅ Environment configuration validated\n")

    return True