# KeePassDiff

This software was almost fully developed using Windsurf (with Trial Pro access). 
The 90-95% of code was written by Windsurf, I just do some small touches
.

⚠️ **Warning**: This software is not extensively tested and should be used with understanding of potential risks. However:
- In normal mode (without --edit), the tool only reads and compares databases without any modifications
- In edit mode (--edit), the tool automatically creates backup copies of databases before making any changes

A command-line utility to compare two KeePass database files and show their differences. This tool helps you identify and manage differences between two KeePass databases, including moved entries, entries that exist in only one database, and modified entries.

## Features

- Compare two KeePass database files (.kdbx)
- Interactive editing mode with multiple operations:
  - View detailed entry information
  - Process individual entries
  - Batch process multiple entries
  - Re-run comparisons on demand
- Automatic backup creation before any modifications
- Secure password handling
- Rich display of differences with color highlighting
- Support for all entry attributes:
  - Title, username, password
  - URL, notes, tags
  - Custom fields
  - Last modification time
- Handle various types of differences:
  - Moved entries (same entry in different locations)
  - Entries existing in only one database
  - Modified entries with detailed change tracking
- Recycle bin support for safe operations

## Installation

1. Create and activate a virtual environment:
```bash
# Create a virtual environment
python3 -m venv venv

# Activate it on Linux/macOS
source venv/bin/activate

# Activate it on Windows
venv\Scripts\activate
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Comparison
```bash
python keepass_diff.py <path_to_first_db> <path_to_second_db>
```

### Interactive Editing Mode
```bash
python keepass_diff.py <path_to_first_db> <path_to_second_db> --edit
```

### Include Recycle Bin in Comparison
```bash
python keepass_diff.py <path_to_first_db> <path_to_second_db> --check-trash
```

### Batch Operations
```bash
# Move all moved entries to match db1
python keepass_diff.py <path_to_first_db> <path_to_second_db> --batch-moved db1

# Copy all entries that exist only in db1 to db2
python keepass_diff.py <path_to_first_db> <path_to_second_db> --batch-copy db2
```

## Interactive Menu Options

0. **Re-run comparison and show results**
   - Re-runs the comparison and displays fresh results
   - Useful after making changes or viewing multiple entries

1. **Process individual entry by ID**
   - Select a specific entry by its ID
   - View detailed comparison
   - Choose which database to update
   - Options for moving, copying, or updating entries

2. **Batch process moved entries**
   - Process all moved entries at once
   - Choose which database should be updated
   - Entries are moved to match the selected database's structure

3. **Batch process entries existing in only one database**
   - Copy multiple entries between databases at once
   - Choose source and target databases
   - Maintains all entry attributes including custom fields

4. **Show entry details by ID**
   - View comprehensive entry information
   - Compare entries side by side when they exist in both databases
   - Toggle password visibility
   - See all attributes including custom fields
   - Differences are highlighted in red

## Safety Features

- Automatic database backups before any modifications
- Confirmation prompts for all operations
- Recycle bin backup of modified/moved entries
- Clear display of planned changes before execution
- Error handling with detailed messages

## Requirements

- Python 3.7+
- Required Python packages:
  - pykeepass
  - rich (for colored terminal output)

## Notes

- Passwords are never displayed in clear text unless explicitly requested
- All operations maintain the integrity of custom fields and entry attributes
- The tool creates timestamped backups before any modifications
- Entries are identified using a combination of title and username
- Modified entries are backed up to the Recycle Bin before changes
