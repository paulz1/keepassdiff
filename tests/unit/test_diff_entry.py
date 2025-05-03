import unittest
from datetime import datetime
from keepass_diff_class.keepass_classes import DiffEntry

class TestDiffEntry(unittest.TestCase):
    def setUp(self):
        # Create a sample DiffEntry for testing
        self.diff_entry = DiffEntry(
            diff_id="1",
            diff_type="moved",
            title="Test Entry",
            username="testuser",
            path1="/Group1/SubGroup1",
            path2="/Group2/SubGroup2",
            changes=["Path changed"],
            mtime1=datetime(2025, 4, 11, 12, 0),
            mtime2=datetime(2025, 4, 11, 12, 0)
        )

    def test_diff_entry_initialization(self):
        """Test that DiffEntry is initialized correctly"""
        self.assertEqual(self.diff_entry.diff_id, "1")
        self.assertEqual(self.diff_entry.diff_type, "moved")
        self.assertEqual(self.diff_entry.title, "Test Entry")
        self.assertEqual(self.diff_entry.username, "testuser")
        self.assertEqual(self.diff_entry.path1, "/Group1/SubGroup1")
        self.assertEqual(self.diff_entry.path2, "/Group2/SubGroup2")
        self.assertEqual(self.diff_entry.changes, ["Path changed"])

    def test_diff_entry_str_representation(self):
        """Test the string representation of DiffEntry"""
        expected_str = "[1] moved: Test Entry (testuser) from /Group1/SubGroup1 to /Group2/SubGroup2"
        self.assertEqual(str(self.diff_entry), expected_str)

    def test_diff_entry_equality(self):
        """Test equality comparison between DiffEntry objects"""
        same_entry = DiffEntry(
            diff_id="1",
            diff_type="moved",
            title="Test Entry",
            username="testuser",
            path1="/Group1/SubGroup1",
            path2="/Group2/SubGroup2",
            changes=["Path changed"],
            mtime1=datetime(2025, 4, 11, 12, 0),
            mtime2=datetime(2025, 4, 11, 12, 0)
        )
        different_entry = DiffEntry(
            diff_id="2",
            diff_type="moved",
            title="Different Entry",
            username="testuser",
            path1="/Group1/SubGroup1",
            path2="/Group2/SubGroup2",
            changes=["Path changed"],
            mtime1=datetime(2025, 4, 11, 12, 0),
            mtime2=datetime(2025, 4, 11, 12, 0)
        )
        
        self.assertEqual(self.diff_entry, same_entry)
        self.assertNotEqual(self.diff_entry, different_entry)

if __name__ == '__main__':
    unittest.main()
