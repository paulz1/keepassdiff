#!/usr/bin/env python3

import sys
import getpass
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Tuple, List, Optional, Any
from pykeepass import PyKeePass
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from keepass_diff_class.keepass_classes import DiffEntry, KeePassDiffer

console = Console()

def display_cli_results(results: List[DiffEntry], db1_path: str, db2_path: str) -> None:
    """Display results in CLI format."""
    if not results:
        console.print("[green]No differences found between the databases.[/green]")
        return

    # Group results by type
    moved = [r for r in results if r.diff_type == 'moved']
    db1_only = [r for r in results if r.diff_type == 'db1_only']
    db2_only = [r for r in results if r.diff_type == 'db2_only']
    modified = [r for r in results if r.diff_type == 'modified']

    # Display moved entries
    if moved:
        console.print(f"\n[blue]Moved entries:[/blue]")
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Username")
        table.add_column(f"Path in {db1_path}")
        table.add_column(f"Path in {db2_path}")
        for entry in moved:
            table.add_row(
                entry.diff_id,
                entry.title,
                entry.username or '',
                entry.path1,
                entry.path2 or ''
            )
        console.print(table)

    # Display entries only in db1
    if db1_only:
        console.print(f"\n[yellow]Entries existing only in[/yellow] [blue]{db1_path}[/blue]:")
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Path")
        table.add_column("Title")
        for entry in db1_only:
            table.add_row(
                entry.diff_id,
                entry.path1,
                entry.title
            )
        console.print(table)

    # Display entries only in db2
    if db2_only:
        console.print(f"\n[yellow]Entries existing only in[/yellow] [blue]{db2_path}[/blue]:")
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Path")
        table.add_column("Title")
        for entry in db2_only:
            table.add_row(
                entry.diff_id,
                entry.path2 or '',
                entry.title
            )
        console.print(table)

    # Display modified entries
    if modified:
        console.print(f"\n[yellow]Entries different between databases:[/yellow]")
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Path")
        table.add_column("Title")
        table.add_column("Changes")
        for entry in modified:
            table.add_row(
                entry.diff_id,
                entry.path1,
                entry.title,
                ", ".join(entry.changes or []),
            )
        console.print(table)

def cli_get_passwords(db1_path: str, db2_path: str) -> Tuple[str, str]:
    """Get passwords from command line."""
    password1 = getpass.getpass(f"Enter password for {db1_path}: ")
    
    if get_yes_no_input("Use the same password for the second database?"):
        password2 = password1
    else:
        password2 = getpass.getpass(f"Enter password for {db2_path}: ")

    return password1, password2

