#!/usr/bin/env python3
"""
Test suite for emergency CLI wrapper component.
Validates compliance with <1000 line component requirements.
"""

import unittest
import subprocess
import os
from pathlib import Path


class TestEmergencyCLI(unittest.TestCase):
    """Test emergency CLI wrapper functionality."""

    def setUp(self):
        """Set up test environment."""
        # Get absolute path to script from tests directory
        test_dir = Path(__file__).parent
        self.script_path = test_dir.parent / "scripts" / "emergency_cli.py"
        self.assertTrue(self.script_path.exists(), "Emergency CLI script must exist")

    def test_script_size_compliance(self):
        """Test that emergency CLI is under size limit."""
        with open(self.script_path, 'r') as f:
            lines = len(f.readlines())

        self.assertLess(lines, 100, f"Emergency CLI ({lines} lines) must be under 100 lines")

    def test_help_display(self):
        """Test help functionality."""
        result = subprocess.run(['python', str(self.script_path)],
                              capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn("EMERGENCY COMPLETION CLI", result.stdout)
        self.assertIn("Quick commands:", result.stdout)

    def test_executable_permissions(self):
        """Test script has executable permissions."""
        self.assertTrue(os.access(self.script_path, os.X_OK),
                       "Emergency CLI must be executable")

    def test_component_isolation(self):
        """Test component works independently."""
        # Test that CLI wrapper doesn't depend on large components
        scripts_dir = self.script_path.parent
        result = subprocess.run(['python', '-c',
                               f'import sys; sys.path.insert(0, "{scripts_dir}"); import emergency_cli'],
                              capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, "CLI component must import cleanly")


if __name__ == '__main__':
    unittest.main()
