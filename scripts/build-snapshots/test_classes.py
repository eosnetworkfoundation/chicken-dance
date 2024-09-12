"""Test Single Run"""
import unittest
import os
import logging
from manifest import Manifest

class TestFileParsing(unittest.TestCase):
    """unittest class for testing manifest class"""
    @classmethod
    def setUpClass(cls):
        # Create a sample file
        cls.sample_file_path = 'sample_test_file.tsv'
        with open(cls.sample_file_path, 'w', encoding='utf-8') as file:
            file.write("0\t500000\t500000\n")
            file.write("500000\t2000000\t500000\n")
            file.write("2000000\t2500000\t500000\n")
            file.write("2500000\t3000000\t400000\n")

    @classmethod
    def tearDownClass(cls):
        # Clean up: Remove the sample file after tests
        os.remove(cls.sample_file_path)

    def test_manifest(self):
        """test the manifest using faked file"""
        test_manifest = Manifest('sample_test_file.tsv')
        self.assertTrue(test_manifest.is_valid())
        self.assertEqual(test_manifest.len(), 7)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