def cli_get_keyfiles(db1_path: str, db2_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Get key files from command line."""
    if not get_yes_no_input("Do you need a key file to open the databases?"):
        return None, None
    
    keyfile1 = input(f"Enter key file path for {db1_path}: ").strip()
    if not keyfile1:
        keyfile1 = None
    else:
        # Validate key file exists
        if not Path(keyfile1).exists():
            console.print(f"[red]Warning: Key file '{keyfile1}' does not exist.[/red]")
            if not get_yes_no_input("Continue anyway?"):
                keyfile1 = None
    
    if get_yes_no_input("Use the same key file for the second database?"):
        keyfile2 = keyfile1
    else:
        keyfile2 = input(f"Enter key file path for {db2_path}: ").strip()
        if not keyfile2:
            keyfile2 = None
        else:
            # Validate key file exists
            if not Path(keyfile2).exists():
                console.print(f"[red]Warning: Key file '{keyfile2}' does not exist.[/red]")
                if not get_yes_no_input("Continue anyway?"):
                    keyfile2 = None
    
    return keyfile1, keyfile2

def get_yes_no_input(prompt: str) -> bool:
    """Get a yes/no response from the user."""
    while True:
        response = input(prompt + " (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        console.print("[red]Please answer 'y' or 'n'[/red]")

def handle_batch_operations(differ: KeePassDiffer, batch_type: str, target_db: str) -> None:
    """Handle batch operations for moved entries or entries existing in only one database.
    
    Args:
        differ: The KeePassDiffer instance
        batch_type: Type of batch operation ('moved', 'db1_only', or 'db2_only')
        target_db: Which database to update ('db1' or 'db2')
    """
    if not differ._results:
        console.print("[yellow]No differences found to process.[/yellow]")
        return

    # Filter entries based on batch_type
    entries_to_process = [r for r in differ._results if r.diff_type == batch_type]
    
    if not entries_to_process:
        console.print(f"[yellow]No {batch_type} entries found to process.[/yellow]")
        return

    # Show summary of what will be processed
    console.print(f"\n[blue]The following entries will be processed:[/blue]")
    for entry in entries_to_process:
        if batch_type == 'moved':
            source_path = entry.path1 if target_db == 'db1' else entry.path2
            target_path = entry.path2 if target_db == 'db1' else entry.path1
            console.print(f"- {entry.title} will be moved from {source_path} to {target_path}")
        else:  # db1_only or db2_only
            source_path = entry.path1 if entry.diff_type == 'db1_only' else entry.path2
            console.print(f"- {entry.title} will be copied from {source_path}")

    # Ask for confirmation
    if not get_yes_no_input("\nDo you want to proceed with these changes?"):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    # Process each entry
    success_count = 0
    error_count = 0
    
    for entry in entries_to_process:
        try:
            if batch_type == 'moved':
                differ.handle_moved_entry(entry, target_db)
            else:  # db1_only or db2_only
                differ.handle_copy_entry(entry, target_db)
            success_count += 1
        except Exception as e:
            console.print(f"[red]Error processing entry '{entry.title}': {e}[/red]")
            error_count += 1

    # Show results
    console.print(f"\n[green]Successfully processed {success_count} entries[/green]")
    if error_count > 0:
        console.print(f"[red]Failed to process {error_count} entries[/red]")

    # Reload databases to get fresh state
    differ.load_databases(differ.db1.password, differ.db2.password, differ._keyfile1, differ._keyfile2)
    # Get fresh comparison
    differ._results = differ.compare()
    # Show updated results
    console.print("\n[blue]Updated comparison:[/blue]")
    display_cli_results(differ._results, differ.db1_path, differ.db2_path)

def cli_edit_prompt(differ: KeePassDiffer) -> None:
    """Handle the interactive edit prompt."""
    while True:
        try:
            # Show available options
            console.print("\n[blue]Available actions:[/blue]")
            console.print("0) Re-run comparison and show results")
            console.print("1) Process individual entry by ID")
            console.print("2) Batch process moved entries")
            console.print("3) Batch process entries existing in only one database")
            console.print("4) Show entry details by ID")
            console.print("n) Exit")

            choice = Prompt.ask("\nSelect an action", choices=["0", "1", "2", "3", "4", "n"], default="1")

            if choice.lower() == 'n':
                break

            if choice == "0":
                # Re-run comparison and show results
                console.print("\n[blue]Re-running comparison...[/blue]")
                # Get fresh comparison
                differ._results = differ.compare()
                # Show updated results
                display_cli_results(differ._results, differ.db1_path, differ.db2_path)

            elif choice == "4":
                # Show entry details
                response = input("Enter difference ID to show: ").strip()
                diff_entry = differ.get_diff_by_id(response)
                if not diff_entry:
                    console.print(f"[red]No difference found with ID: {response}[/red]")
                    continue
                
                # Show entry details
                console.print("\n[blue]Entry details:[/blue]")
                console.print(f"Type: {diff_entry.diff_type}")
                console.print(f"Title: {diff_entry.title}")
                
                # Get entries from both databases
                entry1 = differ.db1.find_entries(title=diff_entry.title, username=diff_entry.username, first=True) if diff_entry.path1 else None
                entry2 = differ.db2.find_entries(title=diff_entry.title, username=diff_entry.username, first=True) if diff_entry.path2 else None
                
                # Ask about password display
                show_password = get_yes_no_input("\nWould you like to see the passwords in clear text?")
                
                # Create a table for comparison
                table = Table(show_header=True, title="Entry Details")
                table.add_column("Parameter")
                if entry1:
                    table.add_column(differ.db1_path)
                if entry2:
                    table.add_column(differ.db2_path)
                
                # Add entry details to table
                params_to_compare = []
                if entry1 or entry2:
                    params_to_compare = [
                        ("Title", entry1.title if entry1 else None, entry2.title if entry2 else None),
                        ("Username", entry1.username if entry1 else None, entry2.username if entry2 else None),
                        ("URL", entry1.url if entry1 else None, entry2.url if entry2 else None),
                        ("Notes", entry1.notes if entry1 else None, entry2.notes if entry2 else None),
                        ("Path", diff_entry.path1, diff_entry.path2),
                        ("Tags", ', '.join(entry1.tags or []) if entry1 else None, 
                               ', '.join(entry2.tags or []) if entry2 else None),
                        ("Last Modified", str(entry1.mtime) if entry1 else None, 
                                       str(entry2.mtime) if entry2 else None)
                    ]
                    
                    # Add each parameter to the table
                    for param, val1, val2 in params_to_compare:
                        if entry1 and entry2:
                            style1 = "[red]" if val1 != val2 else ""
                            style2 = "[red]" if val1 != val2 else ""
                            display_val1 = val1 if val1 else ""
                            display_val2 = val2 if val2 else ""
                            table.add_row(
                                param,
                                f"{style1}{display_val1}{style1 and '[/red]' or ''}",
                                f"{style2}{display_val2}{style2 and '[/red]' or ''}"
                            )
                        elif entry1:
                            table.add_row(param, str(val1) if val1 else "")
                        elif entry2:
                            table.add_row(param, str(val2) if val2 else "")
                    
                    # Handle password display
                    if show_password:
                        if entry1 and entry2:
                            table.add_row(
                                "Password",
                                f"[yellow]{entry1.password}[/]",
                                f"[yellow]{entry2.password}[/]"
                            )
                        elif entry1:
                            table.add_row("Password", f"[yellow]{entry1.password}[/]")
                        elif entry2:
                            table.add_row("Password", f"[yellow]{entry2.password}[/]")
                    else:
                        if entry1 and entry2:
                            passwords_match = entry1.password == entry2.password
                            table.add_row(
                                "Password",
                                "[green]<identical>[/]" if passwords_match else "[red]<different>[/]",
                                "[green]<identical>[/]" if passwords_match else "[red]<different>[/]"
                            )
                        elif entry1:
                            table.add_row("Password", "<hidden>")
                        elif entry2:
                            table.add_row("Password", "<hidden>")
                    
                    # Add custom properties
                    if entry1 and entry1.custom_properties:
                        for key, value in entry1.custom_properties.items():
                            if entry2:
                                val2 = entry2.custom_properties.get(key)
                                style = "[red]" if value != val2 else ""
                                table.add_row(
                                    f"Custom: {key}",
                                    f"{style}{value}{style and '[/red]' or ''}",
                                    f"{style}{val2}{style and '[/red]' or ''}" if val2 else "[red]<not set>[/red]"
                                )
                            else:
                                table.add_row(f"Custom: {key}", value)
                    
                    if entry2 and entry2.custom_properties:
                        # Add custom properties that only exist in entry2
                        if entry1:
                            for key, value in entry2.custom_properties.items():
                                if key not in (entry1.custom_properties or {}):
                                    table.add_row(
                                        f"Custom: {key}",
                                        "[red]<not set>[/red]",
                                        value
                                    )
                        else:
                            for key, value in entry2.custom_properties.items():
                                table.add_row(f"Custom: {key}", value)
                
                # Display the table
                console.print("\n")
                console.print(table)
                
                # If entry has changes, show them
                if diff_entry.changes:
                    console.print("\n[yellow]Changed fields:[/yellow]", ", ".join(diff_entry.changes))

            elif choice == "1":
                # Original individual entry processing
                response = input("Enter difference ID to edit: ").strip()
                diff_entry = differ.get_diff_by_id(response)
                if diff_entry:
                    console.print("\n[blue]Selected difference:[/blue]")
                    if diff_entry.diff_type == 'moved':
                        console.print(f"Type: Moved entry")
                        console.print(f"Title: {diff_entry.title}")
                        console.print(f"Path in {differ.db1_path}: {diff_entry.path1}")
                        console.print(f"Path in {differ.db2_path}: {diff_entry.path2}")
                        
                        # Ask which database to modify
                        console.print("\nWhich database would you like to modify?")
                        console.print(f"1) {differ.db1_path} (move entry to match second database)")
                        console.print(f"2) {differ.db2_path} (move entry to match first database)")
                        console.print("r) Return to edit prompt")
                        db_choice = input("Enter 1, 2, or r: ").strip().lower()
                        
                        if db_choice == 'r':
                            continue
                        
                        if db_choice not in ['1', '2']:
                            console.print("[red]Invalid choice. Please enter 1, 2, or r.[/red]")
                            continue
                        
                        target_db = 'db1' if db_choice == '1' else 'db2'
                        source_path = diff_entry.path1 if target_db == 'db1' else diff_entry.path2
                        target_path = diff_entry.path2 if target_db == 'db1' else diff_entry.path1
                        
                        # Explain what will happen
                        db_path = differ.db1_path if target_db == 'db1' else differ.db2_path
                        console.print(f"\n[yellow]The following changes will be made in {db_path}:[/yellow]")
                        console.print(f"1. Entry '{diff_entry.title}' will be backed up to Recycle Bin")
                        console.print(f"2. Then it will be moved to: {target_path}")
                        
                        # Ask for confirmation
                        if get_yes_no_input("\nDo you want to proceed with these changes?"):
                            try:
                                differ.handle_moved_entry(diff_entry, target_db)
                                console.print("[green]Changes applied successfully![/green]")
                                # Reload databases to get fresh state
                                differ.load_databases(differ.db1.password, differ.db2.password, differ._keyfile1, differ._keyfile2)
                                # Get fresh comparison
                                differ._results = differ.compare()
                                # Show updated results
                                console.print("\n[blue]Updated comparison:[/blue]")
                                display_cli_results(differ._results, differ.db1_path, differ.db2_path)
                            except Exception as e:
                                console.print(f"[red]Error applying changes: {e}[/red]")
                        else:
                            console.print("[yellow]Operation cancelled.[/yellow]")
                            
                    elif diff_entry.diff_type in ['db1_only', 'db2_only']:
                        console.print(f"Type: Only in {differ.db1_path if diff_entry.diff_type == 'db1_only' else differ.db2_path}")
                        console.print(f"Title: {diff_entry.title}")
                        console.print(f"Path: {diff_entry.path1 or diff_entry.path2}")
                        
                        # Ask if user wants to copy the entry to the other database
                        target_db = 'db2' if diff_entry.diff_type == 'db1_only' else 'db1'
                        db_path = differ.db2_path if target_db == 'db2' else differ.db1_path
                        source_db_path = differ.db1_path if target_db == 'db2' else differ.db2_path
                        
                        console.print(f"\nWould you like to copy this entry from {source_db_path} to {db_path}?")
                        if get_yes_no_input("Proceed with copy?"):
                            try:
                                differ.handle_copy_entry(diff_entry, target_db)
                                console.print("[green]Entry copied successfully![/green]")
                                # Reload databases to get fresh state
                                differ.load_databases(differ.db1.password, differ.db2.password, differ._keyfile1, differ._keyfile2)
                                # Get fresh comparison
                                differ._results = differ.compare()
                                # Show updated results
                                console.print("\n[blue]Updated comparison:[/blue]")
                                display_cli_results(differ._results, differ.db1_path, differ.db2_path)
                            except Exception as e:
                                console.print(f"[red]Error copying entry: {e}[/red]")
                        else:
                            console.print("[yellow]Operation cancelled.[/yellow]")
                            
                    else:  # modified
                        console.print(f"Type: Modified entry")
                        
                        # Get entries from both databases for comparison
                        # Find entries by title and username since that's our unique identifier
                        entry1 = differ.db1.find_entries(title=diff_entry.title, username=diff_entry.username, first=True)
                        entry2 = differ.db2.find_entries(title=diff_entry.title, username=diff_entry.username, first=True)
                        
                        if entry1 and entry2:
                            # Create side-by-side comparison table
                            table = Table(show_header=True, title="Entry Comparison")
                            table.add_column("Parameter")
                            table.add_column(differ.db1_path)
                            table.add_column(differ.db2_path)
                            
                            # Add all parameters to compare
                            params_to_compare = [
                                ("Title", entry1.title, entry2.title),
                                ("Username", entry1.username, entry2.username),
                                ("URL", entry1.url, entry2.url),
                                ("Notes", entry1.notes, entry2.notes),
                                ("Path", diff_entry.path1, diff_entry.path2 or diff_entry.path1),
                                ("Tags", ', '.join(entry1.tags or []), ', '.join(entry2.tags or []))
                            ]
                            
                            # Add each parameter to the table with color highlighting for differences
                            for param, val1, val2 in params_to_compare:
                                style1 = "[red]" if val1 != val2 else ""
                                style2 = "[red]" if val1 != val2 else ""
                                # Handle empty values properly
                                display_val1 = val1 if val1 else ""
                                display_val2 = val2 if val2 else ""
                                table.add_row(
                                    param,
                                    f"{style1}{display_val1}{style1 and '[/red]' or ''}",
                                    f"{style2}{display_val2}{style2 and '[/red]' or ''}"
                                )
                            table.add_row("Last Modified",str(entry1.mtime),str(entry2.mtime))
                            
                            # Handle password comparison separately based on ID and user choice
                            show_password = get_yes_no_input("\nWould you like to see the passwords in clear text?")
                            if show_password:
                                table.add_row(
                                    "Password",
                                    f"[yellow]{entry1.password}[/]",
                                    f"[yellow]{entry2.password}[/]"
                                )
                            else:
                                passwords_match = entry1.password == entry2.password
                                table.add_row(
                                    "Password",
                                    "[green]<identical>[/]" if passwords_match else "[red]<different>[/]",
                                    "[green]<identical>[/]" if passwords_match else "[red]<different>[/]"
                                )
                            
                            # Display the comparison table
                            console.print("\n")
                            console.print(table)
                            
                            # Show changes summary
                            if diff_entry.changes:
                                console.print("\n[yellow]Changed fields:[/yellow]", ", ".join(diff_entry.changes))
                        
                        # Ask which database to update
                        console.print(f"\nWhich database would you like to update?")
                        console.print(f"1) Update {differ.db2_path} to match {differ.db1_path}")
                        console.print(f"2) Update {differ.db1_path} to match {differ.db2_path}")
                        console.print("r) Return to edit prompt")
                        
                        db_choice = input("Enter 1, 2, or r: ").strip().lower()
                        if db_choice == 'r':
                            continue
                        
                        if db_choice not in ['1', '2']:
                            console.print("[red]Invalid choice. Please enter 1, 2, or r.[/red]")
                            continue
                        
                        target_db = 'db2' if db_choice == '1' else 'db1'
                        source_db = 'db1' if db_choice == '1' else 'db2'
                        
                        # Confirm the changes
                        db_path = differ.db2_path if target_db == 'db2' else differ.db1_path
                        source_path = differ.db1_path if source_db == 'db1' else differ.db2_path
                        console.print(f"\n[yellow]The following changes will be made in {db_path}:[/yellow]")
                        console.print(f"Entry '{diff_entry.title}' will be updated to match the version in {source_path}")
                        
                        if get_yes_no_input("\nDo you want to proceed with these changes?"):
                            try:
                                differ.handle_modified_entry(diff_entry, target_db)
                                console.print("[green]Changes applied successfully![/green]")
                                # Reload databases to get fresh state
                                differ.load_databases(differ.db1.password, differ.db2.password, differ._keyfile1, differ._keyfile2)
                                # Get fresh comparison
                                differ._results = differ.compare()
                                # Show updated results
                                console.print("\n[blue]Updated comparison:[/blue]")
                                display_cli_results(differ._results, differ.db1_path, differ.db2_path)
                            except Exception as e:
                                console.print(f"[red]Error applying changes: {e}[/red]")
                        else:
                            console.print("[yellow]Operation cancelled.[/yellow]")
            elif choice == "2":
                # Batch process moved entries
                console.print("\n[blue]Which database would you like to update?[/blue]")
                console.print(f"1) {differ.db1_path} (move entries to match second database)")
                console.print(f"2) {differ.db2_path} (move entries to match first database)")
                console.print("r) Return to main menu")
                
                db_choice = input("Enter 1, 2, or r: ").strip().lower()
                if db_choice == 'r':
                    continue
                if db_choice not in ['1', '2']:
                    console.print("[red]Invalid choice. Please enter 1, 2, or r.[/red]")
                    continue
                
                target_db = 'db1' if db_choice == '1' else 'db2'
                handle_batch_operations(differ, 'moved', target_db)
            
            elif choice == "3":
                # Batch process entries existing in only one database
                console.print("\n[blue]Which entries would you like to process?[/blue]")
                console.print(f"1) Copy entries from {differ.db1_path} to {differ.db2_path}")
                console.print(f"2) Copy entries from {differ.db2_path} to {differ.db1_path}")
                console.print("r) Return to main menu")
                
                db_choice = input("Enter 1, 2, or r: ").strip().lower()
                if db_choice == 'r':
                    continue
                if db_choice not in ['1', '2']:
                    console.print("[red]Invalid choice. Please enter 1, 2, or r.[/red]")
                    continue
                
                if db_choice == '1':
                    handle_batch_operations(differ, 'db1_only', 'db2')
                else:
                    handle_batch_operations(differ, 'db2_only', 'db1')

        except (KeyboardInterrupt, EOFError):
            break

    return 0

def main():
    parser = argparse.ArgumentParser(description='Compare two KeePass database files.')
    parser.add_argument('db1', help='First KeePass database')
    parser.add_argument('db2', help='Second KeePass database')
    parser.add_argument('--edit', action='store_true', help='Enable interactive editing mode')
    parser.add_argument('--check-trash', action='store_true', help='Include Recycle Bin in comparison')
    parser.add_argument('--batch-moved', choices=['db1', 'db2'], 
                      help='Batch process all moved entries to match the specified database')
    parser.add_argument('--batch-copy', choices=['db1', 'db2'],
                      help='Batch copy entries that exist in one database to the other. '
                           'Specify the target database to copy to.')
    parser.add_argument('--key-file', nargs='?', const='', action='append',
                      help='Key file path(s) for opening databases. Can be specified once (for both databases) or twice (once per database)')
    
    args = parser.parse_args()
    
    try:
        differ = KeePassDiffer(args.db1, args.db2, args.check_trash)
        
        if args.edit or args.batch_moved or args.batch_copy:
            # Create backups before proceeding
            db1_backup, db2_backup = differ.create_backups()
            console.print(f"[green]Created backups:[/green]")
            console.print(f"DB1 backup: {db1_backup}")
            console.print(f"DB2 backup: {db2_backup}")
    
        # Get passwords
        password1, password2 = cli_get_passwords(args.db1, args.db2)
        
        # Get key files (from command line or interactive)
        keyfile1 = None
        keyfile2 = None
        if args.key_file:
            # Handle key file arguments
            if len(args.key_file) == 1:
                # One key file for both databases
                keyfile_path = args.key_file[0].strip() if args.key_file[0] else None
                if keyfile_path:
                    if Path(keyfile_path).exists():
                        keyfile1 = keyfile_path
                        keyfile2 = keyfile_path
                    else:
                        console.print(f"[red]Warning: Key file '{keyfile_path}' does not exist.[/red]")
            elif len(args.key_file) >= 2:
                # Separate key files for each database
                keyfile_path1 = args.key_file[0].strip() if args.key_file[0] else None
                keyfile_path2 = args.key_file[1].strip() if args.key_file[1] else None
                if keyfile_path1:
                    if Path(keyfile_path1).exists():
                        keyfile1 = keyfile_path1
                    else:
                        console.print(f"[red]Warning: Key file '{keyfile_path1}' does not exist.[/red]")
                if keyfile_path2:
                    if Path(keyfile_path2).exists():
                        keyfile2 = keyfile_path2
                    else:
                        console.print(f"[red]Warning: Key file '{keyfile_path2}' does not exist.[/red]")
        else:
            # Interactive key file input if not provided via command line
            keyfile1, keyfile2 = cli_get_keyfiles(args.db1, args.db2)
    
        # Initialize and run comparison
        differ.load_databases(password1, password2, keyfile1, keyfile2)
        results = differ.compare()
    
        # Display results
        display_cli_results(results, args.db1, args.db2)
    
        # Handle batch operations if specified
        if args.batch_moved:
            handle_batch_operations(differ, 'moved', f'db{args.batch_moved[-1]}')
        elif args.batch_copy:
            target_db = f'db{args.batch_copy[-1]}'
            source_db = 'db1' if target_db == 'db2' else 'db2'
            handle_batch_operations(differ, f'{source_db}_only', target_db)
        # If edit mode is enabled, start the edit prompt
        elif args.edit:
            cli_edit_prompt(differ)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
