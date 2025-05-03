import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from keepass_diff_class.keepass_classes import KeePassDiffer, DiffEntry

class TestKeePassDiffer(unittest.TestCase):
    def setUp(self):
        # Create a KeePassDiffer instance with mock paths
        self.differ = KeePassDiffer(
            db1_path="test1.kdbx",
            db2_path="test2.kdbx",
            check_trash=False
        )
        
        # Create mock entries with proper group paths
        group1 = Mock(path=['Group1'])
        group2 = Mock(path=['Group2'])
        
        # Create entries with matching content but different paths
        self.entry1 = Mock(
            title="Entry",
            username="user",
            path="",  # Path is constructed from group path
            mtime=datetime(2025, 4, 11, 12, 0),
            group=group1,
            custom_properties={},
            password="password123",
            url="https://example.com",
            notes="Test notes",
            tags=["test"],
            icon="1"
        )
        self.entry2 = Mock(
            title="Entry",
            username="user",
            path="",  # Path is constructed from group path
            mtime=datetime(2025, 4, 11, 12, 0),
            group=group2,
            custom_properties={},
            password="password123",  # Same password as entry1
            url="https://example.com",  # Same URL as entry1
            notes="Test notes",  # Same notes as entry1
            tags=["test"],  # Same tags as entry1
            icon="1"  # Same icon as entry1
        )
        
        # Create mock recycle bin group
        recycle_bin = Mock(
            name='Recycle Bin',
            path=['Recycle Bin']
        )
        
        # Create mock databases with entries and recycle bin
        self.differ.db1 = Mock(
            entries=[self.entry1],
            find_groups=Mock(return_value=recycle_bin),
            recycle_bin=recycle_bin
        )
        self.differ.db2 = Mock(
            entries=[self.entry2],
            find_groups=Mock(return_value=recycle_bin),
            recycle_bin=recycle_bin
        )

    def test_get_diff_by_id(self):
        """Test retrieving a diff entry by ID"""
        # Create a sample diff entry
        test_entry = DiffEntry(
            diff_id="1",
            diff_type="moved",
            title="Entry",
            username="user",
            path1="Group1",
            path2="Group2",
            changes=["Path changed"],
            mtime1=datetime(2025, 4, 11, 12, 0),
            mtime2=datetime(2025, 4, 11, 12, 0)
        )
        self.differ._results = [test_entry]

        # Test finding existing entry
        found_entry = self.differ.get_diff_by_id("1")
        self.assertEqual(found_entry, test_entry)

        # Test with non-existent ID
        not_found = self.differ.get_diff_by_id("999")
        self.assertIsNone(not_found)

    @patch('shutil.copy2')
    def test_backup_database(self, mock_copy):
        """Test database backup functionality"""
        timestamp = datetime.now().strftime("%Y%m%d_%H_%M")
        db1_backup, db2_backup = self.differ.create_backups()
        
        self.assertTrue(mock_copy.called)
        self.assertEqual(mock_copy.call_count, 2)
        
        # Verify backup paths
        self.assertTrue(db1_backup.startswith("test1.kdbx.backup_"))
        self.assertTrue(db2_backup.startswith("test2.kdbx.backup_"))

    def test_compare_moved_entries(self):
        """Test detection of moved entries"""
        # Compare databases
        self.differ._results = self.differ.compare()

        # Verify that moved entries were detected
        moved_entries = [r for r in self.differ._results if r.diff_type == "moved"]
        self.assertEqual(len(moved_entries), 1)
        self.assertEqual(moved_entries[0].title, "Entry")
        self.assertEqual(moved_entries[0].path1, "Group1")
        self.assertEqual(moved_entries[0].path2, "Group2")

if __name__ == '__main__':
    unittest.main()
