from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple, List, Optional, Any
from pykeepass import PyKeePass
import shutil

@dataclass
class DiffEntry:
    """Represents a single difference entry."""
    diff_id: str
    title: str
    path1: str
    path2: Optional[str]
    username: Optional[str]
    changes: Optional[List[str]]
    diff_type: str  # 'moved', 'db1_only', 'db2_only', 'modified'
    mtime1: Optional[datetime] = None  # Last modification time in db1
    mtime2: Optional[datetime] = None  # Last modification time in db2

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.diff_type == "moved":
            return f"[{self.diff_id}] moved: {self.title} ({self.username}) from {self.path1} to {self.path2}"
        elif self.diff_type == "db1_only":
            return f"[{self.diff_id}] only in db1: {self.title} ({self.username}) at {self.path1}"
        elif self.diff_type == "db2_only":
            return f"[{self.diff_id}] only in db2: {self.title} ({self.username}) at {self.path2}"
        else:  # modified
            return f"[{self.diff_id}] modified: {self.title} ({self.username}) at {self.path1}"

class KeePassDiffer:
    """Main class for comparing KeePass databases."""
    
    def __init__(self, db1_path: str, db2_path: str, check_trash: bool = False):
        self.db1_path = db1_path
        self.db2_path = db2_path
        self.db1: Optional[PyKeePass] = None
        self.db2: Optional[PyKeePass] = None
        self._results: Optional[List[DiffEntry]] = None
        self.check_trash = check_trash
    
    def create_backups(self) -> Tuple[str, str]:
        """Create backups of both databases with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H_%M")
        db1_backup = f"{self.db1_path}.backup_{timestamp}"
        db2_backup = f"{self.db2_path}.backup_{timestamp}"
        
        shutil.copy2(self.db1_path, db1_backup)
        shutil.copy2(self.db2_path, db2_backup)
        
        return db1_backup, db2_backup
    
    def get_diff_by_id(self, diff_id: str) -> Optional[DiffEntry]:
        """Get a difference entry by its ID."""
        if not self._results:
            return None
        return next((diff for diff in self._results if diff.diff_id == diff_id), None)

    def load_databases(self, password1: str, password2: str) -> None:
        """Load both KeePass databases with provided passwords."""
        try:
            self.db1 = PyKeePass(self.db1_path, password=password1)
            self.db2 = PyKeePass(self.db2_path, password=password2)
        except Exception as e:
            raise ValueError(f"Error opening database: {e}")

    def _get_entry_dict(self, db: PyKeePass) -> Dict[Tuple[str, str], Dict]:
        """Convert database entries to a dictionary format for comparison."""
        entries = {}
        recycle_bin = db.find_groups(name='Recycle Bin', first=True)
        
        for entry in db.entries:
            # Skip entries in Recycle Bin if check_trash is False
            if not self.check_trash and recycle_bin:
                entry_path = '/'.join(entry.group.path)
                recycle_path = '/'.join(recycle_bin.path)
                if entry_path.startswith(recycle_path):
                    continue
                
            # Use title and username as unique identifier
            key = (entry.title, entry.username or '')
            
            # Convert path from list to string
            path = '/'.join(entry.group.path) if entry.group.path else '/'
            
            entries[key] = {
                'title': entry.title,
                'username': entry.username,
                'password': entry.password,
                'path': path,
                'url': entry.url,
                'notes': entry.notes,
                'tags': entry.tags,
                'icon': entry.icon,
                'custom_properties': {k: v for k, v in entry.custom_properties.items()},
                'mtime': entry.mtime  # Add last modification time
            }
        return entries

    def compare(self) -> List[DiffEntry]:
        """Compare the databases and return structured results."""
        if not self.db1 or not self.db2:
            raise ValueError("Databases must be loaded before comparison")

        db1_entries = self._get_entry_dict(self.db1)
        db2_entries = self._get_entry_dict(self.db2)
        
        # Find all unique titles across both databases
        all_keys = set(db1_entries.keys()) | set(db2_entries.keys())
        
        results: List[DiffEntry] = []
        diff_id = 1
        
        # Track moved entries
        moved_entries = []
        
        # First, find moved entries (same title and content but different paths)
        for key in all_keys:
            entry1 = db1_entries.get(key)
            entry2 = db2_entries.get(key)
            
            if entry1 and entry2:
                # Check if paths are different but content is same
                if entry1['path'] != entry2['path']:
                    # Check if other attributes match
                    content_matches = (
                        entry1['password'] == entry2['password'] and
                        entry1['url'] == entry2['url'] and
                        entry1['notes'] == entry2['notes'] and
                        entry1['custom_properties'] == entry2['custom_properties']
                    )
                    
                    if content_matches:
                        moved_entries.append(key)
                        results.append(DiffEntry(
                            diff_id=f"M{diff_id:04d}",
                            title=entry1['title'],
                            path1=entry1['path'],
                            path2=entry2['path'],
                            username=entry1['username'],
                            changes=None,
                            diff_type='moved',
                            mtime1=entry1['mtime'],
                            mtime2=entry2['mtime']
                        ))
                        diff_id += 1
        
        # Then process remaining entries
        for key in all_keys:
            # Skip entries we already identified as moved
            if key in moved_entries:
                continue
                
            entry1 = db1_entries.get(key)
            entry2 = db2_entries.get(key)
            
            if entry1 and not entry2:
                # Entry only in first database
                results.append(DiffEntry(
                    diff_id=f"1{diff_id:04d}",
                    title=entry1['title'],
                    path1=entry1['path'],
                    path2=None,
                    username=entry1['username'],
                    changes=None,
                    diff_type='db1_only',
                    mtime1=entry1['mtime']
                ))
                diff_id += 1
            elif entry2 and not entry1:
                # Entry only in second database
                results.append(DiffEntry(
                    diff_id=f"2{diff_id:04d}",
                    title=entry2['title'],
                    path1=None,
                    path2=entry2['path'],
                    username=entry2['username'],
                    changes=None,
                    diff_type='db2_only',
                    mtime2=entry2['mtime']
                ))
                diff_id += 1
            elif entry1 and entry2:
                # Entry exists in both, check for modifications
                changes = []
                if entry1['password'] != entry2['password']:
                    changes.append('password')
                if entry1['url'] != entry2['url']:
                    changes.append('url')
                if entry1['notes'] != entry2['notes']:
                    changes.append('notes')
                if entry1['custom_properties'] != entry2['custom_properties']:
                    changes.append('custom fields')
                
                if changes:
                    results.append(DiffEntry(
                        diff_id=f"D{diff_id:04d}",
                        title=entry1['title'],
                        path1=entry1['path'],
                        path2=entry2['path'],
                        username=entry1['username'],
                        changes=changes,
                        diff_type='modified',
                        mtime1=entry1['mtime'],
                        mtime2=entry2['mtime']
                    ))
                    diff_id += 1
        
        self._results = results
        return results

    def _get_entry_by_path_and_title(self, db: PyKeePass, path: str, title: str) -> Optional[Any]:
        """Find an entry by its path and title."""
        group = db.find_groups(path=path.split('/'), first=True)
        if not group:
            return None
        return db.find_entries(title=title, group=group, first=True)

    def handle_copy_entry(self, diff_entry: DiffEntry, target_db: str) -> None:
        """Handle copying an entry from one database to another."""
        # Determine source and target databases
        source_db = self.db1 if target_db == 'db2' else self.db2
        target_db_obj = self.db2 if target_db == 'db2' else self.db1
        
        # Get the source path
        source_path = diff_entry.path1 if diff_entry.diff_type == 'db1_only' else diff_entry.path2
        
        # Find the source entry using path and title
        source_entry = self._get_entry_by_path_and_title(source_db, source_path, diff_entry.title)
        if not source_entry:
            raise ValueError(f"Source entry not found at path {source_path}: {diff_entry.title}")
        
        # Get the target path
        target_path = diff_entry.path1 if diff_entry.diff_type == 'db1_only' else diff_entry.path2
        
        # Check if an identical entry already exists in the target path
        target_entry = self._get_entry_by_path_and_title(target_db_obj, target_path, diff_entry.title)
        if target_entry:
            # If entry exists, check if username matches
            # If the username match (and title and path as well)
            # It means that something wrong happened, as we want copy entry somewhere, 
            # where it's not exist
            # So we will stop and Raise Exception
            if target_entry.username == source_entry.username:
                raise ValueError(f"Entry with same title and username already exists at target path {target_path}")
        
        # Create path if it doesn't exist
        self._ensure_group_path(target_db_obj, target_path)
        
        # Find target group
        target_group = target_db_obj.find_groups(path=target_path.split('/'), first=True)
        if not target_group:
            raise ValueError(f"Could not find or create target group: {target_path}")
        
        # Create new entry in target database
        target_db_obj.add_entry(
            destination_group=target_group,
            title=source_entry.title,
            username=source_entry.username,
            password=source_entry.password,
            url=source_entry.url,
            notes=source_entry.notes,
            tags=source_entry.tags,
            icon=source_entry.icon
        )
        
        # Copy custom properties
        new_entry = self._get_entry_by_path_and_title(target_db_obj, target_path, source_entry.title)
        for key, value in source_entry.custom_properties.items():
            new_entry.set_custom_property(key, value)
        
        # Save the changes
        target_db_obj.save()

    def handle_modified_entry(self, diff_entry: DiffEntry, target_db: str) -> None:
        """Handle a modified entry by backing up the old version to Recycle Bin and updating with new values.
        
        Args:
            diff_entry: The difference entry to handle
            target_db: Which database to update ('db1' or 'db2')
        """
        # Get source and target databases
        source_db = self.db1 if target_db == 'db2' else self.db2
        target_db = self.db2 if target_db == 'db2' else self.db1
        
        # Find the entries in both databases
        source_entry = source_db.find_entries(title=diff_entry.title, username=diff_entry.username, first=True)
        target_entry = target_db.find_entries(title=diff_entry.title, username=diff_entry.username, first=True)
        
        if not source_entry or not target_entry:
            raise ValueError("Could not find entries in both databases")
            
        # First move the target entry to Recycle Bin
        target_db.trash_entry(target_entry)
        
        # Update the target entry with values from source entry
        target_entry.title = source_entry.title
        target_entry.username = source_entry.username
        target_entry.password = source_entry.password
        target_entry.url = source_entry.url
        target_entry.notes = source_entry.notes
        target_entry.tags = source_entry.tags
        
        # Move the entry to the correct group if paths are different
        if diff_entry.path1 != diff_entry.path2:
            # Get or create the target group
            group_path = diff_entry.path1 if target_db == self.db1 else diff_entry.path2
            if group_path:
                group_parts = group_path.split('/')
                current_group = target_db.root_group
                
                # Create groups if they don't exist
                for group_name in group_parts:
                    if not group_name:  # Skip empty parts
                        continue
                    next_group = target_db.find_groups(group=current_group, name=group_name, first=True)
                    if not next_group:
                        next_group = target_db.add_group(current_group, group_name)
                    current_group = next_group
                
                # Move entry to the correct group
                target_db.move_entry(target_entry, current_group)
        
        # Save the changes
        target_db.save()

    def handle_moved_entry(self, diff_entry: DiffEntry, target_db: str) -> None:
        """Handle a moved entry by moving it to the correct group, with Recycle Bin backup.
        
        Args:
            diff_entry: The difference entry to handle
            target_db: Which database to update ('db1' or 'db2')
        """
        # Get the target database
        db = self.db2 if target_db == 'db2' else self.db1
        
        # Find the entry in the database
        entry = db.find_entries(title=diff_entry.title, username=diff_entry.username, first=True)
        if not entry:
            raise ValueError(f"Could not find entry '{diff_entry.title}' in target database")
        
        # First move the entry to Recycle Bin as backup
        db.trash_entry(entry)
        
        # Get the target path based on which database we're updating
        target_path = diff_entry.path2 if target_db == 'db1' else diff_entry.path1
        
        if target_path:
            # Split the path into group names
            group_parts = target_path.split('/')
            current_group = db.root_group
            
            # Create groups if they don't exist
            for group_name in group_parts:
                if not group_name:  # Skip empty parts
                    continue
                next_group = db.find_groups(group=current_group, name=group_name, first=True)
                if not next_group:
                    next_group = db.add_group(current_group, group_name)
                current_group = next_group
            
            # Move entry to the target group
            db.move_entry(entry, current_group)
        
        # Save the changes
        db.save()

    def _ensure_group_path(self, db: PyKeePass, path: str) -> None:
        """Ensure a group path exists in the database, creating groups as needed."""
        if not path or path == '/':
            return
            
        current_group = db.root_group
        path_parts = [p for p in path.split('/') if p]
        
        for part in path_parts:
            next_group = db.find_groups(group=current_group, name=part, first=True)
            if not next_group:
                next_group = db.add_group(current_group, part)
            current_group = next_group
