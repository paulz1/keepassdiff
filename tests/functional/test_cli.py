import unittest
import tempfile
import os
from unittest.mock import patch
from pykeepass import create_database
from keepass_diff import main
from datetime import datetime

class TestCLIFunctionality(unittest.TestCase):
    def setUp(self):
        """Set up test databases"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test database 1
        self.db1_path = os.path.join(self.temp_dir, "test1.kdbx")
        # Create a new database instead of trying to open non-existent one
        self.db1 = create_database(self.db1_path, password='test1', keyfile=None)
        group1 = self.db1.add_group(self.db1.root_group, "Group1")
        self.db1.add_entry(group1, title="Test Entry", username="user1", password="pass1")
        self.db1.save()

        # Create test database 2 (with entry in different location)
        self.db2_path = os.path.join(self.temp_dir, "test2.kdbx")
        # Create a new database instead of trying to open non-existent one
        self.db2 = create_database(self.db2_path, password='test2', keyfile=None)
        group2 = self.db2.add_group(self.db2.root_group, "Group2")
        self.db2.add_entry(group2, title="Test Entry", username="user1", password="pass1")
        self.db2.save()

    def tearDown(self):
        """Clean up test files"""
        try:
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"Error during cleanup: {e}")

    @patch('getpass.getpass', side_effect=['test1', 'test2'])
    def test_basic_comparison(self, mock_getpass):
        """Test basic comparison functionality"""
        with patch('builtins.input', side_effect=['n']):
            with patch('sys.argv', ['keepass_diff.py', self.db1_path, self.db2_path]):
                result = main()
                self.assertEqual(result, 0)  # Expect successful execution

    @patch('getpass.getpass', side_effect=['test1', 'test2'])
    @patch('builtins.input', side_effect=['n', '4', 'M0001', 'n', 'n'])
    def test_show_entry_details(self, mock_getpass, mock_input):
        """Test showing entry details in interactive mode"""
        with patch('sys.argv', ['keepass_diff.py', self.db1_path, self.db2_path, '--edit']):
            result = main()
            self.assertEqual(result, 0)

    @patch('getpass.getpass', side_effect=['test1', 'test2'])
    def test_edit_mode_backup_creation(self, mock_getpass):
        """Test that --edit option creates backup files"""
        # Capture the current time which will be used for backup timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H_%M")
        
        with patch('sys.argv', ['keepass_diff.py', self.db1_path, self.db2_path, '--edit']):
            # Simulate user input for password question
            with patch('builtins.input', side_effect=['n', 'n']):
                result = main()
                self.assertEqual(result, 0)

            # Check backup files exist and are identical to originals
            backup_files = [f for f in os.listdir(self.temp_dir) 
                           if f.endswith(f'.backup_{timestamp}')]
            self.assertEqual(len(backup_files), 2)

            # Verify backup files are identical to original databases
            for db_path in [self.db1_path, self.db2_path]:
                # Find the backup file for this database
                backup_file = next((f for f in backup_files if f.startswith(os.path.basename(db_path))), None)
                self.assertIsNotNone(backup_file)
                backup_path = os.path.join(self.temp_dir, backup_file)
                self.assertTrue(os.path.exists(backup_path))
                with open(db_path, 'rb') as original, open(backup_path, 'rb') as backup:
                    self.assertEqual(original.read(), backup.read())

    @patch('getpass.getpass', side_effect=['test1', 'test2'])
    def test_database_synchronization(self, mock_getpass):
        """Test copying entry from one database to another"""
        # Create a new test database with one entry
        source_db_path = os.path.join(self.temp_dir, "source.kdbx")
        source_db = create_database(source_db_path, password='test1', keyfile=None)
        source_group = source_db.add_group(source_db.root_group, "Group")
        source_db.add_entry(source_group, title="Test Entry", username="user1", password="pass1")
        source_db.save()

        # Create an empty target database
        target_db_path = os.path.join(self.temp_dir, "target.kdbx")
        target_db = create_database(target_db_path, password='test2', keyfile=None)
        target_db.save()

        # Simulate copying entry from source to target
        with patch('sys.argv', ['keepass_diff.py', source_db_path, target_db_path, '--edit']):
            # Simulate user input to copy entry
            with patch('builtins.input', side_effect=['n', '1', '10001', 'y', 'n']):
                result = main()
                self.assertEqual(result, 0)

        # Verify target database now has the same entry as source
        from pykeepass import PyKeePass
        source_kp = PyKeePass(source_db_path, password='test1')
        target_kp = PyKeePass(target_db_path, password='test2')

        # Get entries from both databases
        source_entries = source_kp.entries
        target_entries = target_kp.entries

        # Verify both databases have the same entries
        self.assertEqual(len(source_entries), len(target_entries))
        for source_entry, target_entry in zip(source_entries, target_entries):
            self.assertEqual(source_entry.title, target_entry.title)
            self.assertEqual(source_entry.username, target_entry.username)
            self.assertEqual(source_entry.password, target_entry.password)

if __name__ == '__main__':
    unittest.main()
